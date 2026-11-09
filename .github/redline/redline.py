#!/usr/bin/env python3
"""Redline checks for a pull request, from the coding rulebook's Never list.

Hard failures: workflow files that expose secrets, and blocked names in added
lines, commit messages and file paths. Warnings only: AI trailers in commit
messages (cloud sessions add them automatically, so failing on them would turn
most PRs red). Secret scanning is done by gitleaks in the workflow, not here.

A blocked name is never printed: not the name, not a commit subject or file
path that holds it in any spelling, and no traceback. Logs on a public repo
are public.

This runs from the PR's own copy, so it catches honest mistakes. It does not
stop someone who edits the check itself.
"""
from __future__ import annotations

import bisect
import os
import re
import subprocess
import sys
import traceback
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

TRAILER_PATTERNS = [
    re.compile(r"^co-authored-by:.*(claude|anthropic)", re.I | re.M),
    re.compile(r"^claude-session:", re.I | re.M),
    re.compile(r"generated with \[?claude code", re.I),
    re.compile(r"\bclaude (opus|sonnet|haiku|fable) \d", re.I),
]

# A secret is only looked for inside a ${{ ... }} expression, which may run
# over several lines. Both spellings count: secrets.NAME and secrets['NAME'].
EXPRESSION = re.compile(r"\$\{\{(.*?)(?:\}\}|\Z)", re.S)
BRACKET_REF = re.compile(r"(?<![\w.])secrets\s*\[\s*'([A-Za-z0-9_-]+)'\s*\]", re.I)
DOT_REF = re.compile(r"(?<![\w.])secrets\s*\.\s*([A-Za-z0-9_-]+)", re.I)
BARE_REF = re.compile(r"(?<![\w.])secrets\b", re.I)
STRING = re.compile(r"'[^']*'")
TOJSON_SECRETS = re.compile(r"toJSON\s*\(\s*secrets\b", re.I)
SECRETS_INHERIT = re.compile(r"""^\s*["']?secrets["']?\s*:\s*["']?inherit\b""")
# "KEY: ${{ secrets.NAME }}" and nothing else on the line...
SAFE_ASSIGNMENT = re.compile(
    r"""^\s*["']?([\w-]+)["']?\s*:\s*(["']?)\$\{\{\s*secrets\s*"""
    r"""(?:\.\s*[A-Za-z0-9_-]+|\[\s*'[A-Za-z0-9_-]+'\s*\])\s*\}\}\2\s*(?:#.*)?$""", re.I)
# ...and only directly under one of these keys, and never for an input that is
# itself a script or a command line.
SAFE_PARENTS = {"env", "with", "secrets", "credentials"}
SCRIPT_KEYS = {"run", "script", "args", "entrypoint", "command"}
# Secrets that need no protected environment: GitHub's own token, and the
# blocked-names list this check reads on every PR.
NO_ENVIRONMENT_NEEDED = {"GITHUB_TOKEN", "REDLINE_BLOCKED_NAMES"}

LEAD = re.compile(r" *(?:- +)*")
KEY = re.compile(r"""["']?([\w-]+)["']?\s*:(?:\s|$)""")
BLOCK_SCALAR = re.compile(r"""(?:["']?[\w-]+["']?\s*:\s+)?[|>][-+0-9]*\s*(?:#.*)?$""")
ENVIRONMENT = re.compile(r"""\s*["']?environment["']?\s*:(.*)$""")
WORKFLOW_PATH = re.compile(r"\.github/workflows/[^\n]+\.ya?ml", re.I)
HIDDEN_PATH = "(path not shown)"
SEPARATORS = re.compile(r"[\s\-_.]+")


@dataclass
class Finding:
    level: str  # "error" or "warning"
    where: str
    message: str


@dataclass
class LineInfo:
    text: bool = False        # inside a block or multi-line quoted value: text, not YAML keys
    parent: str | None = None  # the key this line sits directly under; None for text
    protected: bool = False   # inside a job that has its own environment: key


