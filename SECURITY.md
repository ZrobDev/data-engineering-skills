# Security policy

## Reporting

Report suspected vulnerabilities **privately** through GitHub's "Report a vulnerability"
button on the Security tab. Do not open a public issue for these. Expect an acknowledgement
within 7 days.

In scope:
- Content that could make an agent run code, fetch remote content, read secrets, or exfiltrate
  data.
- A way around the CI gates.
- A pinned vendor commit that turns out to be malicious.

## What this repo guarantees

- **Plain text only.** No binaries, `.pyc` files, archives, Office documents or images. Every
  file is at most 64 KB and 2,000 lines, and every line is at most 400 characters. These caps
  block padding attacks and hidden payloads.
- **No remote execution paths.** No pipe-to-shell commands, no base64 blobs, and no network
  imports in skill scripts. Links are restricted to `scripts/url-allowlist.txt`.
- **No hooks.** No repo-level `.claude/` config or `.mcp.json` either. No skill pre-approves bare `Bash` or `Bash(*)`. Agents state their model
  and tools explicitly.
- **Pinned tools.** GitHub Actions are pinned by SHA, scanner binaries by checksum, and vendor
  skills by a 40-character commit. Python tools are pinned to an exact version, but their
  transitive dependencies are not.
- **Gates on every PR:**
  - content lint (`scripts/lint_content.py`);
  - structure validation;
  - Cisco `skill-scanner` (fails on high or critical findings);
  - gitleaks across the full history;
  - zizmor on the workflows.
- **Repository rules:**
  - `main` changes only by PR (merge or squash), with passing checks and signed commits;
  - required checks count only when the GitHub Actions app posts them;
  - an outside PR needs the code owner's approval of its final commit, and any later push
    dismisses that approval;
  - every workflow run from a fork waits for the maintainer's approval;
  - only GitHub-owned actions and listed actions run, and each must be pinned to a SHA;
  - CodeQL scans the scripts and workflows (advisory);
  - no force-push;
  - release tags `v*` cannot be moved or deleted;
  - secret scanning with push protection is on.
- **Contributions go through an issue first.** CI on a PR runs that PR's own copy of the
  gates, so the maintainer re-runs main's gates on the PR's files. See
  [CONTRIBUTING.md](CONTRIBUTING.md).

## What it does not guarantee

Scanners can be evaded, and in 2026 every major skill scanner was bypassed. Treat any skill,
including these, as code that runs with your agent's permissions. Read a skill before you
install it, and pin it to a tag. `de-vendors` scans third-party skills before copying them, but
a passing scan is not proof that a skill is safe.
