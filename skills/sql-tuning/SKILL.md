---
name: sql-tuning
description: Use when a SQL query is slow, a plan shows Seq Scan or bad row estimates, EXPLAIN ANALYZE output needs reading, an index choice is unclear, OFFSET pagination degrades, an ORM issues N+1 queries, pg_stat_statements needs triage, or a BigQuery/Snowflake query scans too much. Postgres first.
license: MIT
---

# SQL tuning (PostgreSQL first)

Measure before changing anything. A tuning change without a before/after plan and timing is a guess.

## Procedure

1. Find the target: rank by total cost, not by the single slowest call (see triage loop).
2. Capture the baseline: `EXPLAIN (ANALYZE, BUFFERS) <query>` on production-sized data. Tiny dev data picks different plans.
3. Locate the node where time or rows go wrong (reading rules below). Fix that node only.
4. Re-run the same plan capture. Keep the change only if it wins on both time and buffers.
5. Record the index or rewrite and why, next to the schema migration.

Wrap `EXPLAIN ANALYZE` of INSERT/UPDATE/DELETE in `BEGIN; ... ROLLBACK;` because ANALYZE really executes the statement.

## Reading a plan

- Read bottom-up, inner nodes first. Per-node `actual time` is per loop; multiply by `loops` for the real cost.
- Compare `rows` (estimate) to `actual rows`. A gap of 10x or more is the root cause far more often than a missing index: run `ANALYZE <table>`, raise the column statistics target, or add extended statistics (`CREATE STATISTICS ... (dependencies, ndistinct)`) for correlated columns.
- `Rows Removed by Filter` much larger than rows returned means the index (or lack of one) is not selective for this predicate.
- `Buffers: shared read` is disk or OS cache; `shared hit` is shared_buffers. High reads on repeat runs means the working set does not fit.
- `Sort Method: external merge Disk:` means work_mem was too small for this sort. Raise it per session or per role, not globally, because it multiplies per sort node per connection.
- `Nested Loop` with a large inner `loops` count and an unindexed inner side is the classic slow join. `Hash Join` spilling (`Batches: >1`) is the same work_mem story.
- Seq Scan is correct when the query reads a large fraction of the table. Do not add an index to remove a Seq Scan that returns 20% of rows.
- `Heap Fetches` on an Index Only Scan means the visibility map is stale; run VACUUM on the table.

## Choosing an index

Index only the predicate, join, or ORDER BY you measured. Every index costs write time, WAL, and vacuum work.

- btree: default for equality, range, sort. Column order: equality columns first, then the range or sort column. Skip scan in PG 18 helps some leading-column-missing cases, but do not design around it.
- Partial (`WHERE status = 'open'`): when queries target a small, stable slice (open items, not-yet-processed rows). The query's WHERE must imply the index predicate.
- Covering (`INCLUDE (col)`): when an index-only scan would remove heap fetches for a hot query. Included columns are not searchable keys.
- Expression (`ON (lower(email))`, `ON ((payload->>'id'))`): when the query applies a function to the column. The query must use the identical expression.
- BRIN: for huge append-only tables where the column correlates with physical order (timestamps, serial ids). Tiny index, coarse pruning. Check `pg_stats.correlation` near 1; if it is low, BRIN will not prune.
- GIN: jsonb containment, arrays, full text. GiST: ranges, geometry, exclusion constraints.
- Create on live tables with `CREATE INDEX CONCURRENTLY`; it cannot run inside a transaction block and a failed run leaves an INVALID index to drop.
- Drop unused indexes only after checking `pg_stat_user_indexes.idx_scan` over a full business cycle (month-end for finance workloads) and on replicas too.

## Sargability

A predicate can use an index only if the indexed column stands alone on one side.

- `WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'` instead of `WHERE extract(year from created_at) = 2026` or `date_trunc(...) = ...`.
- `WHERE col = $1` with matching types; `numeric_col = '5'::text` style casts on the column side block the index. Cast the parameter, not the column.
- Avoid leading-wildcard `LIKE '%x'`; use `pg_trgm` GIN or full text search.
- `OR` across different columns often loses the index; try `UNION ALL` of two indexed branches.
- `NOT IN (subquery)` is NULL-hostile and slow; use `NOT EXISTS`.
- Prefer `EXISTS` for semi-joins over `DISTINCT` after a join, because it stops at the first match and does not duplicate rows.

