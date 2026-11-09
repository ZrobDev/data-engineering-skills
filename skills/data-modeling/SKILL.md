---
name: data-modeling
description: Use when designing or reviewing an analytical model (star schema, marts, fact/dimension tables), when metrics double-count or inflate after a join, when choosing surrogate vs natural keys or SCD type 1 vs 2, when deciding raw/staging/intermediate/mart layering, naming, or which tests a model needs, and for PostgreSQL OLTP schema review (normalization, FK indexes, multi-tenant keys).
license: MIT
---

# Data modeling

Targets: PostgreSQL, BigQuery, Snowflake. Transformation: dbt. Local prototyping: DuckDB 2.0.
For dbt mechanics (model config, tests YAML, snapshots, semantic layer, v2 migration) use the official dbt Labs skills pulled in by this repo's `de-vendors` skill. This skill decides what to model, not how dbt spells it.

## Procedure

1. State the business question and the consumer (dashboard, ML feature, finance close).
2. Write the grain as one sentence before any column: "One row per order line per day." If the sentence needs "or", it is two tables.
3. Pick the fact type (below), then list dimensions that are true at that grain.
4. Name the grain key (natural columns or a hash of them). It gets unique + not_null.
5. Prototype in DuckDB on a sample, run the fan-out checks, then port.
6. Add the tests listed under "What to test" before declaring done.

## Grain

- Grain first, columns second. Every measure and every foreign key must be single-valued at the grain; a column that is not belongs in another table, because it silently multiplies rows.
- Keep the lowest grain the source supports. Aggregates are derivable from detail, detail is not derivable from aggregates. Build rollups as separate marts.
- Never mix grains in one table (order header totals repeated on order-line rows). Header amounts summed over line rows double-count; model header and line facts separately.

## Facts vs dimensions

- Fact: an event or measurement; numeric, additive where possible, keyed by dimension keys plus degenerate dimensions (order number).
- Dimension: descriptive context used to filter and group. Wide and denormalized is fine.
- Classify each measure: additive (sum across all dims), semi-additive (balances: not across time), non-additive (ratios: store numerator and denominator, divide after aggregation).
- Fact types:
  - Transaction: one row per event. Default choice.
  - Periodic snapshot: one row per entity per period (daily balance). Use when state matters and events are sparse or late.
  - Accumulating snapshot: one row per process instance with a date column per milestone, updated in place. Use for pipelines with a known lifecycle (order placed, shipped, delivered). Expect updates; make the load idempotent.
  - Factless fact: events or coverage with no measure (attendance, eligibility). Count rows.

## Schema shape

- Star by default: one fact, flat dimensions. Snowflake (normalized dimensions) only when a sub-dimension is shared and large or maintained by another team; the extra joins cost readability and BI-tool compatibility.
- Conformed dimensions: one `dim_customer`, `dim_date` shared by every fact, same keys and attribute meanings. Build them once; a second customer table with different rules is a defect, because cross-fact reports then disagree.
- Role-playing dimensions (order_date, ship_date) reuse one `dim_date` via separate FK columns.
- Junk/mini dimensions for low-cardinality flags; do not leave 8 booleans on the fact.
- Unknown member: keep a row (key `-1` or hash of 'unknown') in each dimension so late-arriving facts keep their rows. Inner joins to dimensions drop facts silently; use left joins and a coalesce to the unknown key.

## Keys

- Natural key: the source system's business identifier. Keep it as an attribute always.
- Surrogate key: add one when natural keys are composite, can change, come from several sources, or the dimension is SCD2 (one entity has many versions). In dbt-style warehouses prefer a deterministic hash of the natural key (plus valid_from for SCD2) over sequences, so reruns and parallel builds agree.
- Do not expose surrogate keys to business users as identifiers; they change on rebuild.

## Slowly changing dimensions

- Type 1 (overwrite): when history has no analytic value or the change is a correction.
- Type 2 (new row per version, valid_from / valid_to / is_current): when facts must be reported with the attribute value as of the event time (customer tier at purchase).
- Snapshots suffice when the source keeps no history and you only need to capture changes going forward; they are the capture mechanism, the SCD2 dimension is still a model on top. If the source already has history or an event log, derive validity ranges from it instead of snapshotting.
- Join facts to SCD2 on key plus `event_ts >= valid_from and event_ts < valid_to` (half-open ranges, so no overlap). Test for no overlapping or gapped ranges per natural key.
- Type 3 or per-attribute type 2: only when a single "previous value" column answers the question; otherwise skip.

## Fan-out and double counting

Cause: joining tables at mismatched grains so the "one" side is really many. Symptoms: totals larger than source, `count(*)` grows after a left join, averages shift.
- Detect: compare `count(*)` and `count(distinct grain_key)` before and after every join; they must be equal after a join to a dimension. Test uniqueness of the join key on the dimension side (`select key from dim group by 1 having count(*) > 1`).
- Reconcile: sum of the measure in the mart equals the sum in the source for the same filter.
- Fix by aggregating the many side to the fact's grain before joining, or joining through a bridge table with allocation weights; never `distinct` the result to hide it.
- Many-to-many (customer to account, product to category): bridge table with a weighting factor, or choose a primary and say so.
- SQL for these checks: see references/fan-out-checks.md.

## Layering

- raw/staging: one staging model per source table; rename, cast, dedupe, no joins, no business logic. Keep raw immutable.
- intermediate: joins, reshaping, shared logic reused by 2+ marts. Not exposed to BI.
- marts: facts and dimensions, one business process per mart, documented, tested, contracted. Only marts are public.
- Dependencies flow one way; marts do not read raw, and staging never reads staging.
- Materialize staging as views, marts as tables (incremental when large and the grain key is stable).

## Naming

- `stg_<source>__<entity>`, `int_<entity>_<verb>`, `fct_<process>`, `dim_<entity>`; snake_case; plural or singular consistently (pick one).
- Keys `<entity>_id` (natural) and `<entity>_key` (surrogate); timestamps `<event>_at` in UTC; dates `<event>_date`; booleans `is_` / `has_`; amounts carry a unit or currency (`amount_usd`).

## What to test

- Grain key: unique + not_null, on every model; for composite grains test the combination.
- Every FK on a fact: not_null (or unknown member) and a relationships test to the dimension.
- Accepted values on status/type columns; a new value fails loudly rather than being miscategorized.
- Row-count and sum reconciliation of each mart to its source, with a stated tolerance (zero for finance).
- SCD2: no overlapping ranges, exactly one current row per natural key.
- Freshness on sources. Break each test once on sample data to prove it can fail.

## OLTP schema review (PostgreSQL)

- Normalize to 3NF for transactional tables; denormalize only for a measured read path. Every table has a primary key.
- Index foreign-key columns: Postgres does not do it automatically, and unindexed FKs make parent deletes and joins scan the child table.
- Use `timestamptz`, `numeric` for money, `text` over arbitrary varchar limits; enforce rules with NOT NULL, CHECK, UNIQUE, and FK constraints rather than app code alone.
- Prefer `bigint` identity or UUIDv7 keys over random UUIDv4 for large insert-heavy tables (index locality).
- Multi-tenant: put `tenant_id` on every tenant-owned table, make it the leading column of composite keys and indexes, include it in FKs (composite FK) so cross-tenant references are impossible, and back it with row-level security. Shared schema with tenant_id by default; schema- or database-per-tenant only for hard isolation or per-tenant restore needs.
- Soft deletes: partial unique indexes (`where deleted_at is null`) so uniqueness still holds.

Pitfalls and observed failure modes: references/gotchas.md
