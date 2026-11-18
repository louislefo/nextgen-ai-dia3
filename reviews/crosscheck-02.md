# Peer Cross-Check Log 02: TD 1 Reference Queries C07-C13

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 1 - Deterministic SQL Benchmark  
**Target Repository**: `nextgen-ai-dia3`  
**Target Files**: `td1/reference-td1.csv`, `td1/questions-td1.json`, `data/boutique.sqlite`  

> **Corrected on 2026-11-18 by Romain Thepaut (QA).** The seven reference values previously
> listed in this log matched neither `reference-td1.csv` nor the output of the SQL the log
> itself quoted. One of them, `248180` for C11, was carried over into
> `reviews/crosscheck-06.md` and audited there as a false consensus; C11's reference is
> `446690`. Every value below is now re-executed on `data/boutique.sqlite` and checked
> against `reference-td1.csv`, and the harness check `review_claims` fails the verification
> pass on any contradicted reference. Review scopes and auditor assignments are unchanged.

---

## Review 1: Single-Day Period and Reference-Date Age (C07-C09)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Jean Jaunet
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C07 (one day), C08 and C09 (completed age 25 on two different reference dates)

### Scope of Inspection
1. C07 closes the period family on a one-day window ending the month.
2. C08 and C09 ask the same question on two reference dates one day apart, which makes them
   the sharpest test of the age window in the benchmark.
3. Both age queries must use the anniversary test, never a year difference.

### Audit Procedure & Execution
```sql
-- C08, completed age 25 on 2026-09-24
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE date(c.birth_date, '+25 years') <= '2026-09-24'
  AND date(c.birth_date, '+26 years') > '2026-09-24';

-- C09, the same question on 2026-09-26
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE date(c.birth_date, '+25 years') <= '2026-09-26'
  AND date(c.birth_date, '+26 years') > '2026-09-26';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C07: `13970` cents (139.70 EUR)
   - C08: `605580` cents (6,055.80 EUR)
   - C09: `487980` cents (4,879.80 EUR)
2. **C08 and C09 differ by 117,600 cents for two reference dates two days apart**, and the
   per-customer breakdown explains every cent of it. Moving the reference date from
   2026-09-24 to 2026-09-26 shifts the eligible birth window by two days: C004
   (born 2000-09-25, 150,260) and C005 (born 2000-09-26, 150,240) turn 26 and leave, while
   C001 (born 2001-09-25, 135,000) and C003 (born 2001-09-26, 47,900) turn 25 and enter.
   `605580 - 300500 + 182900 = 487980`. A query using a year difference cannot reproduce
   both values, which is what makes the pair a boundary probe rather than a duplicate.
3. For C09 the eligible window is `2000-09-27 <= birth_date <= 2001-09-26`, six customers,
   and the per-customer breakdown totalling 487,980 is in
   `td2/pair-b/step2-wrong-consensus.sql`, query 4. C003, born exactly 2001-09-26, sits on
   the inclusive boundary.
4. C09 is the case where two models later agreed on a wrong `0` in TD 2. The reference is
   therefore load-bearing for the whole TD 2 argument, which is why it is re-derived by a
   third independent method (arithmetic completed age, no date window) in the same file.

### Verdict
**APPROVED** - the three values reproduce to the exact cent, and the C08/C09 pair behaves
as the boundary probe it is meant to be.

---

## Review 2: Age at Order Time, Late Reference Date and Product Lists (C10-C13)

### Metadata
- **Authors / Reviewees**: reference set authors (Louis Le Forestier, Jean Jaunet)
- **Auditor / Reviewer**: Baptiste Noailhac
- **Review Date**: 2026-10-21, values re-verified 2026-11-18
- **Target Cases**: C10 (age at the time of the order), C11 (age on 2026-12-01), C12 and C13 (product lists)

### Scope of Inspection
1. C10 is the only case where age is evaluated **at the order date** rather than on a fixed
   reference date, so the window is per order line.
2. C11 uses a reference date after the end of the data window, which must not change the
   method.
3. C12 has no period at all; C13 combines two products with a one-month window.

### Audit Procedure & Execution
```sql
-- C10, age at the time of each order: the window follows o.date
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE date(c.birth_date, '+25 years') <= date(o.date)
  AND date(c.birth_date, '+26 years') > date(o.date);

-- C13, products a and c only, April 2026
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o JOIN product p ON o.product_id = p.product_id
WHERE p.product_id IN ('a', 'c')
  AND o.date >= '2026-04-01 00:00:00' AND o.date < '2026-05-01 00:00:00';
```

### Verification Findings
1. Reference values re-executed and confirmed:
   - C10: `558980` cents (5,589.80 EUR)
   - C11: `446690` cents (4,466.90 EUR)
   - C12: `1666490` cents (16,664.90 EUR)
   - C13: `107740` cents (1,077.40 EUR)
2. **C10 is the hardest case of the benchmark and the reference proves why.** Because the
   age window follows `o.date`, a customer can contribute some of their orders and not
   others. In TD 2, qwen and Dots both returned `119410` by accepting only order lines
   where `year(order) - year(birth) = 25` and the order falls after the birthday, missing
   28 lines worth 439,570 cents placed before the birthday in the year of the 26th
   birthday. The reference query has no such hole: `date(birth_date, '+25 years')` is
   compared with `date(o.date)` line by line.
3. C11's reference date, 2026-12-01, is later than the last order (2026-09-20). The
   question still asks who is 25 **on that date**, so the eligible birth window shifts
   while the order set does not. 446,690 is lower than C12's unfiltered product total
   because only eligible customers contribute, which is consistent.
4. C12 has no date predicate, so it is the upper bound for products a, b and c over the
   whole dataset. Every other product-list case must come out below it: C03 (936,350),
   C13 (107,740), C14 (0) and C17 (258,180) all do.
5. No three-way join is accidental: `customers` is joined only in C10 and C11, where an
   age is required.

### Verdict
**APPROVED** - the four values reproduce to the exact cent, and C12 provides the
containment check that constrains every other product-list case.
