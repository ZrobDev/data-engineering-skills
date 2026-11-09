# Landscape for sql-tuning (as of 2026-11-09)

- PostgreSQL 18 is the current stable major (18.6 released 2026-08-13 per the project's versions page). PostgreSQL 19 reached RC 1 on 2026-10-15; check current version before assuming GA. PostgreSQL 14 reaches end of life on 2026-11-12.
- PG 18 items relevant to tuning (verify against release notes before relying on them): btree skip scan, EXPLAIN ANALYZE reporting buffers by default, asynchronous I/O (`io_method`), improved planner handling of some OR/IN and self-join cases.
- Stable since PG 12: CTE inlining with MATERIALIZED / NOT MATERIALIZED; since PG 11: covering indexes with INCLUDE; extended statistics since PG 10.
- pg_stat_statements: column names `total_exec_time`, `mean_exec_time` (PG 13+). Check the docs for your major.
- BigQuery and Snowflake: behaviour described in SKILL.md is long-standing; not re-verified for 2026-11. Check current version of each product's docs.

Docs: https://www.postgresql.org/docs/current/using-explain.html , https://www.postgresql.org/docs/current/pgstatstatements.html , https://use-the-index-luke.com , https://cloud.google.com/bigquery/docs/best-practices-performance-compute , https://docs.snowflake.com/en/user-guide/performance-query
