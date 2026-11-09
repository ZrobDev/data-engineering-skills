# AGENTS.md

This is a public skills repo. Everything here can end up running inside someone else's agent
session. Anything you change must still pass `python3 scripts/lint_content.py`,
`python3 scripts/validate.py` and `python3 -m unittest discover -s tests`.

## Layout

- `skills/<name>/SKILL.md` and `skills/<name>/references/` (which always includes `gotchas.md`).
  `skills/de-vendors/scripts/pull_vendor.py` is the only script.
- `agents/*.md` holds subagents. Each one pins `model` and lists its `tools`.
- `.claude-plugin/marketplace.json` defines one plugin with `source: "./"`. This one tree
  serves both the Claude Code plugin channel and skills.sh.
- `docs/retro/` — one retro per session, newest first; read the newest before host work.

## Developing

- An installed plugin is a cached copy at its version, and editing the clone does not change
  it. To see edits immediately, start a session with
  `claude --plugin-dir <path-to-your-clone>`.
- After a release, `claude plugin update data-engineering@zrobdev-data` refreshes the
  installed copy. Restart the session afterwards.
- Check that skills.sh can see every skill with `pnpm dlx skills@<pinned> add <clone> --list`.
  A frontmatter value that is invalid YAML (for example, an unquoted `: `) is dropped silently
  there. `validate.py` guards against this.

## Change rule: observed failure first

A behaviour change to a skill or agent must link the session where it went wrong: a
`skill-feedback` issue, or a retro row that names the misfire. "It would be nicer" is not
enough. Fix it in the smallest place that would have prevented it, in this order:
1. Add a line to `references/gotchas.md`.
2. Edit a rule in `SKILL.md`.
3. Change a script.

Add evals (`evals/`, run with `claude plugin eval`) only for a skill that has misfired twice.

## Content rules (CI enforces these)

- Write only plain text. Give no download-and-run instructions. Link only to hosts in
  `scripts/url-allowlist.txt`; adding a host is a reviewed change.
- Keep `SKILL.md` at 150 lines or fewer. No tool-name tables, generic tutorials or
  trigger-phrase lists, because the `description` already does that job.
- Never claim personal experience, and never name clients, people, machine paths or
  infrastructure.
- Scripts use only the stdlib, make no network imports, and end with an assert self-check.
- Do not add plugin hooks. Never use `Bash(*)` or a bare `Bash` in `allowed-tools`.

## Vendor pins

To bump a vendor `sha` in `skills/de-vendors/vendors.toml`:
1. `gh api repos/<repo>/compare/<old>...<new>` and read the diff for the roots you pull.
2. Update `sha` and `THIRD_PARTY_NOTICES.md` in the same commit.
3. Never point at a branch.

## Release

1. Add a `## [x.y.z] - YYYY-MM-DD` section to `CHANGELOG.md` (Keep a Changelog, SemVer).
2. Set the same version in `marketplace.json`, because `validate.py` checks they match.
3. Merge the PR with CI green.
4. Run `git tag -s vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z`.

Tags are immutable. Fix forward with a new tag.

## Boundaries

Never commit secrets, `.env` or `.mcp.json`. Never weaken a guard or a test to get a change
through. Commit only on a branch and through a PR.
