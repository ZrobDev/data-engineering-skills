# Reconciliation recipes (DuckDB SQL)

Assumes tables `a` (source of truth) and `b` (derived) loaded as text, then typed into `a_t` and `b_t` with a derived `key`, `amount_minor` (BIGINT), and `src_row`. Verify syntax against current DuckDB 2.0 docs.

## Typed load with coercion counts
```sql
CREATE TABLE a AS SELECT *, row_number() OVER () AS src_row
FROM read_csv('a.csv', all_varchar=true);

CREATE TABLE a_t AS
SELECT src_row,
       upper(regexp_replace(trim(id), '[\s\-/]', '', 'g')) AS key,
       try_strptime(inv_date, '%Y-%m-%d')::DATE AS inv_date,
       TRY_CAST(round(TRY_CAST(replace(amount, ',', '') AS DECIMAL(18,4)) * 100) AS BIGINT) AS amount_minor,
       id AS raw_id, inv_date AS raw_date, amount AS raw_amount
FROM a;

-- coercion failures (non-empty raw, NULL parsed): report these, never drop them
SELECT 'date' AS col, count(*) FROM a_t WHERE raw_date <> '' AND inv_date IS NULL
UNION ALL
SELECT 'amount', count(*) FROM a_t WHERE raw_amount <> '' AND amount_minor IS NULL;
```
The `replace(amount, ',', '')` form assumes a `1,234.56` locale. For `1.234,56` strip `.` then swap `,` for `.`. Pick per source and assert the pattern with `regexp_matches` over every value.

## Control totals
```sql
SELECT 'A' AS side, count(*) AS n, count(DISTINCT key) AS n_keys, sum(amount_minor) AS total FROM a_t
UNION ALL
SELECT 'B', count(*), count(DISTINCT key), sum(amount_minor) FROM b_t;
```

## Duplicate keys per side (resolve before joining)
```sql
SELECT key, count(*) AS n FROM a_t GROUP BY key HAVING count(*) > 1 ORDER BY n DESC;
```
Pick survivors deterministically, keep the rest as `DUP_KEY_*` exceptions:
```sql
CREATE TABLE a_u AS SELECT * FROM a_t
QUALIFY row_number() OVER (PARTITION BY key ORDER BY inv_date DESC NULLS LAST, src_row DESC) = 1;
```

## Anti-joins, both directions
```sql
SELECT a.* FROM a_u a ANTI JOIN b_u b USING (key);   -- MISSING_IN_B
SELECT b.* FROM b_u b ANTI JOIN a_u a USING (key);   -- EXTRA_IN_B
```

## Matched pairs with tolerance
```sql
SELECT a.key, a.src_row AS a_row, b.src_row AS b_row,
       a.amount_minor AS a_amt, b.amount_minor AS b_amt,
       b.amount_minor - a.amount_minor AS delta
FROM a_u a JOIN b_u b USING (key)
WHERE a.amount_minor IS DISTINCT FROM b.amount_minor
  AND abs(b.amount_minor - a.amount_minor) > 0;      -- replace 0 with the declared tolerance
```
Use `IS DISTINCT FROM` so NULL on one side is a mismatch rather than silently dropped.

## Second pass for unmatched rows (labeled)
```sql
SELECT a.key AS a_key, b.key AS b_key, 'PASS2_AMOUNT_DATE' AS pass
FROM (SELECT a.* FROM a_u a ANTI JOIN b_u b USING (key)) a
JOIN (SELECT b.* FROM b_u b ANTI JOIN a_u a USING (key)) b
  ON a.amount_minor = b.amount_minor AND abs(date_diff('day', a.inv_date, b.inv_date)) <= 3;
```
Treat a row matching more than one candidate as `AMBIGUOUS_MATCH`, not as a match. Near-miss keys (one character off) found this way are the usual signature of extraction typos; list them for a human.

## Balance identity
```sql
SELECT (SELECT count(*) FROM a_t) AS total_a,
       (SELECT count(*) FROM a_u JOIN b_u USING (key)) AS matched,
       (SELECT count(*) FROM a_u ANTI JOIN b_u USING (key)) AS missing_in_b,
       (SELECT count(*) FROM a_t) - (SELECT count(*) FROM a_u) AS dup_excess_a;
-- unparseable rows (null key) are counted separately; total_a must equal the sum of all buckets
```

## Export
```sql
COPY (SELECT * FROM exceptions ORDER BY abs(delta) DESC NULLS LAST, reason_code)
TO 'exceptions.csv' (HEADER, DELIMITER ',');
```
