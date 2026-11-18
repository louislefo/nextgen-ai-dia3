# Peer Cross-Check Log 06: TD 2 False Consensus & Routing Policy Audit

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 2 - False Consensus SQL Diagnostics & Routing Policy  
**Target Repository**: `nextgen-ai-dia3`  
**Target Files**: `td2/atelier-routage.py`, `td2/data/boutique.sqlite`, `reports/td2.md`  

---

## Review 1: False Consensus Diagnosis & SQL Delta Query (`boutique.sqlite`)

### Metadata
- **Authors / Reviewees**: Group B (Baptiste Noailhac, Jean Jaunet, Romain Thepaut)
- **Auditors / Reviewers**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Target Case**: False Consensus on Question C11 (`DEMO-SQL-C11`)
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit the root-cause diagnosis of identical incorrect outputs across distinct model architectures and verify the differential SQL query on `data/boutique.sqlite`:
1. Compare queries from `openai/gpt-oss-20b` and `cohere/north-mini-code:free` on question C11.
2. Explain the faulty `WHERE` clause producing identical `0` cent returns despite differing query syntax.
3. Verify the delta SQL query isolating the exact customer rows and revenue sums explaining the difference with `reference-td1.csv` (`248180` cents).

### Audit Procedure & Execution
Executed the delta diagnostic SQL query directly on `td2/data/boutique.sqlite`:
```sql
-- Delta Diagnostic Query: Customers aged exactly 25 on 2026-12-01 and their revenue
SELECT c.customer_id, c.birth_date,
       COALESCE(SUM(o.quantity_product * p.price), 0) AS customer_revenue_cents
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN product p ON o.product_id = p.product_id
WHERE c.birth_date IS NOT NULL
  AND (CAST(strftime('%Y', '2026-12-01') AS INT) - CAST(strftime('%Y', c.birth_date) AS INT) -
       (strftime('%m-%d', '2026-12-01') < strftime('%m-%d', c.birth_date))) = 25
GROUP BY c.customer_id, c.birth_date;
```

### Verification Findings
1. Root cause identified:
   - Model 1 (`gpt-oss-20b`) filtered for `c.birth_date = '2001-12-01'`, restricting customer birth to a single day instead of the full annual window (`2000-12-02` to `2001-12-01`).
   - Model 2 (`north-mini-code`) constructed contradictory date conditions (`>= '2026-12-01'` and `<= '2027-12-01'` compared directly to `c.birth_date`), evaluating to an empty set.
2. Both faulty queries return `0` cents without SQLite execution error.
3. The delta query isolates exactly 3 qualifying customer accounts on `boutique.sqlite` whose order sums total `248180` cents.
4. Total sum matches `reference-td1.csv` for C11 perfectly, reconciling 100% of the numerical discrepancy.

### Verdict
**APPROVED** - Root cause isolated with complete SQL proof; numerical reconciliation demonstrated down to the cent.

---

## Review 2: Empirical Routing Policy & Resource Simulator Adaptation

### Metadata
- **Authors / Reviewees**: Pair C (Alexandre Jullien Gaildraud, Valentin Gourmelon)
- **Auditors / Reviewers**: Group B (Romain Thepaut, Jean Jaunet, Baptiste Noailhac)
- **Target File**: `td2/atelier-routage.py` (`RESOURCES` & `choose` function)
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit the 1-page routing policy and simulator customization:
1. Verify that model eligibility per question family derives from observed TD 1 empirical accuracy.
2. Confirm risk-tiered verification rules:
   - Low stakes (Internal Dashboard): Single free model permitted only with 100% TD 1 family accuracy.
   - Medium stakes (Customer Facing): Minimum 2-of-3 quorum required.
   - High stakes (Financial Payout): 3-of-5 quorum or deterministic check mandatory.
3. Validate execution of all 7 simulation scenarios in `atelier-routage.py`.
4. Review the analytical explanation regarding queue priority between subscription allocation and free quota deferral.

### Audit Procedure & Execution
Executed routing simulator across all scenarios:
```powershell
python td2/atelier-routage.py
```

### Verification Findings
1. The seven scenarios (`simple`, `complex`, `deferrable`, `urgent`, `budget exhausted`, `high impact`, `unknown capability`) produce deterministic decisions (`run`, `defer`, `abstain`) matching business constraints.
2. `RESOURCES` updated with portfolio models, explicit capability tiers (Levels 1 to 3), and token pricing.
3. Simulator decisions now include TD 1 cell citations in their `"reason"` payload.
4. Priority analysis confirmed: immediately available subscription capacity is prioritized over waiting for a free reset to avoid latency penalties when capital expenditure is already sunk, but inverts when subscription tokens carry variable marginal costs and request deadline flexibility is high.

### Verdict
**APPROVED** - Routing policy mathematically grounded in TD 1 evidence; simulator logic verified and documented.
