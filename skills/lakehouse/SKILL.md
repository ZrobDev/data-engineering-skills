---
name: lakehouse
description: Use when choosing or touching lakehouse storage - Postgres vs warehouse vs lakehouse, Delta vs Iceberg vs DuckLake, slow queries from small parquet files, partitioning, OPTIMIZE/VACUUM/expire_snapshots, MERGE or schema-evolution errors, catalog choice, PySpark collect()/UDF/shuffle/skew, or testing tables locally with DuckDB or polars.
license: MIT
---

# Lakehouse

Reference-grade decision support for open-table-format storage and Spark code. Versions and dates live in `references/landscape-2026-11.md`; check them before any version-specific claim. For Databricks, Snowflake or AWS service specifics, use the `de-vendors` skill and the official vendor skills it points to.

## 1. Is a lakehouse warranted?

Start from the cheapest option that fits and move up only when a listed trigger is real and measured.

- **Postgres (or DuckDB on one file set)** when data is under roughly 1 TB, one engine reads it, and concurrent analytical users are few. Reason: no catalog, no compaction, no cluster to run.
- **Cloud warehouse** when many SQL users need elastic concurrency and nobody needs a second engine on the same bytes. Reason: managed storage, maintenance and governance are included in the price.
- **Lakehouse** when at least one holds: tens of TB or more; several engines (Spark, Trino, DuckDB, Python) must read one copy; ML or file-based workloads share tables with SQL; storage cost on object storage clearly beats warehouse storage at your volume; open format is a hard requirement (exit, audit, vendor neutrality).
- Do not pick a lakehouse for a "future scale" that has no number attached. Ask for row counts, daily growth, concurrent readers and engines before recommending.
- Small and medium data that still wants open format: DuckLake or plain parquet plus DuckDB beats running Spark.

## 2. Parquet layout

- Target 128 MB to 1 GB per file; aim for 256 MB to 512 MB when unsure. Many files under 32 MB mean listing and open costs dominate the query.
- Row groups of roughly 128 MB uncompressed (1M+ rows) per file; smaller groups weaken min/max pruning and compression.
- Partition only by low-cardinality columns that queries filter on (date or month, region). A good partition holds at least one full target-size file per writer batch; if partitions average under 1 GB, use a coarser grain or clustering instead.
- Never partition by a high-cardinality id. Use clustering (Delta liquid clustering, Iceberg sort order / Z-order) for those columns.
- Sort or cluster within files on the most-filtered column so min/max statistics prune row groups.
- Streaming or frequent micro-batch writes create small files; schedule compaction, do not rely on writers to size files.

## 3. Choosing a table format

Decide by the engine and catalog you already have, not by feature lists.

- **Delta Lake**: pick when Databricks or Spark is the primary engine, or Unity Catalog is already the governance layer. Strongest Spark integration; other engines read it but write support varies.
- **Apache Iceberg**: pick when multiple engines must write, or you want vendor-neutral catalogs (REST). v3 adds deletion vectors, row lineage and a variant type; confirm that every engine and catalog in the path supports the v3 features you use before upgrading a table, because an old reader fails on a newer format version.
- **DuckLake**: pick for small and medium data, a single team, and a SQL database you already operate as the catalog (metadata lives in plain tables). Cheap to run, young ecosystem; do not choose it when Spark, Trino or Snowflake must write the same tables.
- Interoperability layers (Delta UniForm, Iceberg metadata for Delta tables) are read paths. Pick one format as the writer of record per table.
- Changing format later means a rewrite or metadata conversion; choose the writer of record deliberately.

## 4. Catalogs

- The catalog is the commit coordinator and the access-control point; pick it before the format details matter.
- Unity Catalog: the Databricks-centered default; governance for Delta and Iceberg.
- AWS Glue and S3 Tables: pick when the stack is AWS-native; S3 Tables manages compaction for you but ties you to AWS.
- Iceberg REST catalog (for example Polaris): pick for multi-engine, multi-cloud neutrality.
- DuckLake: the catalog is a SQL database; back it with Postgres for multi-user use, SQLite or DuckDB only for one writer.
- Never let two catalogs register the same table path; commits to one will corrupt the view of the other.

## 5. Maintenance (schedule it, or the table decays)

- Compact small files: Delta `OPTIMIZE`, Iceberg `rewrite_data_files`, DuckLake merge-adjacent-files. Run after heavy ingest, not per write.
- Remove old data: Delta `VACUUM`, Iceberg `expire_snapshots` plus orphan-file removal, DuckLake snapshot expiry then cleanup. Retention must exceed your longest reader or time-travel window, because deleting files under a running reader breaks it.
- Clustering or Z-order only for columns that appear in filters; re-clustering rewrites data and costs compute.
- Check file count and average file size before and after; a maintenance job that changes neither did nothing.
- Dry-run vacuum or orphan removal first where the engine offers it.

## 6. MERGE, schema evolution, time travel

- MERGE: dedupe the source on the match key first (duplicate source matches fail or double-apply). Include a partition or clustering predicate in the ON clause so the engine prunes files instead of scanning the table.
- Prefer append plus periodic MERGE or an idempotent key over repeated full-table MERGE on large tables.
- Schema evolution: additive columns are safe; renames and type widening depend on format and version (column mapping in Delta, field IDs in Iceberg). Check support in the readers that matter before renaming. Never enable automatic schema merge on a production pipeline input you do not control.
- Time travel is a debugging, audit and rollback tool, not a backup. It costs the retained files; the longer the retention, the more storage and slower metadata. Set retention deliberately and keep real backups of critical tables.

## 7. PySpark 4.x essentials

- Transformations are lazy; nothing runs until an action. Build one plan, trigger one write; repeated `count()` or `show()` re-run the whole plan unless you cache deliberately.
- Avoid `collect()`, `toPandas()` and `.rdd` on large data; they pull everything to the driver. Limit or aggregate first.
- Use built-in functions or SQL expressions over Python UDFs. UDFs block optimizer pushdown and serialize rows. If unavoidable, use a vectorized (Arrow) UDF.
- Wide operations (join, groupBy, window, distinct) shuffle. Filter and project before them; check the plan with `explain()`.
- Broadcast a small side of a join (`broadcast(df)`) when it fits in executor memory; do not broadcast an unbounded table.
- Adaptive Query Execution is on by default in Spark 4.x and handles partition coalescing, skew joins and join-strategy switching; tune after reading the plan, not before.
- Skew shows as one slow task; salt or isolate the hot key only after AQE proves insufficient.
- Spark Connect is the client-server mode: code runs as a thin client over a remote session. Do not rely on driver-local JVM internals (`sparkContext`, RDD APIs) in Connect code.
- Write with an explicit target file size via compaction, not by repartitioning to a guessed number.

## 8. Local-first path

Develop and test on DuckDB or polars before paying for a cluster.

- DuckDB reads Delta and Iceberg through extensions and attaches DuckLake catalogs; polars reads Delta and Iceberg lazily with predicate pushdown.
- Use a sample or one partition against the real table layout so file-pruning behavior matches.
- Confirm write semantics (MERGE, deletion vectors, v3 features) on the real engine; local readers may lag format features. Treat a successful local read as necessary, not sufficient.

## Procedure

1. Get the numbers: size, growth, writers, readers, engines. 2. Walk section 1; stop at the cheapest fit. 3. If lakehouse: choose catalog, then format (sections 4, 3). 4. Set layout and a maintenance schedule before first load. 5. Prototype locally (section 8), then run on the cluster with `explain()` output reviewed. 6. Verify with file counts and query plans, not assumptions.

Known pitfalls and fixes: see `references/gotchas.md`.
