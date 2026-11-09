# Fan-out and reconciliation checks

Portable SQL (PostgreSQL, BigQuery, Snowflake, DuckDB). Replace names in the examples with the model's own.

## 1. Grain uniqueness

```sql
select order_line_id, count(*) as n
from fct_order_lines
group by 1
having count(*) > 1;          -- must return zero rows
```

## 2. Join did not change row count

```sql
select
  (select count(*) from stg_orders)                                  as before_join,
  (select count(*) from stg_orders o left join dim_customer c
     on o.customer_id = c.customer_id)                               as after_join;
-- equal, or the dimension key is not unique
```

## 3. Dimension join key is unique

```sql
select customer_id, count(*) from dim_customer group by 1 having count(*) > 1;
```
For an SCD2 dimension this returns many rows by design; join on the validity range and test one match per fact row instead:

```sql
select f.order_id, count(d.customer_id) as matches
from fct_orders f
left join dim_customer_history d
  on d.customer_id = f.customer_id
 and f.ordered_at >= d.valid_from and f.ordered_at < d.valid_to
group by 1 having count(d.customer_id) <> 1;
```
The left join keeps facts that fall in a gap in the history (0 matches) as well as overlaps (2 or more).

## 4. Measure reconciles to source

```sql
select
  (select sum(amount) from stg_payments where status = 'settled') as source_total,
  (select sum(amount_usd) from fct_payments)                      as mart_total;
```
Compare with an explicit tolerance; investigate any difference before shipping.

## 5. Header measure repeated on lines (mismatched grain)

Symptom: `sum(order_total)` over a line-grain table exceeds the sum over the header table. Fix by moving header measures to a header-grain fact, or allocating them to lines with a documented rule.

## 6. SCD2 range integrity

```sql
select a.customer_id
from dim_customer_history a
join dim_customer_history b
  on a.customer_id = b.customer_id and a.valid_from < b.valid_to
 and b.valid_from < a.valid_to and a.customer_key < b.customer_key;  -- overlaps
```
Pair rows by the version's surrogate key (`customer_key`), not by `valid_from`; two versions starting at the same instant still overlap.
Also assert one row with `is_current` per `customer_id`.
