# AGENTS.md

ashwire.ai, the Ashwire Labs site. Plain static files in `site/`, no build step. A push to `main` publishes `site/` to GitHub Pages in about a minute (`DEPLOY.md` has the setup). The repo is public: nothing private goes in it.

## Mission test (higher wins)
1. Protect the person's data. 2. Human first. 3. Does what it says, honest about limits. 4. Time back. 5. Lean.

## Coding practices
- Read the surrounding code first and match its naming, formatting and idiom. Prefer the existing helper over a new one.
- Smallest change that fully solves the ask. No drive-by refactors, renames or reformatting of untouched code.
- Small functions that do one thing, with names that say what they do. Comment only the why, never the what.
- Validate input at the boundary. Trust internal calls.
- Fail loudly with a clear message. Never swallow errors or return a silent default.
- No secrets, keys or real personal data in code, tests, logs or commits. Read secrets from environment or secret stores.
- Check every page at phone width and in the browser before committing. Keep links and images working.
- Use semantic HTML, alt text on images, and sufficient color contrast.
- Commits: one logical change, imperative subject line under 72 characters, saying why.
- Before pushing, re-read your own diff as a reviewer would.

## Project code rules
- Keep it dependency-free: plain HTML, CSS and SVG. Build DOM with `textContent`, never `innerHTML` with data.
- Lean markup. No filler comments, no AI watermarks or model names.
- Keep `site/` and the project's `ashwire/ashwire.ai/index.html` copy in step when either changes.

## Copy
- Never use Stephen's real name. Credit only "Datahead". No founder quote, no profile box.
- Mission first, plain and human. Avoid forced phoenix, fire or forge wording and robotic phrasing. The phoenix is the logo and how Ashwire builds, not a story.
- Ashwire builds many kinds of apps. Cinderbox is first, not the only one, and the site is not privacy-only.
- Approved headline: "Use whatever AI you like. You decide what it gets to know about you." Reuse that voice.
- Sign-ups are "coming soon". Do not add a form without an outside email service and Stephen's say-so.
- Every claim must be true today. Say what exists, not what is planned.

## Brand
Ground `#14121A`, ember `#FF5A2C`, flare `#FF2E88`, wire `#2DE2E6`, smoke `#8E8A9C`. Fonts: Chakra Petch (display), IBM Plex Sans (body), IBM Plex Mono (labels). Logo is the circuit phoenix (concept A).

## Settings
Agents cannot change Pages or DNS settings. Stephen does those clicks (DNS is at GoDaddy). Give exact one-at-a-time steps.
