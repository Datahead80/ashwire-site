# AGENTS.md

ashwire.ai, the Ashwire Labs site. Plain HTML, CSS and SVG in `site/`, no build step, no dependencies. This repo is public: nothing private goes in it.

## Commands
```bash
python3 -m http.server -d site 8080        # preview at http://localhost:8080
```
Deploy: every push to `main` publishes `site/` to GitHub Pages through `.github/workflows/pages.yml`, usually within a minute. Nothing else to run. Agents cannot change Pages or DNS settings; Stephen does those clicks (DNS is at GoDaddy, steps in `DEPLOY.md`).

## Layout
| Path | Purpose |
| --- | --- |
| `site/index.html` | Landing page: mission, values, Cinderbox "first up" |
| `site/cinderbox/index.html` | Cinderbox product page |
| `site/assets/`, `site/brand/`, `site/favicon.svg` | Circuit phoenix mark |
| `DEPLOY.md` | One-time Pages and DNS setup |

## Mission test (higher wins a conflict)
1. Protect the person's data. 2. Human first. 3. Does what it says, honest about limits. 4. Time back. 5. Lean.

## Code style
- Read the surrounding markup and match it: semantic HTML, CSS custom properties from `:root`, inline SVG for the mark, no frameworks or scripts unless the page cannot work without them.
- Smallest change that fully solves the ask. No drive-by restyling or reformatting.
- Build DOM with `textContent`, never `innerHTML` with data.
- Every image has alt text; text meets contrast on the dark ground; the page works at phone width without horizontal scroll.
- No filler comments, no AI watermarks or model names in markup or commits.
- Keep the project copy at `ashwire/ashwire.ai/index.html` in step when `site/index.html` changes.

## Copy
- Never use Stephen's real name. Credit only "Datahead". No founder quote, no profile box.
- Mission first, plain and human. Avoid forced phoenix, fire or forge wording and robotic phrasing; the phoenix is the logo and how Ashwire builds, not a story.
- Ashwire builds many kinds of apps. Cinderbox is first, not the only one, and the site is not privacy-only.
- Approved headline: "Use whatever AI you like. You decide what it gets to know about you." Reuse that voice.
- Every claim must be true today. Say what exists, not what is planned.

## Brand
Ground `#14121A`, ember `#FF5A2C`, flare `#FF2E88`, wire `#2DE2E6`, smoke `#8E8A9C`. Fonts: Chakra Petch (display), IBM Plex Sans (body), IBM Plex Mono (labels). Loaded from Google Fonts; that is the only outside request the pages make.

## Testing
Open the page in a browser at phone and desktop width before committing. Click every link. Check the SVG renders. There is no automated suite.

## Git
- One logical change per commit, imperative subject under 72 characters, saying why.
- Work on the branch you were given; open a PR to `main`. Merging publishes, so the PR is the review.
- Re-read your own diff as a reviewer before pushing.

## Boundaries
**Always**: keep the site dependency-free and static.
**Ask first**: new pages, forms, analytics, third-party scripts, any new outside request, any copy that mentions a product that is not shipped.
**Never**: add a sign-up form or email capture (there is no outside service yet; sign-ups stay "coming soon"); add tracking or ads; commit keys, personal data or anything about the MUD server.

## Done means
Page checked in a browser at both widths, links work, copy rules above hold, `site/` and the project copy match.
