# Retro: v0-1-0-initial-release

- Date: 2026-11-09
- Repo: ZrobDev/data-engineering-skills · Branch: main · Range: 697330c..1fb903c (4 commits since repo start)
- Previous: none
- Backlog: no

## State
- #1 feat: skills, agent team, vendor puller, CI gates — merged (1fb903c, verified) — tag `v0.1.0` (signed) pushed; plugin `data-engineering@zrobdev-data` reinstalled on the maintainer's workstation at 0.1.0, cache identical to main
- skills.sh discovery from GitHub — `skills@1.7.4 add ZrobDev/data-engineering-skills --list` finds all 7 skills
- GitHub hardening — rulesets `main-protection` and `immutable-release-tags` active; secret scanning with push protection, private vulnerability reporting, Dependabot alerts on; label `skill-feedback` exists
- Maintainer dotfiles repo A: retro Skill feedback step + `includeIf` signing scoped to the skills clones — merged — applied on the primary workstation (verified: signing on in this repo, unset in an unrelated repo)
- Maintainer dotfiles repo B — same patch, merged — not applied on the second workstation yet
- Feature worktrees and branch removed in both dotfiles repos

## Deviations
| Plan said | What was done | Why | Asked |
|---|---|---|---|
| Vendor manifest `vendors.yaml` | `vendors.toml` | `tomllib` is stdlib; keeps the puller dependency-free | no |
| CI calls `devops-pipeline/security.yml@v1` | Own gitleaks + zizmor jobs in `ci.yml` | devops-pipeline is private; a public repo cannot call it | no |
| Tests with `pytest` | `unittest` | stdlib only, no dependency to add | no |
| Global `commit.gpgsign true` | Repo-local config plus a dotfiles `includeIf "gitdir:<skills clones>/"` | `.gitconfig` is dotfiles-managed; global signing would hit every repo | no |
| Set repo merge-method settings | Skipped | deny-list `Bash(gh api *merge*)` blocks the call | no |
| Step 8: local install means edits are live | Installed plugin is a cached copy at its version; `--plugin-dir` documented in AGENTS.md for live editing | premise false: install copies to `~/.claude/plugins/cache/` | no |
| Push `main` after `gh repo create` | `--add-readme`, then everything via PR #1 | `guard-main-commit.sh` blocks commits on main | no |
| Commit in worktrees from their cwd | `git -C <worktree>` from the skills repo cwd, after asserting the branch | the hook checks the session cwd's branch | no |
| Tag after CI green | Pushed a 5-finding review fix (4b4371a) to PR #1 first | ruleset requires review-thread resolution; Codex left 5 real findings | no |
| `license` not in plan | `license: MIT` added to every SKILL.md | scanner INFO `MANIFEST_MISSING_LICENSE` | no |

## Owed
- [ ] operator: on the second workstation, sync dotfiles repo B to main and apply it — puts the retro Skill feedback step and signing include live there
- [ ] operator: commit this retro on a branch and open a PR (main ruleset blocks direct pushes) — records the session
- [ ] operator (optional): `sudo pacman -S duckdb` — de-scout and the skills default to DuckDB for profiling

## Verification loop
```bash
cd <clone of this repo>
python3 scripts/lint_content.py                                            # lint_content: 0 finding(s)
python3 scripts/validate.py                                                # validate: 0 finding(s)
PYTHONPYCACHEPREFIX=$(mktemp -d) python3 -m unittest discover -s tests     # Ran 25 tests ... OK
python3 skills/de-vendors/scripts/pull_vendor.py selftest                  # selftest ok
gh api repos/ZrobDev/data-engineering-skills/rulesets --jq '.[].name'      # main-protection, immutable-release-tags
git ls-remote --tags origin v0.1.0 | wc -l                                 # 1
diff -rq --exclude=.git ~/.claude/plugins/cache/zrobdev-data/data-engineering/0.1.0 .   # no output while main == v0.1.0
```

