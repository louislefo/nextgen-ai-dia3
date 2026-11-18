# Peer Cross-Check Log 01: TD 1 Reference Queries C01-C06

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 1 - Deterministic SQL Benchmark  
**Target Repository**: `nextgen-ai-dia3`  
**Target Files**: `td1/reference-td1.csv`, `td1/questions-td1.json`, `data/boutique.sqlite`  

> **Corrected on 2026-11-18 by Romain Thepaut (QA).** The six reference values previously
> listed in this log matched neither `reference-td1.csv` nor the output of the SQL the log
> itself quoted, and the quoted C01 query filtered January instead of the March-to-June
> window of the actual question. Every value below is now re-executed on
> `data/boutique.sqlite` and checked against `reference-td1.csv`. The harness check
> `review_claims` fails the verification pass if any reference asserted in this directory
> contradicts the reference file. Review scopes and auditor assignments are unchanged.

---

## Review 1: Period, Reference-Date Age and Product List (C01-C03)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Maxime Laurent
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C01 (period), C02 (age on a reference date), C03 (product list and period)

### Scope of Inspection
1. The half-open convention `date >= S AND date < E` is applied to every period, so an
   order at exactly `E` is excluded and no order is counted twice across adjacent windows.
2. Completed age is computed from the anniversary, not from a year difference.
3. Revenue is `SUM(quantity_product * price)` over joined order lines, in euro cents.
4. `COALESCE(..., 0)` guarantees an integer rather than `NULL` when nothing matches.

### Audit Procedure & Execution
```sql
-- C01, re-executed read-only on data/boutique.sqlite
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
WHERE o.date >= '2026-03-01 00:00:00' AND o.date < '2026-06-01 00:00:00';

-- C02, completed age 25 on the reference date 2026-09-25
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE date(c.birth_date, '+25 years') <= '2026-09-25'
  AND date(c.birth_date, '+26 years') > '2026-09-25';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C01: `792800` cents (7,928.00 EUR)
   - C02: `590320` cents (5,903.20 EUR)
   - C03: `936350` cents (9,363.50 EUR)
2. C02 expresses completed age through `date(birth_date, '+25 years')` and
   `date(birth_date, '+26 years')`, which is the anniversary test the conventions require.
   A year difference (`strftime('%Y', ...)` subtraction) would include customers whose
   birthday falls after the reference date; TD 1 later showed three of the five models
   failing exactly there.
3. C03 combines a product filter (`product_id IN ('a','b','c')`) with a January-to-July
   window. The product filter is applied before aggregation, so no line of another product
   contributes.
4. No cartesian join: each query joins `orders` to `product` on `product_id`, and to
   `customers` on `customer_id` when an age is involved.

### Verdict
**APPROVED** - the three queries implement their questions, and the three values reproduce
on the database to the exact cent.

---

## Review 2: Period Boundaries and the Empty Window (C04-C06)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Louis Le Forestier
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C04, C05, C06 (three periods, including a single day and an empty window)

### Scope of Inspection
Audit the three period cases, which together fix the boundary behaviour of the whole
benchmark: a nine-month window, a single day, and a window with no data.

### Audit Procedure & Execution
```sql
-- C05, a single day: [2026-06-01, 2026-06-02)
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
WHERE o.date >= '2026-06-01 00:00:00' AND o.date < '2026-06-02 00:00:00';

-- C06, the year 2025: no order exists before 2026-01-05
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
WHERE o.date >= '2025-01-01 00:00:00' AND o.date < '2026-01-01 00:00:00';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C04: `2826250` cents (28,262.50 EUR)
   - C05: `38480` cents (384.80 EUR)
   - C06: `0` cents (0.00 EUR)
2. C06 is the case that proves the `COALESCE` requirement. The order window of the dataset
   is `2026-01-05` to `2026-09-20` (`data/manifest.json`), so the 2025 window matches no
   row. Without `COALESCE`, `SUM` returns `NULL` and the answer is unusable rather than
   zero. The expected answer is the integer `0`.
3. C05 confirms the half-open convention on the tightest possible window. Timestamps are
   compared as text in the format `YYYY-MM-DD HH:MM:SS`, so `'2026-06-01 09:12:00'` sorts
   inside `['2026-06-01 00:00:00', '2026-06-02 00:00:00')` as intended.
4. **Caveat worth recording**: comparing a timestamp column with a bare date string is not
   equivalent. `o.date > '2026-01-01'` keeps `'2026-01-01 00:00:00'`, because the longer
   text sorts after the shorter one. Pair B hit the same edge in TD 2 on the `DEMO-VOTE`
   illustration. The reference queries avoid it by always writing the full timestamp.

### Verdict
**APPROVED** - boundary semantics are correct on all three windows, including the empty
one, and the values reproduce to the exact cent.
