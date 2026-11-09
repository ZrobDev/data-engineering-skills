# Landscape slice: ETL / orchestration (as of 2026-11-09)

Versions below are as stated by the repo maintainers on 2026-11-09. Mark anything you cannot confirm as unverified before relying on it.

| Component | Version | Note |
|---|---|---|
| Apache Airflow | 3.4.0 (released 2026-11-06) | Airflow 2 to 3 is a breaking migration (task SDK, removed/changed imports, new API server). Verify DAG snippets target 3.x. |
| astro CLI | 1.47.0 | Local Airflow dev and deploy tooling. |
| dlt | 1.32.0 (2026-10-29) | Python ingestion library: schema inference, incremental state, merge/replace dispositions. |
| DuckDB | 2.0.0 | Local/analytical transforms; reads Parquet, CSV, Postgres. |
| Polars | 2.1.0 | DataFrame engine for local transforms. |
| dbt | v2 (Rust engine, formerly Fusion), GA 2026-06 | Use the official vendor skills for dbt specifics. |
| n8n | self-hosted, version unverified | Check the running instance version before citing node behaviour. |
| Astronomer Cosmos | version unverified | Renders dbt projects as Airflow tasks. |
| PostgreSQL | version unverified | Default store; `ON CONFLICT` upsert, `COPY`, logical replication available in all supported majors. |

Docs: https://airflow.apache.org/ , https://dlthub.com/docs , https://docs.n8n.io , https://docs.getdbt.com , https://duckdb.org/docs , https://docs.pola.rs , https://www.postgresql.org/docs/ .
