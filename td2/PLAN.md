# TD 2 Action Plan: Quorum Voting and Dynamic Model Routing

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Session Date**: 2026-11-18  
**Reference Document**: `https://storage.googleapis.com/docs.g.quanticfactory.io/ESILV/next-generation-ai/latest/students/kit-td1/enonce-td2-en.html`  
**Pack Version**: `2026-11-18-students-5`  

---

## 1. Team Allocation and Roles

The sub-group is split into three operational pairs, with defined primary owners, cross-reviewers, and specific deliverables.

| Pair | Members (Roster) | Primary Role | Assigned Step | Key Deliverable |
|---|---|---|---|---|
| **Pair A** | **Louis Le Forestier**<br>**Maxime Laurent** | Consensus Engineering | **Step 1**: $k$-of-$n$ Quorum Voting | `skeleton-multi-llm-en.py` (`vote_k_sur_n`), 20-question comparison matrix (2-of-3 vs 3-of-5) |
| **Pair B** | **Baptiste Noailhac**<br>**Jean Jaunet**<br>*(Support: Romain Thepaut)* | SQL Diagnostics & Evidence Auditing | **Step 2**: False Consensus Investigation | False consensus root-cause analysis, delta SQL diagnostic on `boutique.sqlite`, discrepancy reconciliation |
| **Pair C** | **Alexandre Jullien Gaildraud**<br>**Valentin Gourmelon** | Routing Architecture & Cost Simulation | **Step 3**: Dynamic Routing Rule | 1-page Routing Policy, adapted `atelier-routage.py` (`RESOURCES` & `choose`), queue priority analysis |

---

## 2. Operational Schedule (13:30 - 18:00)

```
+---------------------------------------------------------------------------------------+
| 13:30 - 13:45 | Briefing, workspace sync, trace validation                           |
+---------------------------------------------------------------------------------------+
| 13:45 - 15:45 | Parallel Work: Step 1 (Pair A) | Step 2 (Pair B) | Step 3 (Pair C)    |
+---------------------------------------------------------------------------------------+
| 15:45 - 16:00 | Break                                                                 |
+---------------------------------------------------------------------------------------+
| 16:00 - 16:45 | Consolidation: Matrix build, delta SQL runs, simulator adaptation     |
+---------------------------------------------------------------------------------------+
| 16:45 - 17:15 | Mandatory Internal Subgroup Cross-Review (Peer Knowledge Transfer)    |
+---------------------------------------------------------------------------------------+
| 17:15 - 17:30 | Step 4 Plenary Session: Group finding presentation                    |
+---------------------------------------------------------------------------------------+
| 17:30 - 17:45 | Table Evaluation by Course Instructors (Grades Q1, Q2, Q3)            |
+---------------------------------------------------------------------------------------+
| 17:45 - 18:00 | Individual Moodle Quiz (15 minutes - Mandatory for all members)       |
+---------------------------------------------------------------------------------------+
| Post-Session  | Final Assembly of reports/td2.md and Moodle submission (due 22/11)    |
+---------------------------------------------------------------------------------------+
```

---

## 3. Detailed Work Breakdown by Pair

### Pair A: Step 1 - Quorum Voting Engine (`skeleton-multi-llm-en.py`)

* **Objective**: Implement and validate the majority voting mechanism to eliminate single-model hallucinations and handle abstentions safely.
* **Lead Engineers**: Louis Le Forestier, Maxime Laurent.

#### Implementation Tasks:
1. **Implement `Orchestrateur.vote_k_sur_n(self, traces_question, k)`**:
   - Check strict majority requirement: verify that `len(traces_question) // 2 < k <= len(traces_question)`. Raise `ValueError` if violated.
   - Filter out duplicate proposals: ensure every `(provider, model_requested)` pair occurs at most once. Raise `ValueError` if duplicate detected.
   - Separate executed proposals from errors:
     - Proposals with `verdict == "executed"` and integer `value` participate in voting.
     - Unexecuted proposals, HTTP errors (e.g. 429), or empty values remain in total count $n$, but cast no vote.
   - Aggregate votes by integer value:
     - If the highest vote count reaches or exceeds $k$, return:  
       `{"consensus": True, "value": v, "votes": count, "models": [list of "provider:model"]}`
     - If no value reaches $k$, return:  
       `{"consensus": False, "value": None, "votes": max_count, "models": []}`
