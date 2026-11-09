# Contributing

This repo has one maintainer. PRs may take a while to review, and some will be declined.

## How to contribute

1. **Open an issue first.** Use the "Skill feedback" form. Say what the skill or agent did,
   what it should have done, and include the evidence. A skill changes only after a failure
   someone has observed. "It would be nicer" is not enough (see "Change rule" in
   [AGENTS.md](AGENTS.md)).
2. **Send a PR only for an accepted issue.** Make the smallest fix, following the order in
   AGENTS.md: `references/gotchas.md` first, then `SKILL.md`, then a script.
3. **Run the checks** listed in AGENTS.md before you push, and follow its "Content rules".
4. **Report security problems privately.** Use the "Report a vulnerability" button, not an
   issue. See [SECURITY.md](SECURITY.md).

Contributions are licensed under this repo's MIT license.

## How a PR is reviewed

CI on a PR runs that PR's own copy of the workflows, scripts and tests, so a PR can weaken a
gate and still pass it. The review does not take CI at its word:

1. The maintainer approves every workflow run from a fork.
2. The maintainer reads `gh pr diff <n>`. If the diff touches `.github/`, `scripts/`, `tests/`
   or `scripts/url-allowlist.txt`, a green CI run is not evidence, and those files are read
   line by line.
3. The PR's files are checked as data with main's gates, from a clone on `main`:

   ```
   git fetch origin pull/<n>/head && git worktree add --detach ../pr-<n> FETCH_HEAD
   python3 scripts/lint_content.py ../pr-<n>
   python3 scripts/validate.py ../pr-<n>
   git worktree remove ../pr-<n>
   ```

   The PR's tests are never run outside CI, and no agent session is started inside `../pr-<n>`.
4. Skill text is read for what it makes an agent do. Does it now run commands, fetch URLs,
   read outside the project, touch credentials, or widen `allowed-tools` or `tools`? Does it
   change `AGENTS.md` or `CLAUDE.md`? A scanner pass is support, not a verdict.
5. The maintainer approves the final head commit. Any later push dismisses that approval.
