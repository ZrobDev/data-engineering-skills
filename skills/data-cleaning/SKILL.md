---
name: data-cleaning
description: Use when a new CSV, parquet or xlsx needs profiling before touching it, or when cleaning, deduping or normalizing records, coercing dates/currency/IDs, or reconciling a source of truth against a derived file (OCR'd or scanned documents vs a system export, an upload vs the DB). Covers row-count mismatches, lost leading zeros, duplicates, control totals, anti-joins, exceptions reports.
license: MIT
---

# Data cleaning and reconciliation

Default tools: DuckDB 2.0 SQL or polars 2.x lazy API (`scan_csv`, `scan_parquet`) for local files. pandas only when a library forces it. Python via uv, lint with ruff. Verify any API detail that changed in Polars 2.0 or DuckDB 2.0 against current docs before relying on it (see `references/landscape-2026-11.md`).

## Never silently fix

Every coercion, drop, default, or merge is counted and reported. A cleaning step is `(rows_in, rows_out, rows_changed, reason)`. Cast failures become NULL plus a count, never a dropped row and never a guessed value. Keep the raw input untouched; write cleaned output to a new path. If a step's counts surprise you, stop and report instead of continuing.

## Procedure

1. Profile (read-only). 2. Decide key, grain, and types. 3. Clean in a pipeline of small counted steps. 4. Reconcile if two sources exist. 5. Emit exceptions plus a run summary with every count.

## 1. Profile before touching

Read every column as text first (`all_varchar=true` in DuckDB, `infer_schema=False` in polars), because inference on a sample silently turns `00123` into `123` and mixed columns into the first row's type.
Then per column compute: row count, null/empty-string rate, distinct count, min/max (as text and as parsed), shortest/longest length, and share of values matching a type pattern (integer, decimal, ISO date, other).
DuckDB `SUMMARIZE` does most of this in one call.

Record before cleaning: total rows, distinct candidate-key count, rows per key (max), and the headers exactly as found (trailing spaces, BOM, duplicate names). A candidate key is only a key if distinct count equals row count after normalization; test it, do not assume.

Check for: whole-row duplicates, header repeated mid-file, footer/total rows inside the data, sentinel values ("N/A", "-", "0000-00-00", 9999-12-31), mixed encodings, and numeric columns that are really identifiers.

## 2. Types and parsing

- IDs, ZIP/postal codes, account and phone numbers are strings, always. Store zero-padded width as a rule (`lpad` to the known width) only when the width is documented; otherwise keep as read.
- Dates: parse with an explicit format per column (`try_strptime` / `str.to_date(format, strict=False)`). Never let the engine guess day/month order. Ambiguous values (`03/04/2026`) with no documented order are an exception, not a coin flip. Keep a timezone decision explicit.
- Money: parse to integer minor units or `DECIMAL(p,s)`, never float. Strip currency symbols and thousands separators by locale rule: `1.234,56` and `1,234.56` are different locales, so decide per source and assert that every value matches the chosen pattern. Parentheses and trailing minus are negatives. Record currency per row; do not sum across currencies.
- Booleans and enums: map from an explicit table; unmapped values go to exceptions.
- After each cast, count `non-null before` minus `non-null after`. That number is the coercion-failure count and goes in the report.

## 3. Normalization

Apply to a derived match key, not over the original column, so the raw value stays available:
Unicode NFKC, trim, collapse internal whitespace, casefold, strip zero-width and non-breaking spaces.
NFKC is lossy (ligatures, full-width forms, superscripts), which is the point for matching and wrong for display.
For identifiers also remove separators (`-`, `/`, spaces) and decide O/0 and I/1 handling explicitly.
NFKC is not in DuckDB core SQL; do it in polars/Python or register a UDF (verify current support).

## 4. Dedupe

- Exact duplicates: drop with a count; keep the surviving row's source row number.
- Duplicates by key: first decide whether they are true repeats or distinct events (same invoice number, different amount is a conflict, not a duplicate).
- Survivor choice must be deterministic and stated:
`ROW_NUMBER() OVER (PARTITION BY key ORDER BY updated_at DESC NULLS LAST, completeness DESC, source_row DESC) = 1` (DuckDB `QUALIFY`).
Always end the ORDER BY with a unique tiebreaker such as source row number, because ties otherwise resolve by arbitrary scan order.
In polars use `sort(...)` then `unique(subset, keep="first", maintain_order=True)`.
- Fuzzy dedupe is a candidate generator, never an auto-merge: block on a cheap key (normalized postal code, first 3 letters, year), score within blocks, auto-accept only above a high threshold with an exact secondary field agreeing, and send the middle band to a human list. Report threshold and counts.

## 5. Reconciliation audit

Source of truth = A, derived = B (e.g. system export vs OCR'd documents). Never say "B is wrong" before checking whether the extraction or the key is wrong.

1. **Control totals first.** Row count and sum of every money/quantity column in A and B, plus distinct key counts. A mismatch tells you whether to expect missing rows, extra rows, or amount drift. Totals that tie while rows differ means offsetting errors; keep going.
2. **Key matching.** Build the same normalized key on both sides (section 3). Match exactly first, then in explicit passes of decreasing strictness (e.g. key only, then key plus date window), labeling each match with the pass that produced it. Never mix passes unlabeled.
3. **Anti-joins both directions.** A-not-in-B (missing from derived) and B-not-in-A (unexpected in derived, often OCR key typos or duplicates). Report both; reading only one direction hides half the errors. Before calling a row missing, check whether its key collides with duplicates on either side (many-to-many joins inflate totals).
4. **Field comparison on matched pairs.** Compare per field after the same normalization.
Money tolerance: compare in minor units, `abs(a - b) <= tol` where tol is declared up front (0 for ledgers; a rounding tolerance such as 1 minor unit per line only when the sources round differently, and never a percentage on small amounts).
Dates: exact, or a stated day window.
Text: normalized equality, then a similarity score reported as a score, not as a pass.
5. **Classify, do not just diff.** Each exception gets one reason code: `MISSING_IN_B`, `EXTRA_IN_B`, `DUP_KEY_A`, `DUP_KEY_B`, `AMOUNT_MISMATCH`, `FIELD_MISMATCH`, `UNPARSEABLE_A`, `UNPARSEABLE_B`, `AMBIGUOUS_MATCH`. Unparseable rows are exceptions, never silently excluded from totals.
6. **Close the loop.** Final identity must hold: `|A| = matched + missing_in_B + dup_excess_A + unparseable_A` (and the B equivalent). If it does not balance, the audit is not finished.

SQL patterns for passes, anti-joins, tolerance, and the balance check are in `references/reconciliation-recipes.md`.

## Exceptions report

One row per exception, readable without the tooling:
`reason_code`, `key`, A source file and row number, B source file and row number (and page for scanned documents), `field`, `a_value`, `b_value`, `delta`, `suggested_action`.
Sort by money impact descending, then reason.
Put a run summary on top: inputs with row counts and checksums, every cleaning step with counts, control totals both sides, the balance identity, tolerances used.
Write CSV for the machine and a short markdown or xlsx view for the human; do not dump thousands of lines into chat, summarize counts by reason and show the top few.

## Guardrails

- Assert, do not eyeball: row counts after joins, key uniqueness after dedupe, no float columns for money.
- Left joins on non-unique keys multiply rows; check the count before and after every join.
- Do not overwrite A. Corrections to the source of truth are a human decision listed in the report.
- Secrets for databases are read from `/run/secrets/<name>`, not env vars or command lines.
- Declarative checks (soda-core, great_expectations) are worth adding once rules are stable; the profile and counts above come first.

Lessons from real use accumulate in `references/gotchas.md`.