def normalize(text: str) -> str:
    """NFKD, strip accents, casefold, per the rulebook's matching rule."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def fold(text: str) -> str:
    """normalize(), with spaces, hyphens, underscores and dots all read as one
    space, so "Zoe Quill" also matches zoe-quill, zoe_quill and zoe.quill."""
    return SEPARATORS.sub(" ", normalize(text))


def squash(text: str) -> str:
    return "".join(c for c in normalize(text) if c.isalnum())


def name_targets(blocked: list[str]) -> list[str]:
    return [t for t in (fold(b).strip() for b in blocked) if t]


def has_name(text: str, targets: list[str]) -> bool:
    folded = fold(text)
    return any(t in folded for t in targets)


def may_show_name(text: str, targets: list[str]) -> bool:
    """Looser than has_name, for deciding what is safe to print. Letters and
    digits only, %-encoding undone, and a name's words in any order with
    anything between them, so ZoeQuill, Quill_Zoe and Zoe%20Quill all count.
    A wrong yes only hides a path."""
    for reading in {text, unquote(text, errors="replace")}:
        squashed = squash(reading)
        if has_name(reading, targets):
            return True
        for target in targets:
            words = [w for w in (squash(part) for part in target.split()) if w]
            if words and all(w in squashed for w in words):
                return True
    return False


def shown_path(paths: list[str], targets: list[str]) -> str:
    """The path to print, given its readings: hidden when it may hold a name,
    or isn't clean UTF-8 and so can't be checked well enough."""
    if len(paths) > 1 or may_show_name(paths[0], targets):
        return HIDDEN_PATH
    return paths[0]


def parse_blocked(raw: str) -> list[str]:
    """Names separated by commas, semicolons or new lines, each trimmed."""
    return [part.strip() for part in re.split(r"[,;\n]", raw) if part.strip()]


def readings(raw: bytes) -> list[str]:
    """The text as UTF-8. Where it isn't UTF-8, two readings: lossy UTF-8 and
    Windows-1252, so a name is found whichever way it was saved."""
    try:
        return [raw.decode("utf-8")]
    except UnicodeDecodeError:
        return [raw.decode("utf-8", errors="replace"), raw.decode("cp1252", errors="replace")]


def check_commit_message(sha: str, message: str) -> list[Finding]:
    """The subject is not quoted back: it may hold a blocked name."""
    if not any(p.search(message) for p in TRAILER_PATTERNS):
        return []
    return [Finding("warning", f"commit {sha[:8]}",
                    "AI trailer or model name in the commit message")]


def strip_comment(value: str) -> str:
    return re.sub(r"(^|\s)#.*$", "", value).strip()


def quote_closes(text: str, quote: str) -> bool:
    """Does text hold the closing quote of a value opened with this quote?"""
    i = 0
    while i < len(text):
        if quote == '"' and text[i] == "\\":
            i += 2
        elif text[i] == quote and quote == "'" and text[i + 1:i + 2] == "'":
            i += 2
        elif text[i] == quote:
            return True
        else:
            i += 1
    return False


def scan_structure(lines: list[str]) -> list[LineInfo]:
    """Place each line in the file's layout by indentation, with no YAML parser.

    Anything this can't place counts as unprotected text, so an odd layout
    fails rather than passes.
    """
    info = [LineInfo() for _ in lines]
    job_of: list[int | None] = [None] * len(lines)
    protected: dict[int, bool] = {}
    stack: list[tuple[int, str]] = []       # (column, key) of the open keys
    block_col: int | None = None            # inside a | or > block deeper than this
    open_quote: str | None = None           # inside a quoted value that runs over lines
    bare_environment: tuple[int, int] | None = None  # (job, indent) of "environment:" alone
    in_jobs, job_indent, child_indent, job = False, None, None, None

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        job_of[i] = job
        if open_quote:
            info[i].text = True
            if quote_closes(line, open_quote):
                open_quote = None
            continue
        if block_col is not None:
            if not stripped or indent > block_col:
                info[i].text = True
                continue
            block_col = None
        if not stripped or stripped.startswith("#"):
            continue

        # Which key is this line directly under?
        col = len(LEAD.match(line).group(0))
        rest = line[col:]
        while stack and stack[-1][0] >= col:
            stack.pop()
        info[i].parent = stack[-1][1] if stack else None
        key = KEY.match(rest)
        if key:
            stack.append((col, key.group(1)))
        if BLOCK_SCALAR.match(rest):
            block_col = col if key else max(col - 2, indent)
        else:
            value = (rest[key.end():] if key else rest).lstrip()
            if value[:1] in ("'", '"') and not quote_closes(value[1:], value[0]):
                open_quote = value[0]

        # Which job is it in, and does that job have its own environment?
        if bare_environment is not None:
            env_job, env_indent = bare_environment
            if indent > env_indent:
                protected[env_job] = True
            bare_environment = None
        if indent == 0:
            in_jobs = bool(re.match(r"jobs\s*:\s*(#.*)?$", line))
            job_indent = child_indent = job = None
        elif in_jobs:
            if job_indent is None:
                job_indent = indent
            if indent <= job_indent:
                job, child_indent = i, None
                protected[i] = False
            else:
                if child_indent is None:
                    child_indent = indent
                env = ENVIRONMENT.match(line)
                if env and indent == child_indent:
                    value = strip_comment(env.group(1))
                    if not value:
                        bare_environment = (job, indent)
                    elif (value not in ('""', "''") and value.count('"') % 2 == 0
                          and value.count("'") % 2 == 0):
                        protected[job] = True
        job_of[i] = job

    for i, j in enumerate(job_of):
        info[i].protected = j is not None and protected.get(j, False)
    return info


def secrets_in(expression: str) -> tuple[list[str], bool]:
    """Named secrets in one expression, and whether the whole object is used."""
    names = BRACKET_REF.findall(expression)
    rest = STRING.sub("''", BRACKET_REF.sub(" ", expression))
    names += DOT_REF.findall(rest)
    return names, bool(BARE_REF.search(DOT_REF.sub(" ", rest)))


def check_workflow(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    raw_lines = text.splitlines()
    info = scan_structure(raw_lines)
    # Only whole-line YAML comments are skipped. A "#" later on a line, or at
    # the start of a line inside a script, is still read: Actions fills in
    # ${{ }} there too.
    lines = ["" if l.lstrip().startswith("#") and not info[i].text else l
             for i, l in enumerate(raw_lines)]
    starts = [0]
    for l in lines:
        starts.append(starts[-1] + len(l) + 1)
    expressions: dict[int, list[str]] = {}
    for m in EXPRESSION.finditer("\n".join(lines)):
        expressions.setdefault(bisect.bisect_right(starts, m.start()), []).append(m.group(1))

    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"{path}:{n}"
        here = info[n - 1]
        if re.search(r"\bpull_request_target\b", re.sub(r"\s#.*$", "", line)):
            findings.append(Finding("error", where,
                "pull_request_target gives PR code access to secrets; use pull_request"))
        if SECRETS_INHERIT.match(line) and not here.text:
            findings.append(Finding("error", where,
                "secrets: inherit hands every secret to another workflow; pass each one by name"))
        names: list[str] = []
        whole = bool(TOJSON_SECRETS.search(line))
        for expression in expressions.get(n, []):
            found, uses_whole = secrets_in(expression)
            whole = whole or uses_whole
            for name in found:
                if name not in names:
                    names.append(name)
        if whole:
            findings.append(Finding("error", where,
                "the whole secrets object is used (toJSON(secrets), secrets.* or a "
                "computed name); name each secret instead"))
        assignment = SAFE_ASSIGNMENT.match(line)
        safe = bool(assignment and here.parent in SAFE_PARENTS  # text lines have no parent
                    and assignment.group(1).lower() not in SCRIPT_KEYS)
        for name in names:
            if not safe:
                findings.append(Finding("error", where,
                    f"secrets.{name} is pasted into a script; pass it through env: instead"))
            if name.upper() not in NO_ENVIRONMENT_NEEDED and not here.protected:
                findings.append(Finding("error", where,
                    f"secrets.{name} used without a protected environment: block"))
    return findings


def check_added_lines(diff: str | bytes, blocked: list[str]) -> list[Finding]:
    targets = name_targets(blocked)
    if not targets:
        return []
    findings: list[Finding] = []
    path, line_no, in_hunk = "?", 0, False
    for diff_line in diff.split(b"\n" if isinstance(diff, bytes) else "\n"):
        texts = readings(diff_line) if isinstance(diff_line, bytes) else [diff_line]
        raw = texts[0]
        if raw.startswith("diff --git "):
            in_hunk = False
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) - 1 if m else 0
            in_hunk = True
            continue
        if not in_hunk:
            # File headers. Inside a hunk a line starting "+++ " is content.
            if raw.startswith('+++ "'):
                # git quotes and escapes a path holding a tab, a new line or
                # a quote mark; an escaped path can't be checked, so hide it.
                path = HIDDEN_PATH
            elif raw.startswith("+++ "):
                cut = 6 if raw.startswith("+++ b/") else 4
                path = shown_path([t[cut:].rstrip("\t") for t in texts], targets)
            continue
        if raw.startswith("+"):
            line_no += 1
            if any(has_name(t[1:], targets) for t in texts):
                findings.append(Finding("error", f"{path}:{line_no}",
                    "blocked personal name in an added line (value not shown)"))
        elif not raw.startswith(("-", "\\")):
            line_no += 1
    return findings


def git_raw(*args: str) -> bytes:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args],
                          check=True, capture_output=True).stdout


def git(*args: str) -> str:
    return git_raw(*args).decode("utf-8", errors="replace")


def run(base: str, head: str, blocked: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    targets = name_targets(blocked)
    # Merge commits are left out of the trailer warning, not out of the names check.
    plain = set(git("rev-list", "--no-merges", f"{base}..{head}").split())
    for sha in git("rev-list", f"{base}..{head}").split():
        messages = readings(git_raw("log", "-1", "--format=%B", sha))
        if sha in plain:
            findings += check_commit_message(sha, messages[0])
        if any(has_name(m, targets) for m in messages):
            findings.append(Finding("error", f"commit {sha[:8]}",
                "blocked personal name in a commit message (value not shown)"))
    # --no-renames: a renamed or copied workflow file shows up as a new file.
    changed = git_raw("diff", "--name-only", "--no-renames", "--diff-filter=d", "-z",
                      f"{base}...{head}").split(b"\0")
    for raw_path in changed:  # each path decoded on its own
        paths = readings(raw_path)
        shown = shown_path(paths, targets)
        if any(has_name(p, targets) for p in paths):
            findings.append(Finding("error", "a changed file",
                "blocked personal name in a file path (path not shown)"))
        on_disk = Path(os.fsdecode(raw_path))
        if any(WORKFLOW_PATH.fullmatch(p) for p in paths) and on_disk.is_file():
            findings += check_workflow(
                shown, on_disk.read_bytes().decode("utf-8", errors="replace"))
    findings += check_added_lines(git_raw("diff", "--unified=0", f"{base}...{head}"), blocked)
    return findings


def check() -> int:
    base, head = os.environ.get("BASE_SHA", ""), os.environ.get("HEAD_SHA", "")
    if not base or not head:
        print("::error::BASE_SHA and HEAD_SHA must be set")
        return 2
    blocked = parse_blocked(os.environ.get("BLOCKED_NAMES", ""))
    if not blocked:
        print("::notice::redline: blocked-names check skipped, no names list reached this run")
    targets = name_targets(blocked)
    findings = run(base, head, blocked)
    for f in findings:
        line = f"::{f.level}::{f.where}: {f.message}"
        # Last net: the parts that come from the PR (a path, a secret's name)
        # are checked once more before anything is printed.
        from_pr = " ".join([f.where, *re.findall(r"secrets\.([\w-]+)", f.message)])
        if may_show_name(from_pr, targets):
            line = f"::{f.level}::a finding whose details would show a blocked name (not shown)"
        print(line)
    errors = sum(f.level == "error" for f in findings)
    warnings = len(findings) - errors
    print(f"redline: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def main() -> int:
    try:
        return check()
    except Exception as exc:  # no traceback: it could quote a path or a name
        here = [f.lineno for f in traceback.extract_tb(exc.__traceback__)
                if f.filename == __file__]
        print("::error::redline stopped on an internal error "
              f"({type(exc).__name__} at redline.py line {here[-1] if here else '?'})")
        return 2


if __name__ == "__main__":
    sys.exit(main())
