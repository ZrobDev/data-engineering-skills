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
- **No hooks.** No skill pre-approves bare `Bash` or `Bash(*)`. Agents state their model
  and tools explicitly.
- **Pinned everything.** GitHub Actions are pinned by SHA, scanner binaries by checksum,
  Python tools by exact version, and vendor skills by a 40-character commit.
- **Gates on every PR:**
  - content lint (`scripts/lint_content.py`);
  - structure validation;
  - Cisco `skill-scanner` (fails on high or critical findings);
  - gitleaks across the full history;
  - zizmor on the workflows.
- **Repository rules:**
  - `main` changes only by PR, with passing checks and signed commits;
  - no force-push;
  - release tags `v*` cannot be moved or deleted;
  - secret scanning with push protection is on.

## What it does not guarantee

Scanners can be evaded, and in 2026 every major skill scanner was bypassed. Treat any skill,
including these, as code that runs with your agent's permissions. Read a skill before you
install it, and pin it to a tag. `de-vendors` scans third-party skills before copying them, but
a passing scan is not proof that a skill is safe.