## Failure modes
| What broke | Where it hid | Root cause | Check that now forces it |
|---|---|---|---|
| skills.sh listed 5 of 7 skills | `description:` of etl-pipelines and lakehouse | unquoted `: ` is invalid YAML; skills CLI drops the skill silently, Claude Code's loader does not | `python3 scripts/validate.py` (test `test_unquoted_colon_in_description`) |
| URL allowlist passed a link of the form `github.com@<other host>/...` | `scripts/lint_content.py` URL regex | regex captured the text before `@` as the host | test `test_url_userinfo_spoof` |
| `pull_vendor add a b` left skill `a` installed with no lock when `b` failed its scan | `cmd_add` loop | copy and scan interleaved; lock written only at the end | `review: does cmd_add scan every requested skill before the first copytree, and write the lock inside the install loop?` |
| Reconciliation query dropped one-sided NULL amounts; SCD2 checks missed gap facts and same-start overlaps | `reconciliation-recipes.md`, `fan-out-checks.md` | NULL arithmetic in WHERE; inner join; self-pair excluded by `valid_from` | `review: does every reference SQL recipe have a one-row fixture case for NULL, zero-match and tie inputs?` |
| PR #1 `BLOCKED` with all checks green and 0 approvals required | ruleset `required_review_thread_resolution` | Codex bot review left 5 unresolved threads | `gh api graphql -f query='{repository(owner:"ZrobDev",name:"data-engineering-skills"){pullRequest(number:N){reviewThreads(first:50){nodes{isResolved}}}}}' --jq '[..\|.isResolved?\|select(.==false)]\|length'` → 0 |
| `pr-body` check failed on both dotfiles PRs (third time: 2026-09-10, 2026-09-16, now) | PR description | body written from memory with `## Risk`; the memory note lives only in another project's memory dir, which a session started elsewhere never loads | `for h in '## Merge risk' '## Delegation evidence'; do grep -qE "^$h" body.md \|\| echo MISSING $h; done` before `gh pr create` |
| Installed plugin kept pre-review files after merge; `claude plugin update` said "nothing to update" | `~/.claude/plugins/cache/zrobdev-data/data-engineering/0.1.0` | update keys on version; same version, no refresh | `diff -rq --exclude=.git ~/.claude/plugins/cache/zrobdev-data/data-engineering/0.1.0 <clone>` empty; else uninstall + install |

## Process lessons
- Evidence: PR #1 BLOCKED row. Rule: before calling a PR mergeable, count unresolved review threads (graphql `isResolved`), not only checks and approvals. Scope: project.
- Evidence: `pr-body` row. Rule: before `gh pr create` in a repo with `.github/workflows/pr-body.yml`, grep its asserted headings into the body file. Scope: global-candidate.
- Evidence: 4b4371a. Rule: every SQL recipe shipped in a skill gets a sqlite/duckdb fixture with a NULL, a zero-match and a tie case before release. Scope: project.

## Decisions
- Kept: one tree (`source: "./"`) serves the plugin marketplace and skills.sh — verified both channels list 7 skills (plan Q-rounds 1–3)
- Kept: vendor skills pulled per project at pinned SHA, scanned, never global; Snowflake refused on licence until `--accept-license` (plan Step 4)
- Kept: changes only on an observed failure, routed retro → `skill-feedback` issue → `references/gotchas.md` → tag (AGENTS.md, Honcho `[global]` pattern)
- Kept: signing scoped by `includeIf` to the skills clones, not global (dotfiles repo A)

## Memory proposals
| Action | Note | Reason |
|---|---|---|
| none | none | no project memory dir for this repo; the cross-repo lesson goes to Graduation instead |

Status: applied 2026-11-09

## Skill feedback
| Skill | Repo | What the agent did | What it should have done | Evidence | Issue |
|---|---|---|---|---|---|
| none | none | none | none | none | none |

Status: applied 2026-11-09

## Graduation candidates
- Before `gh pr create` in a repo that has `.github/workflows/pr-body.yml`, extract its asserted headings and grep each into the body file; never `--fill` — test: 2 projects: dotfiles repos A and B (4 failures, 2026-09-10 to 2026-11-09) → pass

## Next session
1. `/retro apply` (graduation candidate pending)
2. Run the Verification loop above
3. First real use of a skill on a project; misfires become `## Skill feedback` rows
