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

## 4. Step 3: Routing rule (Pair C)

**Source:** real TD 1 traces (`td2/traces-td1.csv`, 104 rows, `nature = real`), last attempt per (provider, model, case), giving 100 cells, the same rule as Pairs A and B. Prices come from `td1/portefeuille-modeles-2026-09-28.csv`. Simulator outputs are labelled `nature = simulation`: quota states are scenario inputs, not measurements.
**Evidence:** `td2/atelier-routage.py` (adapted), `td2/pair-c/simulator-before.jsonl`, `td2/pair-c/simulator-after.jsonl`. You can rebuild the rate table with `python3 atelier-routage.py --rates`.

### 4.1 Exact TD 1 rate per family (correct / cases)

| Family | TD 1 cells | gpt-oss-120b (Groq) | gpt-oss-20b (Groq) | qwen3.8-27b (Groq) | north-mini-code:free (OR) | dots-3-note:free (OR) |
|---|---|---|---|---|---|---|
| **F1** period | C01 C04 C05 C06 C07 C20 | **6/6** | **6/6** | 5/6 (C20 HTTP 429) | **6/6** | **6/6** |
| **F2** age at a date | C02 C08 C09 C11 | **4/4** | 2/4 (C02, C11 wrong) | 3/4 (C09 = 0) | 0/4 | 3/4 (C09 `sql_rejected`) |
| **F2b** age at the order | C10 | **1/1** | **1/1** | 0/1 | 0/1 | 0/1 |
| **F3** product list | C03 C12 C13 C14 | **4/4** | **4/4** | **4/4** | **4/4** | **4/4** |
| F1+F2 | C15 | **1/1** | **1/1** | 0/1 | 1/1 | 0/1 |
| F2+F3 | C16 | **1/1** | **1/1** | 0/1 (429) | 1/1 | 0/1 |
| F1+F2+F3 | C17 C19 | **2/2** | **2/2** | 0/2 | 0/2 | 1/2 (C17 rejected) |
| F1+F2b | C18 | **1/1** | **1/1** | 1/1 | 1/1 | 1/1 |
| **Total** | 20 | **20/20** | 18/20 | 13/20 | 13/20 | 15/20 |

**Eligibility rule** (how we read the table):
1. 100 % means correct / **cases**, not correct / executed. A 429 counts as a miss, so qwen is not eligible on F1 (5/6).
2. A combination inherits the failures of its components. north-mini-code is right on C15 and C16, but it scores 0/4 on F2, so we do not trust it on any family that contains an age. With one or two cells per combination, a lucky hit is weaker evidence than four failures on the component.

| Family | Eligible routes (100 % in TD 1) |
|---|---|
| F1 | gpt-oss-20b, north-mini-code, dots, gpt-oss-120b |
| F3 | all five |
| F2b, F1+F2b | gpt-oss-20b, gpt-oss-120b |
| F2, F1+F2, F2+F3, F1+F2+F3 | **gpt-oss-120b only** |

### 4.2 The rule (one page)

All five TD 1 models are **free** routes (portfolio G5, 0 USD), so equal cost is broken by sending the **smallest eligible model first**. This keeps the Groq quota of gpt-oss-120b, the only model at 20/20, for the families where nothing else qualifies. Free order: qwen3.8-27b → gpt-oss-20b → north-mini-code → dots → gpt-oss-120b. Paid fallback: `openai/gpt-oss-120b` on OpenRouter (portfolio G4, 0.15 / 0.60 USD per M tokens, which is **0.000711 USD/request** for a 641 in + 1024 out envelope). It is the same model, but TD 1 measured it on Groq, so this route never runs without a check.

| Family | First model called | If unavailable | Dashboard (internal) | Figure shown to customer | Amount paid out |
|---|---|---|---|---|---|
| F1 | gpt-oss-20b (6/6) | north → dots → 120b → wait for refill / paid 120b → abstain | **none** (6/6) | 2-of-3 quorum of eligible free models | 3-of-5 quorum **and** reference query, human sign-off on mismatch |
| F3 | qwen3.8-27b (4/4) | 20b → north → dots → 120b → … | **none** (4/4) | 2-of-3 quorum (all five at 4/4) | 3-of-5 quorum **and** reference query |
| F2b, F1+F2b | gpt-oss-20b (C10 1/1, C18 1/1) | 120b → wait / paid 120b → abstain | none + zero-value guard | reference query; abstain + review on mismatch | reference query **and** human sign-off |
| F2 and combinations with F2 | gpt-oss-120b (F2 4/4, C15–C17, C19) | wait for Groq refill if it can wait → paid 120b within budget → abstain | none + zero-value guard | reference query; abstain + review on mismatch | reference query **and** human sign-off |
| Unknown family (no TD 1 cell) | none | none | **abstain** | abstain | abstain |

Why the checks are what they are:
- **none** appears only for a low-stakes dashboard on a family where the model scored 100 % in TD 1, as required by the consistency constraint. The "zero-value guard" on age families is a free local check: if the answer is 0, recount rows. Pair B showed that empty filters converge on 0 (C09).
- **Customer, F1/F3:** every model is correct, so a 2-of-3 quorum of free models is cheap and catches a one-off slip.
- **Customer, age families:** a quorum is not enough. On C09 the fixed 2-of-3 panel **published a wrong 0** (north + qwen), and 3-of-5 abstained on C09 and C10, which is safe but gives no answer. Only one model is reliable, so the check must be **deterministic**: the reference SQL template from `reference-td1.csv`, run by the local `script` route (portfolio G5, `retenu`, 0 cost). On mismatch, abstain and send to review.
- **Payout:** reference query plus human sign-off for every family. For F1/F3 we also run a 3-of-5 quorum, since all five free models qualify there.

