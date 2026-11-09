#!/usr/bin/env python3
"""Redline checks for a pull request, from the coding rulebook's Never list.

Hard failures: workflow files that expose secrets, and blocked names in added
lines. Warnings only: AI trailers in commit messages (cloud sessions add them
automatically, so failing on them would turn most PRs red).
Secret scanning is done by gitleaks in the workflow, not here.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

TRAILER_PATTERNS = [
    re.compile(r"^co-authored-by:.*(claude|anthropic)", re.I | re.M),
    re.compile(r"^claude-session:", re.I | re.M),
    re.compile(r"generated with \[?claude code", re.I),
    re.compile(r"\bclaude (opus|sonnet|haiku|fable) \d", re.I),
]

SECRET_REF = re.compile(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)")
SAFE_ASSIGNMENT = re.compile(r"^\s*-?\s*[\w-]+:\s*\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}\s*$")


@dataclass
class Finding:
    level: str  # "error" or "warning"
    where: str
    message: str


def normalize(text: str) -> str:
    """NFKD, strip accents, casefold, per the rulebook's matching rule."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def check_commit_message(sha: str, message: str) -> list[Finding]:
    hits = [p.pattern for p in TRAILER_PATTERNS if p.search(message)]
    if not hits:
        return []
    subject = message.splitlines()[0][:60] if message else ""
    return [Finding("warning", f"commit {sha[:8]}",
                    f"AI trailer or model name in commit message ('{subject}')")]


def check_workflow(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    uses_environment = any(re.match(r"^\s*environment:", l) for l in lines)
    for n, line in enumerate(lines, 1):
        code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        if not code.strip():
            continue
        where = f"{path}:{n}"
        if re.search(r"\bpull_request_target\b", code):
            findings.append(Finding("error", where,
                "pull_request_target gives PR code access to secrets; use pull_request"))
        if re.search(r"toJSON\(\s*secrets\s*\)", code, re.I):
            findings.append(Finding("error", where, "toJSON(secrets) dumps every secret"))
        ref = SECRET_REF.search(code)
        if not ref:
            continue
        name = ref.group(1)
        if not SAFE_ASSIGNMENT.match(code):
            findings.append(Finding("error", where,
                f"secrets.{name} is pasted into a script; pass it through env: instead"))
        if name != "GITHUB_TOKEN" and not uses_environment:
            findings.append(Finding("error", where,
                f"secrets.{name} used without a protected environment: block"))
    return findings


def check_added_lines(diff: str, blocked: list[str]) -> list[Finding]:
    """Never print the blocked value itself: logs on public repos are public."""
    targets = [normalize(b) for b in blocked if b.strip()]
    if not targets:
        return []
    findings: list[Finding] = []
    path, line_no = "?", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) - 1 if m else 0
            continue
        if raw.startswith("+"):
            line_no += 1
            text = normalize(raw[1:])
            if any(t in text for t in targets):
                findings.append(Finding("error", f"{path}:{line_no}",
                    "blocked personal name in an added line (value not shown)"))
        elif not raw.startswith("-"):
            line_no += 1
    return findings


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True,
                          text=True).stdout


def run(base: str, head: str, blocked: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for sha in git("rev-list", "--no-merges", f"{base}..{head}").split():
        findings += check_commit_message(sha, git("log", "-1", "--format=%B", sha))
    changed = git("diff", "--name-only", "--diff-filter=AM", f"{base}...{head}").split()
    for path in changed:
        if re.match(r"^\.github/workflows/.+\.ya?ml$", path) and Path(path).exists():
            findings += check_workflow(path, Path(path).read_text())
    findings += check_added_lines(git("diff", "--unified=0", f"{base}...{head}"), blocked)
    return findings


def main() -> int:
    base, head = os.environ.get("BASE_SHA", ""), os.environ.get("HEAD_SHA", "")
    if not base or not head:
        print("::error::BASE_SHA and HEAD_SHA must be set")
        return 2
    blocked = [b for b in os.environ.get("BLOCKED_NAMES", "").split(",") if b.strip()]
    findings = run(base, head, blocked)
    for f in findings:
        print(f"::{f.level}::{f.where}: {f.message}")
    errors = sum(f.level == "error" for f in findings)
    warnings = len(findings) - errors
    print(f"redline: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
