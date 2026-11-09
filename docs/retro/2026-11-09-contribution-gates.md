# Retro: contribution-gates

- Date: 2026-11-09
- Repo: ZrobDev/data-engineering-skills · Branch: main · Range: 1fb903c..e7c8549 (12 commits since 2026-11-09)
- Previous: [2026-11-09-v0-1-0-initial-release.md](2026-11-09-v0-1-0-initial-release.md)
- Backlog: no

## State
- #2 docs: retro for v0.1.0 — merged (6b700b2, merge commit) — redacted in 435b723, but the unredacted fd482c3 is in main's history
- #3 chore: contribution gates — merged (f2a0c47) — issue form, PR template, CONTRIBUTING review procedure, lint blocks tracked `.claude/` config and `.mcp.json`, SKILL.md cap 150, SECURITY.md rules
- #4 docs(agents): generic clone path — merged (e7c8549, verified merge commit) — first PR under `main-review`, merged through the owner bypass
- GitHub settings live:
  - `main-protection` is merge or squash only, with 4 checks bound to app 15368 and no bypass;
  - `main-review` requires 1 approval, a code-owner review and last-push approval, and the admin can bypass it only through a PR;
  - only selected actions run, and each must be SHA-pinned;
  - every external contributor's fork run needs approval;
  - CodeQL default setup is configured (2 analyses, 0 alerts, advisory);
  - delete-branch-on-merge is on.
- Plugin users are still on 0.1.0. Nothing user-facing changed, so no release.

## Deviations
| Plan said | What was done | Why | Asked |
|---|---|---|---|
| Lint exempts `.claude/settings.local.json` by name | Exempt only when git does not track it (8694503) | Codex P2 on #3: a committed "local" file ships hooks | no |
| Ponytail commit nets about −8 lines | +6 lines (6626fed) | plain `if` dispatch and a once-only frontmatter read are clearer but longer | no |
| SECURITY.md commit lists the repository rules | Also extended the "No hooks" line to cover `.claude/` and `.mcp.json` | mirrors the new lint rule | no |
| Throwaway docs-only PR, closed afterwards | Real fix PR #4 (machine path in AGENTS.md) used as the experiment, and merged | same test, plus a real fix | no |
| Operator commits the retro-apply edits | Committed together with the PR #2 redaction (435b723) | PR #2 was blocked; both files were on the same branch | no |
| Merge #3, then change settings | #2 merged first, so #3 went BEHIND; merged main into the branch (48f4b49) | strict status checks | no |
| Operator settings run applies the rulesets (premise) | First "done" left the rulesets unchanged; re-run with `--jq .name` worked | the commands had not run | no |

## Owed
- [ ] operator: commit this retro on `docs/retro-contribution-gates` and open a PR. Merge it through the `main-review` bypass with a merge commit. — records the session
- [ ] operator: in both dotfiles repos, add a public-repo identity grep to the retro skill's Step 3, and make its README block's "Graduated" line generic (it currently names a personal path) — stops the PR #2 class of leak in every repo
- [ ] operator: decide whether to narrow deny `Bash(gh api *merge*)`. Any narrower set must still cover `gh api .../pulls/N/merge`, graphql `mergePullRequest` and `enablePullRequestAutoMerge`, and `gh -R x pr merge`. It was widened on purpose after an earlier bypass. — unblocks read-only `gh api` calls on fields named `*merge*`
- [ ] operator: carried from the previous retro: sync dotfiles repo B to main on the second workstation; optionally install DuckDB

## Verification loop
```bash
cd <clone of this repo>
python3 scripts/lint_content.py                                          # lint_content: 0 finding(s)
python3 scripts/validate.py                                              # validate: 0 finding(s)
PYTHONPYCACHEPREFIX=$(mktemp -d) python3 -m unittest discover -s tests   # Ran 30 tests ... OK
python3 skills/de-vendors/scripts/pull_vendor.py selftest                # selftest ok
gh api repos/ZrobDev/data-engineering-skills/rules/branches/main --jq '[.[].type]|sort|join(",")'   # deletion,non_fast_forward,pull_request,pull_request,required_signatures,required_status_checks
gh api repos/ZrobDev/data-engineering-skills/actions/permissions --jq '"\(.allowed_actions) \(.sha_pinning_required)"'   # selected true
gh api repos/ZrobDev/data-engineering-skills/actions/permissions/fork-pr-contributor-approval --jq .approval_policy   # all_external_contributors
gh api repos/ZrobDev/data-engineering-skills/code-scanning/default-setup --jq .state               # configured
```

