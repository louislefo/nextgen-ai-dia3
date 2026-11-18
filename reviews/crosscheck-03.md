# Peer Cross-Check Log 03: TD 1 SQL References (Part 3 - C14 to C20)

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 1 - Ground-Truth SQL References Verification  
**Target Repository**: `nextgen-ai-dia3`  
**Database**: `data/boutique.sqlite` (Seed `20260925`, SHA-256 verified)  

---

## Review 1: Questions C14 to C17 (Volume Constraints & Status Aggregations)

### Metadata
- **Author / Reviewee**: Alexandre Jullien Gaildraud
- **Auditor / Reviewer**: Valentin Gourmelon
- **Target Artifact**: `reference-td1.csv` (Rows C14, C15, C16, C17)
- **Review Date**: 2026-10-21

### Scope of Inspection
Audit aggregations involving order volumes, multi-item quantities, and status filtering:
- **C14**: Revenue of orders placed in Q1 2026 (`2026-01-01` to `2026-04-01`).
- **C15**: Revenue of orders placed in Q2 2026 (`2026-04-01` to `2026-07-01`).
- **C16**: Revenue of orders containing strictly more than 3 units of product `b`.
- **C17**: Revenue of orders placed by customers located in postal area code starting with `75`.

### Audit Procedure & Execution
Executed independently on `data/boutique.sqlite`:
```sql
-- Audited Query for C16
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o
JOIN product p ON o.product_id = p.product_id
WHERE o.product_id = 'b' AND o.quantity_product > 3;
```

### Verification Findings
1. For C14 and C15, multi-month quarterly interval boundaries align seamlessly with preceding single-month intervals.
2. For C16, the volume threshold `o.quantity_product > 3` evaluates integer quantities without converting to floating point.
3. For C17, postal code prefix pattern matching uses `c.postal_code LIKE '75%'` properly.
4. Calculated ground truth values confirmed:
   - C14: `1109570` cents (11,095.70 EUR)
   - C15: `1084200` cents (10,842.00 EUR)
   - C16: `254800` cents (2,548.00 EUR)
   - C17: `612400` cents (6,124.00 EUR)

### Verdict
**APPROVED** - Quarterly date intervals and volume thresholds execute with complete arithmetic precision.

---

## Review 2: Questions C18 to C20 (Edge Cases & Zero-Match Boundary Intervals)

### Metadata
- **Author / Reviewee**: Valentin Gourmelon
- **Auditor / Reviewer**: Alexandre Jullien Gaildraud
- **Target Artifact**: `reference-td1.csv` (Rows C18, C19, C20)
- **Review Date**: 2026-10-21

### Scope of Inspection
Audit edge cases involving narrow intervals, dynamic age at order time, and boundary checks:
- **C18**: Revenue of orders placed in May 2026 by customers who were exactly 25 years old at order time.
- **C19**: Revenue of product `d` in September 2026 for customers exactly 25 years old on `2026-09-25`.
- **C20**: Revenue of orders placed from `2026-06-01` to `2026-09-01`.

### Audit Procedure & Execution
Executed independently on `data/boutique.sqlite`:
```sql
-- Audited Edge Query for C18
SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN product p ON o.product_id = p.product_id
WHERE o.date >= '2026-05-01 00:00:00' AND o.date < '2026-06-01 00:00:00'
  AND (CAST(strftime('%Y', o.date) AS INT) - CAST(strftime('%Y', c.birth_date) AS INT) -
       (strftime('%m-%d', o.date) < strftime('%m-%d', c.birth_date))) = 25;
```

### Verification Findings
1. In C18, dynamically binding age to `o.date` inside the narrow May window returns positive revenue without null errors.
2. For C19, product `d` combined with customer age 25 accurately resolves single-order matching.
3. For C20, three-month boundary aggregation produces exact total revenue.
4. Calculated ground truth values confirmed:
   - C18: `62480` cents (624.80 EUR)
   - C19: `1990` cents (19.90 EUR)
   - C20: `1106090` cents (11,060.90 EUR)

### Verdict
**APPROVED** - Dynamic order-time age arithmetic and multi-condition edge queries fully verified.
