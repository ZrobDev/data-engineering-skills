# Patterns (PostgreSQL + Python)

## Upsert from staging (idempotent, skips unchanged rows)

```sql
CREATE TEMP TABLE stage (LIKE target INCLUDING DEFAULTS) ON COMMIT DROP;
-- COPY rows into stage here (psycopg copy), then:
INSERT INTO target AS t (id, payload, row_hash, updated_at)
SELECT id, payload, row_hash, updated_at FROM stage
ON CONFLICT (id) DO UPDATE
  SET payload = excluded.payload, row_hash = excluded.row_hash, updated_at = excluded.updated_at
  WHERE t.row_hash IS DISTINCT FROM excluded.row_hash;
```

Duplicate keys inside one batch make `ON CONFLICT DO UPDATE` error; dedupe the batch first (keep latest per key).

## Partition replace (one transaction)

```sql
BEGIN;
DELETE FROM facts WHERE event_date >= :start AND event_date < :end;
INSERT INTO facts SELECT ... FROM stage;
-- assert inserted count > 0 or window is known-empty, else ROLLBACK
COMMIT;
```

## Watermark committed with the load

```sql
-- same transaction as the upsert
INSERT INTO etl_state (job, watermark) VALUES (:job, :new_wm)
ON CONFLICT (job) DO UPDATE SET watermark = excluded.watermark;
```

Compute `:new_wm` as the max source timestamp actually read, not `now()`. Next run reads from `watermark - lookback`.

## Table swap

```sql
BEGIN;
ALTER TABLE report RENAME TO report_old;
ALTER TABLE report_new RENAME TO report;
DROP TABLE report_old;
COMMIT;
```

Validate `report_new` (row count, key uniqueness, null rates) before this transaction.

## Run-log table

```sql
CREATE TABLE etl_run (
  run_id uuid PRIMARY KEY, job text, win_start timestamptz, win_end timestamptz,
  status text, rows_in bigint, rows_out bigint, rows_rejected bigint,
  started_at timestamptz, finished_at timestamptz
);
```

## Retry skeleton (stdlib)

```python
import random, time

def retry(fn, attempts=5, base=1.0, cap=60.0, retry_on=(TimeoutError, ConnectionError)):
    for i in range(attempts):
        try:
            return fn()
        except retry_on:
            if i == attempts - 1:
                raise
            time.sleep(min(cap, base * 2 ** i) * random.uniform(0.5, 1.0))

if __name__ == "__main__":
    calls = []
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError
        return "ok"
    assert retry(flaky, base=0.0) == "ok" and len(calls) == 3
    def dead():
        raise TimeoutError
    try:
        retry(dead, attempts=2, base=0.0)
        raise SystemExit("should have raised")
    except TimeoutError:
        pass
```

## Idempotency test shape (pytest)

Run the job over a window, snapshot `(count(*), count(distinct key), checksum)`, run it again, assert the snapshot is identical. Then run an overlapping window and assert no key count grows.
