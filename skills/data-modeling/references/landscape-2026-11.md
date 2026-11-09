# Landscape slice: data modeling (as of 2026-11-09)

- dbt: v2 (Rust engine, formerly named Fusion) GA since 2026-06. dbt Core stays on v1. Model design in this skill is engine-independent; for v2 migration steps use the dbt Labs skills via `de-vendors`.
- dbt-mcp: about 1.9 (approximate, unverified).
- DuckDB: 2.0.0, used here for local prototyping of models and fan-out checks before porting to the warehouse.
- Apache Iceberg v3: GA in Databricks Unity Catalog. Relevant only if marts land on lakehouse tables; modeling rules are unchanged. Other engines' v3 support unverified.
- PostgreSQL, BigQuery, Snowflake: modeling guidance here is version-independent. Specific current versions not verified for this skill.
