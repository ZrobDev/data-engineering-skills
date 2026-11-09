## Issue

<!-- Link the accepted issue this PR fixes. PRs without one are usually closed; see CONTRIBUTING.md. -->

## What changed

<!-- The smallest change that would have prevented the observed failure, and where it lives
(references/gotchas.md, SKILL.md, or a script). -->

## Checks

- [ ] `python3 scripts/lint_content.py`, `python3 scripts/validate.py` and
      `python3 -m unittest discover -s tests` pass locally
- [ ] No new link host (`scripts/url-allowlist.txt` unchanged), or the reason is given above
- [ ] No new dependency
- [ ] No wider `allowed-tools` or `tools`
