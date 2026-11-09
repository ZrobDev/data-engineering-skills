# data-engineering-skills

A small set of data-engineering [Agent Skills](https://code.claude.com/docs/en/skills), plus a
low-cost subagent team. The skills cover what official vendor skills don't. Vendor skills are
pulled per project, pinned to a commit and security-scanned, so they aren't copied in here.

| Skill | Use it for |
|---|---|
| `sql-tuning` | Slow queries: Postgres first (`EXPLAIN`, indexes, `pg_stat_statements`), with BigQuery/Snowflake notes |
| `data-cleaning` | Profiling, dedupe, type coercion and reconciliation audits, with polars and DuckDB |
| `etl-pipelines` | Idempotent and incremental loads, backfills, scrape-to-warehouse, choosing an orchestrator |
| `data-modeling` | Grain, star schema, SCD2, fan-out traps, OLTP schema review |
| `lakehouse` | Parquet, Delta, Iceberg, DuckLake, Spark basics (reference material) |
| `de-vendors` | Pull official dbt, Astronomer, Databricks, Snowflake, AWS, DuckDB, dlt or Azure skills into one project |
| `de-orchestrate` | Fan work out to the agent team below |

| Agent | Model | Role |
|---|---|---|
| `de-scout` | haiku | Read-only profiling and recon; returns JSON |
| `de-builder` | sonnet | Implements one spec'd unit and runs its check |
| `de-reviewer` | sonnet | Read-only review: grain, idempotency, cost, PII |

## Install

**Claude Code plugin (skills and agents):**

```text
/plugin marketplace add ZrobDev/data-engineering-skills
/plugin install data-engineering@zrobdev-data
```

**Skills only, via [skills.sh](https://skills.sh).** Pin the CLI version and pick one skill at a time:

```text
pnpm dlx skills@1.7.4 add ZrobDev/data-engineering-skills --skill sql-tuning
npx skills@1.7.4 add ZrobDev/data-engineering-skills --skill sql-tuning
```

Agents are not installed by skills.sh. To use `de-orchestrate`, install the plugin, or copy
`agents/*.md` into `.claude/agents/`.

To pin a release, check out a tag (`v0.1.0`). Tags are immutable (see SECURITY.md).

## Vendor skills on demand

Inside a project, ask Claude to "pull the dbt skills", or run the script directly:

```text
python3 skills/de-vendors/scripts/pull_vendor.py list
python3 skills/de-vendors/scripts/pull_vendor.py skills dbt
python3 skills/de-vendors/scripts/pull_vendor.py add dbt running-dbt-commands adding-dbt-unit-test --project .
```

Each skill is fetched at the SHA pinned in `skills/de-vendors/vendors.toml`. It is then
checked for symlinks and binaries and scanned with
[cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner).
If the scan passes, it is copied to `.claude/skills/` and recorded in
`.claude/de-vendors.lock.json`. Vendor CLI and MCP install lines are printed for you to review;
they are never run for you.

## How this repo changes

Skills change only when they fail in a real session. Open an issue labeled `skill-feedback`
that describes what the agent did and what it should have done. The fix lands in that skill's
`references/gotchas.md` or `SKILL.md`, gets a CHANGELOG entry, and ships in a new tag. See
`AGENTS.md`. To contribute, open an issue first: [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

This repo is plain text only. CI blocks binaries, archives, Office files, pipe-to-shell
commands, base64 blobs, URLs outside `scripts/url-allowlist.txt`, oversized files, plugin
hooks, and wildcard tool grants. It runs the Cisco skill scanner, gitleaks and zizmor on every
PR. To report a problem, see [SECURITY.md](SECURITY.md).

MIT licensed. Third-party notices: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
