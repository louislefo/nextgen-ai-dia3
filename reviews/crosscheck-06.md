# Peer Cross-Check Log 06: TD 2 False Consensus & Routing Policy Audit

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 2 - False Consensus SQL Diagnostics & Routing Policy  
**Target Repository**: `nextgen-ai-dia3`  
**Target Files**: `td2/pair-b/`, `td2/pair-c/`, `td2/atelier-routage.py`, `td2/data/boutique.sqlite`, `reports/td2.md`  

> **Corrected on 2026-11-18 by Romain Thepaut (QA)** after the automated pass recorded in
> [crosscheck-07.md](crosscheck-07.md). Review 1 previously audited a false consensus on
> C11 between `gpt-oss-20b` and `north-mini-code`, with a reference of 248180 reconciled
> over 3 customers. That configuration is `DEMO-SQL-C11`, the illustration given in the
> statement, not a measurement on our traces: C11's reference is 446690 and the two models
> return two *different* wrong values there. Our batch produces a wrong consensus on **C09**
> instead, which is the case Pair B investigated. Review 2 carried a verdict on a routing
> adaptation that did not exist yet; it is now the audit of the delivered step 3
> (commit `ce2b612`). Review scopes and auditor assignments are unchanged.

---

## Review 1: False Consensus Diagnosis & SQL Delta Query (`boutique.sqlite`)

### Metadata
- **Authors / Reviewees**: Group B (Baptiste Noailhac, Jean Jaunet, Romain Thepaut)
- **Auditors / Reviewers**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Target Case**: wrong consensus on **C09**, with C10 as a secondary non-zero case
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit the root-cause diagnosis of identical incorrect outputs across distinct model
architectures, and verify the differential SQL on `td2/data/boutique.sqlite`:
1. Establish which cases of the 100-cell matrix actually carry a shared wrong value.
2. Compare the queries of the agreeing models and explain the faulty clauses.
3. Verify the delta query isolating the exact customer rows and revenue sums that
   reconcile the gap with `reference-td1.csv`.
4. Assess what each quorum does with the wrong value.

### Audit Procedure & Execution
```bash
sqlite3 "file:td2/data/boutique.sqlite?mode=ro" < td2/pair-b/step2-wrong-consensus.sql
python3 td2/qa/verify-td2.py        # checks shared_wrong_values, sql_evidence, sql_verbatim
```

### Verification Findings
1. **Exactly three cases carry a shared wrong value** across the 100 cells, and the search
   is exhaustive, not a spot check:
   - **C09**, value `0`, by `cohere/north-mini-code:free` and `qwen/qwen3.8-27b`, reference 487980.
   - C02, value `0`, by `gpt-oss-20b` and `north-mini-code`, reference 590320.
   - C10, value `119410`, by `qwen` and `dots-3-note-preview:free`, reference 558980.
2. **C09 is the only one that wins a quorum.** Both agreeing models sit in the fixed 2-of-3
   panel, so `0` reaches 2 votes out of 3 and is published. C02's two wrong votes are split
   across the panel and the extra models, and C10 is a 1-1-1 split in the panel.
3. **Root cause, two unrelated bugs converging on the same value:**
   - `north-mini-code`: its age expression is `CAST(SUBSTR(birth_date,1,4) AS INTEGER)`
     minus a 0-or-1 correction, which is the *birth year* (about 2000 to 2001), never
     `2026 - birth_year`. Compared with 25, it is false for every customer.
   - `qwen3.8-27b`: uses `o.date` instead of the reference date 2026-09-26, which is F2b
     logic on an F2 question, and its window
     `strftime('%m-%d', o.date) >= birth_md AND < strftime('%m-%d', date(birth_date, '+26 years'))`
     compares the birth month-day with itself, a contradiction.
   - Both keep **zero rows**, and `COALESCE(SUM(...), 0)` turns an empty filter into a
     plausible `0`. Agreement on `0` is therefore weak evidence by construction.
4. **Both faulty queries are verbatim from `traces-td1.csv`**, verified by normalised
   comparison of their `WHERE` clauses, so the diagnosis is on the real model output.
5. **Delta query reconciles to the cent.** The correct window for age 25 on 2026-09-26 is
   `2000-09-27 <= birth_date <= 2001-09-26`. Six customers qualify:

   | customer_id | birth_date | orders | revenue_cents |
   |---|---|---|---|
   | C007 | 2000-11-30 | 6 | 118740 |
   | C009 | 2001-03-10 | 5 | 61330 |
   | C008 | 2001-05-15 | 7 | 99090 |
   | C002 | 2001-09-24 | 3 | 25920 |
   | C001 | 2001-09-25 | 8 | 135000 |
   | C003 | 2001-09-26 | 4 | 47900 |
   | **Total** | | | **487980 = 487980 - 0** |

   C003, born 2001-09-26 and turning 25 that day, sits on the inclusive boundary and is the
   row a strict `<` would drop. A third, independent method (completed age computed
   arithmetically, with no date window) also returns 487980.
6. **Secondary case C10 reconciles too**: 28 order lines across C004, C005, C007 and C022,
   totalling 439570 = 558980 - 119410. Both qwen and Dots accept only orders where
   `year(order) - year(birth) = 25` and the order falls after the birthday, so they miss
   orders placed before the birthday in the year of the 26th birthday, when the customer is
   still 25.
