---
name: etl-pipelines
description: Use when designing, reviewing or debugging batch ETL/ELT in Python - duplicate or missing rows after a rerun, double-counted backfills, watermark gaps, late-arriving data, retry storms, schema drift breaking a load, scrape-to-warehouse pipelines, a job that silently loads zero rows, or choosing between cron, n8n, Airflow and dlt.
license: MIT
---

# ETL pipelines

Batch ingestion into PostgreSQL (default store) with Python (uv, ruff, pytest). Local transforms: polars 2.x or DuckDB 2.0.

## Procedure

1. State the grain: one row means what, identified by which natural key. No key, no idempotent load; define one (or a content hash) first.
2. Pick the load pattern (below). Pick the incremental strategy. Pick the orchestrator last.
3. Write the run so that rerunning any window gives the same end state. Prove it: run it twice in a test and assert row counts and a checksum are unchanged.
4. Add the observability checks (below) before the first production run.
5. Review against the checklist at the end.

## Idempotent load pattern

- Rows have a stable natural key and may change: `INSERT ... ON CONFLICT (key) DO UPDATE` (Postgres) or `MERGE`. Add `WHERE target.hash IS DISTINCT FROM excluded.hash` so unchanged rows do not churn.
- Data arrives as a whole partition (day, batch id) and is rewritten as a unit: delete-insert that partition in ONE transaction. A delete committed separately from the insert leaves a hole on crash.
- Whole table is rebuilt: load into a staging table, validate, then swap (rename in one transaction). Readers never see a half-loaded table.
- Append-only facts with no key: add a deterministic `batch_id` / source file hash and make the load refuse or replace an already-loaded batch id.
- Never `INSERT` blindly then dedupe later. Duplicates reach a dashboard before the dedupe runs.
- Load via `COPY` into a temp/staging table, then one set-based upsert. Row-by-row upserts from Python are 10-100x slower.

## Incremental loads

- Watermark on a column the source guarantees monotonic and indexed (updated_at, sequence id). Store it in a state table, written in the same transaction as the load, never in a file on the side.
- Read `watermark - lookback` (e.g. 1 to 24 h), not `> watermark`. Source commits are not ordered by timestamp; the lookback plus upsert absorbs late rows. Size the lookback from measured lateness, not a guess.
- Watermark column unreliable (not bumped on update, timezone mixed, soft deletes missing): do a periodic full reconcile (key set diff or count + checksum per partition) instead of trusting it.
- Hard deletes at the source are invisible to watermarks. Decide explicitly: reconcile by key diff, or accept and document.
- CDC (Postgres logical replication, Debezium-style log readers): use only when you need deletes, sub-minute latency, or the source cannot be queried by timestamp. It adds slots, retention risk (an idle slot fills the source disk), and ordering/snapshot handling. Otherwise stay with watermarks.

## Backfills

- Every job takes `--start` and `--end` (half-open `[start, end)`, UTC) and derives everything from them. No `now()` inside the transform.
- A backfill is the normal job run over old windows. If it needs different code, the normal job is not idempotent; fix that.
- Chunk by partition, run chunks independently, record per-chunk status, so a failure at chunk 40 resumes at 40.
- Backfill into the same target via the same upsert/partition replace. Check no double counting: `count(*)` and `count(distinct key)` per window before and after.
- Throttle against the source API/DB; a backfill is a self-inflicted load spike.

## Retries, timeouts, "exactly once"

- Exactly-once delivery does not exist across a network. Build at-least-once delivery plus idempotent writes; the result is effectively-once.
- Retry only idempotent steps, with exponential backoff and jitter, a cap on attempts, and a hard timeout on every network call (connect and read set separately). Retry on 429/5xx/timeouts, not on 4xx.
- Honor `Retry-After`. Retries without a global rate limit amplify an outage.
- A step that sends email, charges, or posts to a webhook is not idempotent: guard with an idempotency key stored before the call.
- On final failure exit non-zero and alert; never swallow the exception to keep a schedule green.

## Schema drift

- Landing layer is permissive (store raw payload as JSON/text plus load metadata). Typed layer is strict and fails loudly on type/required-field violations.
- New columns: additive and allowed with an alert. Dropped, renamed or retyped columns: fail the run and surface the diff; do not coerce to NULL.
- Validate with an explicit schema (polars schema, pydantic, or DuckDB `DESCRIBE`) at the boundary, once, not scattered through the transform.

## Scrape to warehouse

- Two stages. Stage 1 fetches and stores the raw response unchanged and immutable (object path keyed by source, fetch time, content hash). Stage 2 parses raw into tables.
- Parser bugs are then fixed by re-parsing stored raw, with no re-fetch, no ban risk, and no lost history.
- Record URL, fetch timestamp, HTTP status, parser version on every parsed row. Parse is a pure function of raw bytes plus parser version.
- Fetch failures and empty/blocked pages (captcha, 200 with a login wall) are detected by content checks, not status code alone.

## Observability (minimum)

- Log per step: rows read, rows written, rows rejected, duration, window start/end, run id. Structured (JSON) lines.
- Assert invariants: rows out vs in within a tolerance; zero rows on a window that is normally non-empty FAILS the run. A silent zero-row success is the most common undetected failure.
- Heartbeat: ping an external healthcheck on success and on start; alert on a missed ping (catches cron not firing, host down). Failure also pings the fail endpoint.
- Alert on freshness (max loaded timestamp older than threshold), not only on job errors.
- Keep a run-log table (run id, window, status, counts); it is also your backfill ledger.

## Choosing the orchestrator

- Cron (or systemd timer) + one script: one to a few independent jobs, no cross-job dependencies, a team that can read logs. Default. Needs the heartbeat above and a lock (`flock`) against overlapping runs.
- n8n: low volume, glue between SaaS APIs, webhook-triggered, non-developers edit flows. Poor fit for large batches, heavy transforms, or code review; keep heavy logic in a Python script it calls.
- Airflow 3.x: many DAGs, cross-job dependencies, first-class backfills, retries and SLAs, audit UI. Real operational cost (scheduler, metadata DB, workers); not worth it for a handful of jobs. Airflow 2 to 3 is a migration with breaking changes; check the version before copying a snippet. For dbt on Airflow use Astronomer Cosmos.
- dlt: API or database ingestion where you want schema inference, incremental state, and merge/replace dispositions handled for you. Use it instead of hand-writing paginated extract + watermark + upsert code; still apply the rules above to its config.
- Containers: secrets as Compose secrets read from /run/secrets/<name>, never env vars or env_file; bind published ports to 127.0.0.1 or keep them on an internal network.

## Vendor skills

When the task needs dbt or Airflow specifics (models, tests, DAG authoring, operators, Cosmos config), do not improvise: use the official vendor skills pulled in through this repo's `de-vendors` skill, and fall back to the version in `references/landscape-2026-11.md` only to check what is current.

## Review checklist

- Key and grain stated; rerun of the same window yields identical state (tested).
- Delete and insert in one transaction; watermark committed with the load.
- Lookback present; late data and deletes have an explicit answer.
- Timeouts, bounded retries with backoff, non-idempotent steps guarded.
- Raw landing immutable; parse separable and re-runnable.
- Row counts per step logged; zero-row and freshness alerts exist; heartbeat configured.
- Schema drift fails loudly in the typed layer.
- Orchestrator choice justified by job count and dependencies, not habit.

Concrete SQL and Python skeletons: `references/patterns.md`. Lessons from real use: `references/gotchas.md`.