## Failure modes
| What broke | Where it hid | Root cause | Check that now forces it |
|---|---|---|---|
| Public retro named the operator's machines, local paths, private repos and an unrelated project (Codex P1 on #2) | `docs/retro/2026-11-09-v0-1-0-initial-release.md` | the retro is drafted from operator context, and its Step 3 gate checks only for secrets | `grep -nE "/home/[a-z]\|/Users/[A-Za-z]\|~/(Projects\|Documents)/" docs/retro/*.md AGENTS.md README.md CONTRIBUTING.md SECURITY.md` → empty |
| A machine path shipped in AGENTS.md since v0.1.0, and tag `v0.1.0` keeps it | `AGENTS.md:20` | AGENTS.md bans machine paths, but no lint rule enforces it | same grep → empty (a lint rule is the Next-session item) |
| The redacted PR still put the unredacted commit on main | PR #2, merged with a merge commit | the redaction was a fix-forward commit, and a merge commit keeps the branch history | `review: in a public repo, was the redaction an amend plus force-push while the PR was OPEN?` |
| Lint passed a committed `.claude/settings.local.json` with hooks | `scripts/lint_content.py` | the exemption was by filename only | test `test_claude_settings_local_tracked` |
| CI on a fork PR runs the fork's copy of `ci.yml` and the guard scripts | `pull_request` event | GitHub runs the head's workflows; workflows that run from a fixed ref need an org ruleset, which a user account doesn't have | `python3 scripts/lint_content.py ../pr-<n>` run from a clone on main (CONTRIBUTING step 3) |
| Deny `Bash(gh api *merge*)` blocked 3 read-only `gh api` calls | global permission deny list | substring match on field names (`allowed_merge_methods`, `delete_branch_on_merge`) | `review: does the gh api command avoid the substring 'merge', or is it handed to the operator?` |
| PR #3 went BEHIND after #2 merged | `main-protection` strict checks | two PRs open against main | `gh pr view <n> --json mergeStateStatus --jq .mergeStateStatus` → `CLEAN` before handing a PR over |

## Process lessons
- Evidence: CONTRIBUTING.md step 3, plan v2 critique. Rule: before approving a fork PR that touches `.github/`, `scripts/` or `tests/`, run main's `lint_content.py` and `validate.py` on `../pr-<n>`, because the PR's CI isn't evidence. Scope: project.
- Evidence: fd482c3 on main. Rule: in a public repo, redact by amend plus force-push after `gh pr view <n> --json state --jq .state` prints `OPEN`, never with a fix-forward commit. Scope: global-candidate.
- Evidence: PR #2 P1, `AGENTS.md:20`. Rule: before writing into a public repo, grep the draft for this machine's identifiers (`hostname`, `~/.ssh/config` Host names, project directory names), read locally and never written down. Scope: global-candidate.

## Decisions
- Kept: CI on a PR isn't evidence for that PR's own gates; the maintainer runs main's gates on the PR tree — a fork can edit `ci.yml` and the guards, and workflows that run from a fixed ref need an org ruleset (plan v2)
- Kept: issue-first contributions; a PR template only, with no pr-body workflow — a fork can edit a required body check, so it would only stop honest contributors (plan v2)
- Kept: `main-review` (1 approval, last-push approval, admin bypass through a PR only) is separate from `main-protection` (no bypass) — so the bypass skips only review, never the checks (plan v1/v2)
- Kept: CodeQL is advisory, not a merge gate — the stdlib Python is small, actions analysis overlaps zizmor, and blocking docs-only PRs is untested (plan v2)
- Reversed: squash only → merge and squash — squashing breaks the `merge-base --is-ancestor` lesson and the retro evidence SHAs (plan v2 critique)
- Dropped: a required `pr-body` check and a `code_scanning` merge rule — reasons above (plan v1)

## Memory proposals
| Action | Note | Reason |
|---|---|---|
| new | `public-repo-no-operator-identifiers.md` | this repo is public; retros, docs and PR bodies use generic names (dotfiles repo A/B, primary workstation), never hostnames, local paths or other project names. It bit twice: PR #2 and `AGENTS.md:20` |

Status: applied 2026-11-09

## Skill feedback
| Skill | Repo | What the agent did | What it should have done | Evidence | Issue |
|---|---|---|---|---|---|
| none | none | none | none | none | none |

Status: applied 2026-11-09 (nothing to file)

## Graduation candidates
- Redact a public-repo PR by amend plus force-push while it is OPEN, never with a fix-forward commit — test: 1 project (data-engineering-skills) → fails test
- Grep drafts bound for a public repo for this machine's identifiers, read locally — test: 1 project (data-engineering-skills, twice) → fails test

## Next session
1. `/retro apply` (memory proposal pending)
2. Run the Verification loop above
3. PR: a `lint_content.py` rule that flags home-directory paths (`/home/<name>/`, `/Users/<name>/`, `~/` other than `~/.claude/`), plus a break-the-guard test. The observed failure is the Codex thread on PR #2.