2. **Synthetic Validation**:
   - Run `python atelier-vote.py` from `td2/`.
   - Confirm all 4 synthetic test cases pass without assertion failure (unanimous, split majority, tie/abstention, unavailable member).
3. **Trace Benchmark Across All 20 Questions (C01 to C20)**:
   - Execute the vote on TD 1 traces using the fixed 3-model panel:
     - `openai/gpt-oss-120b` (Groq)
     - `cohere/north-mini-code:free` (OpenRouter)
     - `qwen/qwen3.8-27b` (Groq)
     - Threshold: $k = 2$ ($2$-of-$3$).
   - Execute the vote on TD 1 traces using all 5 models:
     - Adding `openai/gpt-oss-20b` (Groq) and `dots-studio/dots-3-note-preview:free` (OpenRouter).
     - Threshold: $k = 3$ ($3$-of-$5$).
   - Compare both outcomes against `reference-td1.csv`.
   - Construct the side-by-side comparison matrix in `reports/td2.md` explaining every transition (e.g. where $2$-of-$3$ consensus collapsed into $3$-of-$5$ abstention due to model dispersion or rate limits).

---

### Pair B: Step 2 - False Consensus & SQL Delta Diagnostics

* **Objective**: Isolate and prove a case where multiple distinct models agree on an identical incorrect answer, confirming that consensus does not imply ground truth.
* **Lead Engineers**: Baptiste Noailhac, Jean Jaunet, Romain Thepaut.

#### Investigation Tasks:
1. **Trace Audit on `traces-td1.csv`**:
   - Scan all 100 cells across the 5 models.
   - Identify questions where at least two different model families returned the exact same incorrect value (`verdict == "incorrect"` and identical `value`).
   - If no identical false values exist in the team traces, adopt the official historical benchmark case **`DEMO-SQL-C11`**:
     - Question C11: Total revenue excluding VAT in cents generated by customers exactly 25 years old on 2026-12-01.
     - Models: `openai/gpt-oss-20b` (Groq) and `cohere/north-mini-code:free` (OpenRouter).
     - Shared False Output: `0` cents (both queries executed cleanly but returned `0`).
2. **SQL Semantic Diagnosis**:
   - Extract the generated SQL queries from both models.
   - Analyze the filtering logic:
     - Model 1 used `WHERE c.birth_date = '2001-12-01'` (restricting to people born on that single day rather than the entire year span).
     - Model 2 used contradictory date comparison intervals resulting in an empty set.
3. **Delta Diagnostic Query on `boutique.sqlite`**:
   - Write and execute an explicit SQL query on `data/boutique.sqlite` isolating the exact customer rows and order amounts that satisfy the true condition:
     ```sql
     -- Customers exactly 25 years old on 2026-12-01:
     -- Born between 2000-12-02 and 2001-12-01 inclusive
     ```
   - Calculate the sum of `quantity_product * price` for these customers.
   - Demonstrate that this sum equals the ground-truth reference value from `reference-td1.csv`, explaining the entire numerical discrepancy.
4. **Quorum Impact Assessment**:
   - Document whether this false consensus would win a 2-of-3 vote, win a 3-of-5 quorum, or be rejected.
   - Detail the required external verification safeguards for high-stakes decisions.

---

### Pair C: Step 3 - Routing Architecture & Simulator Adaptation

* **Objective**: Establish an empirical routing rule that dispatches queries to the most economical model satisfying reliability requirements, and customize the resource simulator.
* **Lead Engineers**: Alexandre Jullien Gaildraud, Valentin Gourmelon.