**Unavailability:** (1) next eligible free model; (2) if `can_wait` and the free route refills before `deadline_minutes`, **defer** and re-measure availability at wake-up (in TD 1, qwen got a 429 on C18/C19 and then succeeded on the second attempt 10–12 s later); (3) otherwise the paid gpt-oss-120b route if `cash <= budget`; (4) otherwise **abstain**: publish no figure. The retained subscription `gpt-5.6-luna#codex` stays **ineligible**: it has no TD 1 cell.

### 4.3 Simulator: before and after adaptation

`python3 atelier-routage.py`. Full JSON lines in `pair-c/simulator-before.jsonl` and `pair-c/simulator-after.jsonl`.

| Scenario | Before (supplied, synthetic resources) | After (our rule; the request becomes a family + a use) |
|---|---|---|
| simple | run `small-free`, reason "eligible included capacity" | F1 dashboard → run **gpt-oss-20b#groq**, check none; reason cites F1 6/6 (C01…C20), excludes qwen F1 5/6 (C20 not_executed) |
| complex | run `senior-subscription` | F2 customer → run **gpt-oss-120b#groq**, reference query; reason: F2 4/4, excludes 20b (C02, C11), qwen (C09), north (0/4), dots (C09 rejected) |
| deferrable | defer `senior-subscription`, wake 60 | 120b Groq exhausted → **defer gpt-oss-120b#groq**, wake 60, recheck at wake-up |
| urgent | run `senior-api`, 0.30 USD | can't wait → run **gpt-oss-120b#openrouter**, 0.000711 USD, reference query |
| budget exhausted | abstain | **abstain**: both 120b routes unavailable or over budget, nothing else at 100 % on F2 |
| high impact | run `senior-subscription`, "source verification and human review" | F2 payout → run gpt-oss-120b#groq, reference query **and** human sign-off |
| unknown capability | abstain (difficulty 4) | family F4 → **abstain**: no TD 1 cell for the family |
| *product for customer* (added) | – | F3 → run qwen3.8-27b#groq, 2-of-3 quorum (qwen, 20b, north) |
| *first model down* (added) | – | F1, 20b down → run **north-mini-code** (next model), no deferral needed |
| *age at order* (added) | – | F2b dashboard → run gpt-oss-20b (C10 1/1), none + zero-value guard |
| *combined payout* (added) | – | F1+F2+F3 → gpt-oss-120b, reason cites C17, C19 and each component |

Changes to the code:
- `RESOURCES` now holds seven portfolio routes with their prices instead of three fictitious ones.
- The integer `level` is replaced by **per-family eligibility recomputed from `traces-td1.csv`**. A single level could not express our data: gpt-oss-20b is 100 % on F2b and on every combination but only 2/4 on F2, so the families are not nested.
- `choose` keeps the supplied branch order: included, then defer, then paid, then abstain. Each `reason` now cites the TD 1 cells of the chosen route and of every excluded route, and `checks` depends on the use and the family.

### 4.4 Priority order in the supplied `choose`

`choose` tests its branches **in sequence and returns at the first non-empty one**. The first branch keeps every eligible, available resource with `cash == 0`, which includes a subscription with `allocation > 0`. The `defer` branch is reached only when that list is empty. So an available subscription always beats waiting for an exhausted free route, even when the free route refills well before `deadline_minutes`. `allocation` only breaks ties among routes that are already available.

Why this order is sound by default:
- **Zero marginal cash:** the subscription is already paid. Using it costs no new money, and an allocation that resets unused is lost anyway ("use it or lose it").
- **Certainty versus a bet:** running now gives the answer now. Deferring is a bet that the quota will be back. The docstring warns that reaching the reset time does not prove capacity is available, so a deferred request can wake up to another 429 and run out of deadline.
- **Fewer moving parts:** no wake-up, no re-check, no second scheduling decision.

When the priority should be **reversed** (defer instead of spending allocation):
- the allocation is **scarce or charged**: the subscription window is nearly used up and will be needed by harder or urgent requests before it resets, or an internal chargeback puts a real price on each allocation unit;
- **and** the request is latency-tolerant (`can_wait`, `deadline_minutes` much larger than `reset_minutes`), for example a nightly dashboard batch;
- **and** the free refill is short and reliable, such as a Groq per-minute token limit (TD 1: qwen C18/C19, a 429 followed by success 10–12 s later).

In these cases, compare `allocation` with the remaining reserve before the first branch: if a free route refills before the deadline, defer.

A further reason applies to our data. The free route has TD 1 evidence, and the subscription (`gpt-5.6-luna#codex`) has none. Our adapted `choose` therefore never picks it, which settles the question by eligibility before cost.

### 4.5 Limitations and notes for TD 3

- 20 questions × 5 models support a **batch-specific hypothesis only**. F2b (C10) and C18 have one cell each, so "100 %" there means 1/1. More age-at-order cells are the first thing to measure.
- The paid gpt-oss-120b route is assumed to behave like the Groq route measured in TD 1, which is why it always carries a check. The provider's quantisation may differ.
- **No free model is enough on its own** for customer or payout figures on F2, F2b and their combinations. Only gpt-oss-120b is reliable there, and C09 shows that a free quorum can agree on a wrong value. These families set the **price of checking** for TD 3: one reference query (≈0 cost) or a human review per figure.
