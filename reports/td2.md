# TD 2 Report: Quorum Voting and Routing Policy

**Sub-group**: DIA 3  
**Course**: Next-Generation AI - Trustworthy Generative AI (ESILV S7)  
**Session Date**: 2026-11-18  
**Pack Version**: `2026-10-14-students-1`  

---

## 1. Objectives & Scope

TD 2 implements and evaluates:
- A $k$-of-$n$ majority quorum mechanism within `skeleton-multi-llm-en.py`.
- Analysis of consensus behaviors, disagreement handling, and identification of false consensus occurrences.
- Development and empirical testing of a production routing rule based on difficulty, latency, and cost trade-offs.

---

## 2. Quorum Implementation & Threshold Testing

- **Panel Selection**: Three complementary model families evaluated in parallel.
- **Vote Algorithm**: Extraction and normalization of SQL execution results, majority detection, and abstention rules.
- **Validation**: Test coverage across synthetic test cases (`atelier-vote.py`) and historical TD 1 execution traces.

---

## 3. Step 2: Wrong consensus (Pair B: Baptiste Noailhac, Jean Jaunet; support: Romain Thepaut)

**Source:** real TD 1 traces (`td2/traces-td1.csv`, 104 rows, all `nature = real`), last attempt per (provider, model), giving 100 cells. Nothing here is synthetic, except the DEMO-VOTE illustration, which is marked as such.
**SQL evidence:** `td2/pair-b/step2-wrong-consensus.sql`, executed on `td2/data/boutique.sqlite`.

### 3.1 Search: shared wrong values in the 100 cells

| Question | Shared wrong value | Models agreeing | Reference | 2-of-3 panel (k=2) | 3-of-5 quorum (k=3) |
|---|---|---|---|---|---|
| **C09** | **0** | north-mini-code, qwen3.8-27b | 487980 | **Wrong consensus: 0 wins** (2 votes) | Abstains (487980: 2, 0: 2, dots `sql_rejected`) |
| C02 | 0 | gpt-oss-20b, north-mini-code | 590320 | 590320 wins (120b + qwen) | 590320 wins (120b + qwen + dots) |
| C10 | 119410 | qwen3.8-27b, dots-3-note-preview | 558980 | Abstains (558980 / 0 / 119410, 1 vote each) | Abstains (558980: 2, 119410: 2, 0: 1) |

Fixed panel: `openai/gpt-oss-120b` (Groq), `cohere/north-mini-code:free` (OpenRouter), `qwen/qwen3.8-27b` (Groq). GPT-OSS 20B and Dots are in the TD 1 five but not in the panel.

**Main case: C09.** It is the only case where the wrong value **wins the fixed 2-of-3 panel**: two of the three panel members agree on 0. Moving to 3-of-5 brings in GPT-OSS 20B, which is correct (487980), and Dots, whose answer is rejected (`sql_rejected`, markdown fence): Dots stays in n but does not vote. The tie at 2-2 is below k = 3, so the quorum **abstains** instead of publishing a wrong figure.

### 3.2 Identification (C09)

- **Question:** revenue excl. VAT, in cents, from customers aged exactly 25 on 2026-09-26, across all their orders. Family F2.
- **Agreeing models:** `cohere/north-mini-code:free`, `qwen/qwen3.8-27b`, both with `verdict = incorrect`, `value = 0`, HTTP 200, 1 attempt.
- **Independent reference:** 487980 (`reference-td1.csv`), confirmed by a separate arithmetic age computation (query 5).
- **Other votes:** gpt-oss-120b = 487980 (correct), gpt-oss-20b = 487980 (correct), dots = `sql_rejected`.

### 3.3 Faulty SQL diagnosis

Correct window: aged 25 on 2026-09-26 ⇔ `2000-09-27 <= birth_date <= 2001-09-26`.

- **north-mini-code:** its "age" expression is `CAST(SUBSTR(birth_date,1,4) AS INTEGER) - CASE ... END`, which is the **birth year** minus a correction (about 2000 to 2001). It never subtracts from 2026. `... = 25` is false for every customer, so 0 rows and `COALESCE(SUM, 0) = 0`.
- **qwen3.8-27b:** two bugs. (1) It uses `o.date` (the order date) instead of the reference date 2026-09-26, which is F2b logic applied to an F2 question. (2) `strftime('%m-%d', date(birth_date, '+26 years'))` gives back the birth month-day, so `md >= birth_md AND md < birth_md` is a contradiction, and 0 rows are kept (checked: `COUNT(*) = 0`).

**Key finding:** two *different* bugs produce the *same* value. 0 acts as an attractor: any empty filter combined with `COALESCE(SUM(...), 0)` returns 0. Agreement on 0 is therefore weak evidence. Two models can agree without sharing any reasoning.

### 3.4 Delta diagnostic query (executed)

Both faulty queries keep no row, so the delta is the whole reference population:

| customer_id | birth_date | orders | revenue_cents |
|---|---|---|---|
| C007 | 2000-11-30 | 6 | 118740 |
| C009 | 2001-03-10 | 5 | 61330 |
| C008 | 2001-05-15 | 7 | 99090 |
| C002 | 2001-09-24 | 3 | 25920 |
| C001 | 2001-09-25 | 8 | 135000 |
| C003 | 2001-09-26 | 4 | 47900 |
| **Total** | | | **487980 = 487980 − 0** ✓ |

C003 (born 2001-09-26, turning 25 that day) sits on the inclusive boundary. It is the row a strict `<` would drop.

**Independent check:** query 5 computes the completed age arithmetically (`2026 − birth_year − (birth_md > '09-26')`) with no date window, and returns 487980. Three methods agree: the reference, the delta total and the arithmetic age.

### 3.5 Secondary case C10 (non-zero wrong consensus)

qwen and dots both return 119410 (reference 558980). Both only accept orders where `year(order) − year(birth) = 25` and the order comes after the birthday. They miss orders placed **before the birthday in the year of the 26th birthday**, when the customer is still 25. qwen's second branch (`year diff = 24`) would be age 23 and matches 0 rows. Delta: 28 order lines (C004, C005, C007, C022) totalling **439570 = 558980 − 119410** ✓. Neither quorum validates it: both abstain.

### 3.6 DEMO-VOTE (invented teaching example, not a model output)

One sale on `2026-01-01 00:00:00` for 100 cents, period [01-01, 01-02). Proposals `[0, 0, 100]`, reference 100, k = 2 of 3: the quorum **validates 0**. SQLite caveat we found: `date > '2026-01-01'` still returns 100, because `'2026-01-01 00:00:00' > '2026-01-01'` is true in text comparison. The boundary loss only appears with `date > '2026-01-01 00:00:00'`.

### 3.7 Consequence for checking

- A 2-of-3 panel is **not sufficient** for F2 questions: C09 shows it publishing a wrong figure.
- 3-of-5 abstained correctly on C09 and C10. An abstention is safe but gives no answer, so for a figure shown to a customer or a payout, F2/F2b need a **deterministic reference query** (or human review), not only a quorum.
- An agreed value of **0** should trigger an extra check (row count > 0, or a sanity query), since empty filters converge on it.
- Limitation: 20 questions × 5 models support a batch-specific hypothesis only, not a general error rate.

---

## 4. Sub-group Routing Rule

- Routing policy definition linking query complexity categories to the lowest-cost capable model.
- Evaluation across the seven operational scenarios of `atelier-routage.py`.