7. **Quorum outcome**: C09 wins 2-of-3 and is suppressed by 3-of-5 (2-2 tie below $k=3$,
   Dots `sql_rejected` and voteless). C10 is an abstention under both.

### Verdict
**APPROVED** - the wrong consensus is isolated with executable SQL proof, and every figure
reconciles down to the cent. The finding to carry to the plenary is that two models can
agree without sharing any reasoning, and that an agreed value of `0` deserves a row-count
check before publication.

---

## Review 2: Empirical Routing Policy & Resource Simulator Adaptation

### Metadata
- **Authors / Reviewees**: Pair C (Alexandre Jullien Gaildraud, Valentin Gourmelon)
- **Auditors / Reviewers**: Group B (Romain Thepaut, Jean Jaunet, Baptiste Noailhac)
- **Target Files**: `td2/atelier-routage.py` (`RESOURCES` & `choose`), `td2/pair-c/`
- **Review Date**: 2026-11-18, on the delivered step 3 (commit `ce2b612`)

### Scope of Inspection
1. Verify that model eligibility per question family derives from observed TD 1 accuracy,
   and that the families are not a regrouping chosen to fit a conclusion.
2. Confirm the risk-tiered verification rules and their justification.
3. Validate that the captured simulator outputs are what the committed code produces.
4. Review the analysis of queue priority between subscription allocation and free refill.

### Audit Procedure & Execution
```bash
python3 td2/atelier-routage.py            # 11 scenarios
python3 td2/atelier-routage.py --rates    # rate table rebuilt from the traces
python3 td2/qa/verify-td2.py              # checks pair_c_rates, pair_c_simulator
```

`pair_c_rates` parses the rate table out of `td2/pair-c/step3-report-section.md` and
compares it to the traces cell by cell, so the published table and the data cannot drift
apart unnoticed.

### Verification Findings
1. **The 8 x 5 rate table of section 4.1 is exact.** All 40 cells recompute from the
   traces, including qwen at 5/6 on F1 and 0/4 for `north-mini-code` on F2.
2. **The families are the `type` field of `questions-td1.json`**, not a regrouping: F1 (6
   cases), F2 (4), F2b (1), F3 (4), F1+F2 (1), F2+F3 (1), F1+F2+F3 (2), F1+F2b (1).
3. **Counting a `429` as a miss** (correct / cases, not correct / executed) is stated and
   applied consistently. It is what makes qwen ineligible on F1 despite no wrong answer
   there, which is the conservative reading and the right one for a routing decision.
4. **Eligibility by inheritance is sound.** A combination inherits its components'
   failures, which keeps `north-mini-code` out of F1+F2 and F2+F3 despite 1/1 on each. At
   one cell per combination, four failures on the component outweigh one lucky hit.
5. **The simulator reproduces exactly.** `python3 atelier-routage.py` yields the 11
   decisions of `simulator-after.jsonl` decision for decision, and `simulator-before.jsonl`
   replays from the kit version of the file retrieved at `0d1ecd0`, so the before/after
   pair is genuine rather than reconstructed.
6. **Pricing checks out.** `gpt-oss-120b#openrouter` is G4 at 0.15 / 0.60 USD per M tokens
   in `td1/portefeuille-modeles-2026-09-28.csv`; the 641 in / 1024 out envelope gives
   0.00071055, rounded to 0.000711 USD per request.
7. **Risk tiers are consistent with the data.** No check at all appears only for an
   internal dashboard on a family where the model scored 100% in TD 1. Age families carry a
   deterministic reference query rather than a quorum, justified by C09, where a free
   quorum published a wrong `0`, and by C09/C10, where 3-of-5 abstained and produced no
   answer at all.
8. **Priority analysis is correct about the supplied code.** `choose` returns at the first
   non-empty branch, and the first branch keeps every available eligible resource with
   `cash == 0`, which includes a subscription with `allocation > 0`. An available
   subscription therefore always beats waiting for a free refill. The stated reversal
   conditions (scarce or charged allocation, latency-tolerant request, short and reliable
   refill) are the right ones.

Two refinements, neither affecting a conclusion:

- **Traceability.** `north-mini-code:free` and `dots-3-note-preview:free` do not appear in
  `portefeuille-modeles-2026-09-28.csv`. They are OpenRouter `:free` routes, so a 0 USD
  cost is right, but "all five are portfolio G5" cites a file listing only the three Groq
  models. "Three in G5, two OpenRouter free routes outside the portfolio export" is
  checkable as written.
- **Wording on the retry.** The traces confirm the qwen `429` timing (C18: 429 at 12:19:10,
  HTTP 200 at 12:19:22; C19: 429 at 12:19:25, HTTP 200 at 12:19:35), but C19's retry
  returned 83580 against a reference of 1990. The call recovered; the answer did not. The
  deferral argument rests on transport recovery, so the two are worth separating.

### Verdict
**APPROVED** - the routing policy is grounded in TD 1 evidence cell by cell, and the
simulator outputs are reproducible from the committed code.
