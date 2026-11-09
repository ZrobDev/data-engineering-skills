# Landscape slice for data-cleaning (as of 2026-11-09)

Versions: DuckDB 2.0.0 (2026-10-21), Polars 2.0.0 (2026-10-06) and 2.1.0 (2026-10-25). Docs: https://duckdb.org and https://pola.rs. Both are major releases; treat anything below marked "verify" as unconfirmed against current docs.

## Defaults
- Local analysis over CSV, parquet, xlsx: DuckDB SQL or polars lazy. Python tooling via uv and ruff.
- pandas only when a downstream library requires a DataFrame; convert at the edge.
- PostgreSQL when the cleaned result must live in a database.

## DuckDB features this skill relies on (long-standing, verify names after 2.0)
- `read_csv(..., all_varchar=true)`, `sniff_csv`, `SUMMARIZE <table or query>`.
- `TRY_CAST`, `try_strptime`, `QUALIFY` with `ROW_NUMBER()`, `ANTI JOIN`, `FULL OUTER JOIN`.
- Excel reading via the `excel` extension (`read_xlsx`). Verify it is available and which options exist before use.
- Parquet via `read_parquet`, `COPY ... TO ... (FORMAT parquet)`.

## Polars features this skill relies on (verify against 2.x docs)
- `scan_csv(..., infer_schema=False)`, `scan_parquet`, `.collect()`, `group_by`, `join(how="anti")`, `unique(subset=..., keep=..., maintain_order=True)`.
- `str.to_date(format, strict=False)`, `str.strip_chars()`, `str.normalize("NFKC")` exists in recent versions; verify in 2.x.
- Streaming execution engine options changed over the 1.x line; verify the current flag before relying on out-of-core runs.

## Declarative checks
- dlt 1.32 (2026-10-29) for loading with schema contracts; soda-core and great_expectations are pip packages for declarative data checks. Add after the manual profile has settled the rules.
