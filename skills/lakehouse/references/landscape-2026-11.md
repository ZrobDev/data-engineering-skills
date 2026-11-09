# Lakehouse landscape slice

As of 2026-11-09. Versions below were supplied by the repo maintainer; items marked (unverified) were not independently confirmed. Re-check release pages before citing a version to a user.

## Table formats

| Item | Version / state | Notes |
|---|---|---|
| Delta Lake | 4.4.0 (2026-08-20), 4.4.1 (2026-10-05) | Spark 4.x line. Docs: https://docs.delta.io |
| Apache Iceberg | 1.12.0 (2026-09-30) | v3 spec: deletion vectors, row lineage, variant type. v4 is in design discussion only. Docs: https://iceberg.apache.org |
| Iceberg v3 in Databricks Unity Catalog | GA, announced June 2026 | Other engines and catalogs support v3 unevenly (unverified); check each before upgrading a table's format version. |
| DuckLake | 1.1 (2026-10-21) | Catalog is a SQL database. Docs: https://ducklake.select |

## Engines and libraries

| Item | Version / state | Notes |
|---|---|---|
| DuckDB | 2.0.0 (2026-10-21) | Reads Delta and Iceberg via extensions; attaches DuckLake. https://duckdb.org |
| Apache Spark | 4.3.0 tagged about 2026-10-27 | Official announcement not confirmed (unverified); treat 4.2.x as the safe stated baseline until confirmed. https://spark.apache.org |
| pyiceberg | 0.12 | Python client for Iceberg catalogs and tables (unverified feature coverage for v3 writes). |
| Polars | 2.1 | Lazy scans of Delta and Iceberg. https://pola.rs |

## Catalog options

- Unity Catalog (Databricks, also an open-source project).
- AWS Glue Data Catalog and S3 Tables: https://docs.aws.amazon.com
- Iceberg REST catalog protocol; Apache Polaris is an implementation: https://polaris.apache.org
- DuckLake: Postgres, SQLite or DuckDB as the catalog database.

## Vendor specifics

Databricks, Snowflake and AWS service behavior is out of scope here; use the `de-vendors` skill.