## Window functions vs self-joins

Use a window function when the goal is a per-row value from related rows in the same set: running totals, rank, lag/lead, "latest row per key" (`row_number() OVER (PARTITION BY k ORDER BY ts DESC) = 1`), because one scan and one sort replace a join of the table to itself.
Use a self-join or LATERAL only when the second side needs its own filter or an index probe (top-N per key from a large table: `JOIN LATERAL (SELECT ... ORDER BY ts DESC LIMIT 3)` with an index on `(k, ts DESC)`).
`DISTINCT ON (k) ... ORDER BY k, ts DESC` is the short Postgres form for latest-per-key.

## CTEs

Since PG 12, a non-recursive, side-effect-free CTE referenced once is inlined like a subquery. Write for readability by default.
- Add `AS MATERIALIZED` when the CTE is expensive and referenced several times, or when you must stop the planner pushing a bad predicate into it.
- Add `AS NOT MATERIALIZED` to force inlining of a multiply-referenced CTE when the outer filter makes it cheap.
- Data-modifying CTEs always run once; they are not optimised away.

## pg_stat_statements triage loop

Requires `pg_stat_statements` in `shared_preload_libraries` (restart) and `CREATE EXTENSION`.
1. Order by `total_exec_time DESC` (also check `shared_blks_read`, `temp_blks_written`, `rows`). A 5 ms query called 40M times beats a 30 s nightly query.
2. Take the top 3. For each, get a real parameter set (the statistics are normalised) and run step 2 of the procedure.
3. Fix, deploy, then `SELECT pg_stat_statements_reset(<userid>, <dbid>, <queryid>)` for that query only, wait a representative window, compare.
4. Repeat until the top entry is a justified cost. Stop there.
Pair with `auto_explain` (`log_min_duration`, `log_analyze` sparingly) to catch plans for queries you cannot reproduce.

## PL/pgSQL only where it earns its place

Use a function or procedure when it removes round trips for row-by-row logic that cannot be set-based, enforces a trigger invariant, or encapsulates a multi-statement transaction. Do not use it to
loop over rows issuing one UPDATE each: rewrite as one `UPDATE ... FROM` or `INSERT ... SELECT`. Mark pure functions `IMMUTABLE`/`STABLE` correctly (a wrong label yields wrong cached results or blocks
inlining). Prefer plain SQL functions where possible so the planner can inline them.

## N+1 and pagination

- N+1: one query per parent row from application or ORM code. Fix with a single `WHERE id = ANY($1)` batch, a join, or the ORM's eager-load option. Detect via pg_stat_statements: one normalised statement with `calls` close to the parent row count.
- OFFSET pagination reads and discards all skipped rows, so page N costs O(N). Use keyset: `WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT 50` with an index on `(created_at DESC, id DESC)`. The tiebreaker column is mandatory or rows are skipped or repeated. Keyset cannot jump to page N; use OFFSET only for small bounded sets.
- `count(*)` on big tables is a full scan; show approximate counts (`reltuples`) or cap with `SELECT count(*) FROM (SELECT 1 ... LIMIT 10001)`.

## Bulk ETL notes

Batch loads with `COPY` (or `INSERT ... SELECT`) rather than row inserts; drop or defer secondary indexes only for large initial loads, then `ANALYZE` after. Large UPDATEs bloat tables: batch by key range, commit per batch, and let autovacuum keep up.

## Other dialects (short)

- BigQuery: cost is bytes billed, not rows. Partition on a date/timestamp column and filter it with a literal or parameter so pruning happens; cluster on the next most-filtered columns. `SELECT *` bills every column; name columns. Use dry run to see bytes before running. `LIMIT` does not reduce bytes billed.
- Snowflake: pruning uses micro-partition min/max metadata, so filter on columns whose values are naturally ordered on load; check "partitions scanned vs total" in the query profile. Add a clustering
  key only for very large tables with a stable filter pattern, because reclustering costs credits. Scale warehouse size up for spilling (local/remote spill in the profile), scale out (multi-cluster) for
  queueing/concurrency. Auto-suspend short.

Current versions and doc links: references/landscape-2026-11.md. Lessons from real use: references/gotchas.md.