#### Architecture Tasks:
1. **Empirical Accuracy Mapping per Family**:
   - Map each of the 20 questions to its structural family:
     - Family 1 ($F1$): Simple period intervals (`[start_date, end_date)`).
     - Family 2 ($F2$): Customer age at a fixed date.
     - Family 2b ($F2b$): Customer age at order date.
     - Family 3 ($F3$): Product IDs, item categories, multi-item constraints.
     - Family 4 ($F4$): Hybrid multi-table joins and complex aggregations.
   - Calculate the observed success rate (`correct / total`) for each model per family from TD 1 data.
2. **1-Page Routing Policy Definition**:
   - Primary dispatch: select the lowest-cost model with a verified 100 % success rate on that specific family.
   - Verification tiering according to business risk:
     - Internal Dashboard (Low Stakes): Single free model execution allowed only if historical family accuracy is 100 %.
     - Customer Facing (Medium Stakes): Minimum 2-of-3 quorum required.
     - Financial Payout / Invoicing (Critical Stakes): 3-of-5 quorum or deterministic SQL rule check mandatory.
   - Failure and rate-limit recovery:
     - Immediate fallback to secondary model if request is urgent.
     - Queue deferral if request is non-urgent and refill window is within deadline.
     - Explicit abstention when budget or deadline cannot be met.
3. **Adaptation of `atelier-routage.py`**:
   - Run baseline simulation across all 7 scenarios (`python atelier-routage.py`).
   - Modify `RESOURCES` to integrate TD 1 models, their actual pricing from `portefeuille-modeles-2026-09-28.csv`, and empirical capability tiers.
   - Update `choose(request, resources)` to inject justifying TD 1 cells and accuracy ratios into the `"reason"` output.
   - Document the queue priority logic: explain why an immediately available subscription route (`cash == 0, allocation > 0`) takes precedence over waiting for a free route refill (`cash == 0, allocation == 0`), and identify the operational condition where this priority should invert (e.g. when subscription tokens carry an internal budget charge or when request latency tolerance is high).

---

## 4. Deliverables and Acceptance Criteria

| Deliverable | Target Location | Acceptance Criteria |
|---|---|---|
| **Voting Engine** | `td2/skeleton-multi-llm-en.py` | Passes all 4 synthetic tests in `atelier-vote.py`; handles errors and unexecuted items without modifying $n$; enforces strict majority. |
| **Comparison Matrix** | `reports/td2.md` | Complete 20-question table with side-by-side $2$-of-$3$ vs $3$-of-$5$ results, votes, reference agreement, and transition rationale. |
| **False Consensus Proof** | `reports/td2.md` | Identified model pair, shared wrong value, root-cause SQL clause, executable delta query on `boutique.sqlite`, and cent reconciliation. |
| **Routing Policy** | `reports/td2.md` | 1-page structured policy specifying empirical rates, dispatch order, verification tiers, and failover actions. |
| **Adapted Simulator** | `td2/atelier-routage.py` | Updated resources and `choose()` logic emitting TD 1 empirical evidence; captured CLI outputs before and after adaptation. |
| **Session Report** | `reports/td2.md` | Full English documentation of all steps, member contributions, limitations, and future steps for TD 3. |

---

## 5. Subgroup Cross-Review Checklist (Before 17:15)

Prior to the 17:45 Moodle individual quiz, each member must verify mastery of the following cross-cutting concepts:
- [ ] Understand why $k$ must be strictly greater than $n // 2$.
- [ ] Understand why an unavailable model remains in $n$ but casts no vote (abstention safety).
- [ ] Be able to explain the SQL delta query that isolates the false consensus rows on `boutique.sqlite`.
- [ ] Understand the difference between accuracy on $F1$ (date periods) and $F2$ (customer age).
- [ ] Be able to explain the priority decision between subscription allocation and free quota deferral in `atelier-routage.py`.
