# Peer Cross-Check Log 03: TD 1 Reference Queries C14-C20

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 1 - Deterministic SQL Benchmark  
**Target Repository**: `nextgen-ai-dia3`  
**Target Files**: `td1/reference-td1.csv`, `td1/questions-td1.json`, `data/boutique.sqlite`  

> **Corrected on 2026-11-18 by Romain Thepaut (QA).** The four reference values previously
> listed in this log matched neither `reference-td1.csv` nor the output of the SQL the log
> itself quoted, and its scope mentioned volume thresholds and postcodes, which do not
> exist in this schema: `product`, `customers` and `orders` hold ten columns in total and
> no postcode. The scopes below are the families the questions actually belong to, and every
> value is re-executed on `data/boutique.sqlite` and checked against `reference-td1.csv`.
> The harness check `review_claims` fails the verification pass on any contradicted
> reference. Auditor assignments are unchanged.

---

## Review 1: Compound Filters, Product plus Age plus Period (C14-C17)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Valentin Gourmelon
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C14 (product list, empty window), C15 (period + age), C16 (age + product list), C17 (period + age + product list)

### Scope of Inspection
These four cases are where the three primitive filters combine. The audit checks that each
compound query is the conjunction of its parts, with no predicate silently dropped, and
that the compound results stay consistent with the single-filter cases they refine.

### Audit Procedure & Execution
```sql
-- C17, the full conjunction: three products, a six-month window, completed age 25
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE p.product_id IN ('a', 'b', 'c')
  AND o.date >= '2026-01-01 00:00:00' AND o.date < '2026-07-01 00:00:00'
  AND date(c.birth_date, '+25 years') <= '2026-09-25'
  AND date(c.birth_date, '+26 years') > '2026-09-25';

-- C14, products a, b, c in a window that holds no order
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
WHERE p.product_id IN ('a', 'b', 'c')
  AND o.date >= '2026-10-01 00:00:00' AND o.date < '2026-12-01 00:00:00';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C14: `0` cents (0.00 EUR)
   - C15: `168680` cents (1,686.80 EUR)
   - C16: `376740` cents (3,767.40 EUR)
   - C17: `258180` cents (2,581.80 EUR)
2. **Containment holds wherever the cases are actually nested**, which is the cheapest
   cross-check available on compound queries:
   - C17 (258,180) < C16 (376,740): C17 is C16 restricted to a six-month window.
   - C16 (376,740) < C12 (1,666,490): C16 is C12 restricted to eligible customers.
   - C15 (168,680) < C01 (792,800): C15 is the same March-to-June window restricted to
     eligible customers.

   C15 and C17 are *not* nested in each other, since C17 adds a product filter over a
   wider window, so their values are not comparable and no inequality is asserted between
   them.
3. C14 returns `0` for the same reason as C06: the dataset holds no order after
   2026-09-20, so an October-to-December window matches nothing. Two independent empty
   cases in the benchmark means a model that omits `COALESCE` fails twice.
4. In C16 there is no period at all, only a product list and an age. The reference query
   joins all three tables but applies no date predicate, which matches the question.

### Verdict
**APPROVED** - the four values reproduce to the exact cent and satisfy the containment
relations with the single-filter cases they refine.

---

## Review 2: Age at Order Time in a Window, Rare Product, Closing Period (C18-C20)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Alexandre Jullien Gaildraud
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C18 (period + age at the time of the order), C19 (product d + period + age), C20 (period)

### Scope of Inspection
1. C18 is the second case evaluating age **at the order date**, this time inside a period,
   so the two predicates must not be collapsed into one reference date.
2. C19 filters a single product, `d`, which appears in few orders, so the expected result
   is small and any missing predicate shows up as a large overshoot.
3. C20 closes the period family on the last three months of data.

### Audit Procedure & Execution
```sql
-- C18, age at the order date, inside May 2026
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.date >= '2026-05-01 00:00:00' AND o.date < '2026-06-01 00:00:00'
  AND date(c.birth_date, '+25 years') <= date(o.date)
  AND date(c.birth_date, '+26 years') > date(o.date);

-- C19, product d only, September 2026, completed age 25 on 2026-09-25
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE p.product_id = 'd'
  AND o.date >= '2026-09-01 00:00:00' AND o.date < '2026-10-01 00:00:00'
  AND date(c.birth_date, '+25 years') <= '2026-09-25'
  AND date(c.birth_date, '+26 years') > '2026-09-25';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C18: `62480` cents (624.80 EUR)
   - C19: `1990` cents (19.90 EUR)
   - C20: `1106090` cents (11,060.90 EUR)
2. **C19 is the sensitivity case of the benchmark.** At 1,990 cents it is the smallest
   non-zero reference, so dropping any one of its three predicates multiplies the answer
   rather than nudging it. TD 2 bore this out: `north-mini-code` returned 13,930 (seven
   times the reference) and qwen 83,580 (forty-two times), while the three models that kept
   all three predicates returned 1,990 exactly.
3. C18 keeps the period and the per-line age test separate, as the question requires. Note
   it is the only compound case where all five models were correct in TD 1, which makes the
   single-cell "100%" on that family weak evidence rather than a demonstrated strength.
4. C20 is disjoint from C01 (`[2026-03-01, 2026-06-01)` against
   `[2026-06-01, 2026-09-01)`), and the two windows share no order. Their sum, 1,898,890,
   is below the nine-month total of C04 (2,826,250), which is the containment check for the
   period family.

### Verdict
**APPROVED** - the three values reproduce to the exact cent, and the disjointness of C01
and C20 inside C04 confirms the half-open convention across adjacent windows.
