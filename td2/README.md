# TD 2: Majority Quorum Consensus & Dynamic Model Routing

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Session Date**: 2026-11-18  
**Pack Version**: `2026-11-18-students-5`  
**Official Assignment**: `students/kit-td1/enonce-td2-en.html`  

---

## 1. Overview and Core Objectives

TD 2 moves beyond individual model evaluations to design the two core decision systems of a trustworthy AI architecture:
1. **Majority Voting Consensus ($k$-of-$n$)**: Implementing a strict quorum mechanism across heterogeneous model outputs to detect divergences, filter hallucinations, and safely abstain without fabricating values.
2. **False Consensus Analysis**: Proving empirically and in SQL that consensus among models does not guarantee ground truth, using differential diagnostic queries on `data/boutique.sqlite`.
3. **Dynamic Request Routing**: Formulating an empirical routing policy that directs queries to the lowest-cost capable model and adapting a resource simulator (`atelier-routage.py`) with quotas and deferral rules.

*Operational Constraint*: **No new network batch or API spending is required**. All voting and analysis operate offline using your stored TD 1 traces (`traces-td1.csv`) and database (`data/boutique.sqlite`).

---

## 2. Team Work Breakdown (Three Parallel Pairs)

The session is organized into three parallel operational tracks, followed by an internal cross-review:

```
+---------------------------------------------------------------------------------------+
| 13:30 - 13:45 | Briefing, workspace sync, trace validation                           |
+---------------------------------------------------------------------------------------+
| 13:45 - 15:45 | Parallel Work: Step 1 (Pair A) | Step 2 (Pair B) | Step 3 (Pair C)    |
+---------------------------------------------------------------------------------------+
| 15:45 - 16:00 | Break                                                                 |
+---------------------------------------------------------------------------------------+
| 16:00 - 16:45 | Deliverable Consolidation (Voting Matrix, Delta SQL, Adapted Policy)  |
+---------------------------------------------------------------------------------------+
| 16:45 - 17:15 | Mandatory Internal Cross-Review (Peer walk-through for Moodle Quiz)   |
+---------------------------------------------------------------------------------------+
| 17:15 - 17:30 | Step 4 Plenary Session: Presentation of False Consensus & Routing Rule|
+---------------------------------------------------------------------------------------+
| 17:30 - 17:45 | Table Evaluation by Instructors (Grades Q1, Q2, Q3)                   |
+---------------------------------------------------------------------------------------+
| 17:45 - 18:00 | Individual Moodle Quiz (15 minutes - Mandatory for all members)       |
+---------------------------------------------------------------------------------------+
```

### Pair A: Step 1 - Quorum Voting Engine
* **Engineers**: **Louis Le Forestier**, **Maxime Laurent**
* **Core Tasks**:
  1. Implement `Orchestrateur.vote_k_sur_n(self, traces_question, k)` in `skeleton-multi-llm-en.py`:
     - Enforce strict majority constraint: `len(traces_question) // 2 < k <= len(traces_question)` (raise `ValueError` otherwise).
     - Refuse duplicate proposals from identical `(provider, model_requested)` pairs with `ValueError`.
     - Count executed proposals with integer values; unexecuted proposals or errors remain in total $n$ but cast no vote.
     - Return `{"consensus": True, "value": v, "votes": count, "models": [...]}` if a value reaches $k$, otherwise `{"consensus": False, "value": None, "votes": max_votes, "models": []}`.
  2. Validate with synthetic test cases: `python atelier-vote.py`.
  3. Build the 20-question comparison matrix comparing the fixed 2-of-3 panel (`gpt-oss-120b`, `north-mini-code:free`, `qwen3.8-27b` with $k=2$) against the 3-of-5 quorum across all TD 1 models.

### Group B: Step 2 - False Consensus Investigation & SQL Delta
* **Engineers**: **Baptiste Noailhac**, **Jean Jaunet**, **Romain Thepaut**
* **Core Tasks**:
  1. Audit TD 1 traces for identical wrong answers (`verdict == "incorrect"` with identical `value`) or inspect historical benchmark case `DEMO-SQL-C11` (where `openai/gpt-oss-20b` and `cohere/north-mini-code:free` both return `0` on C11).
  2. Diagnose faulty SQL clauses in both queries (`c.birth_date = '2001-12-01'` vs contradictory date window).
  3. Author and execute the Delta Diagnostic SQL query on `data/boutique.sqlite` to isolate mismatched customer IDs and order sums, reconciling the exact cent difference against `reference-td1.csv`.
  4. Assess quorum outcome: show whether the false consensus wins 2-of-3, wins 3-of-5, or is suppressed.

### Pair C: Step 3 - Routing Architecture & Simulator Adaptation
* **Engineers**: **Alexandre Jullien Gaildraud**, **Valentin Gourmelon**
* **Core Tasks**:
  1. Calculate empirical TD 1 accuracy rates per question family ($F1$ period, $F2$ age at date, $F2b$ age at order, $F3$ product).
  2. Author 1-page routing policy: dispatch lowest-cost capable model, enforce risk-tiered checking (none only for internal dashboards with 100% TD 1 accuracy, quorum/verification for customer-facing and payouts), and define failover/abstention rules.
  3. Adapt `RESOURCES` and `choose` in `atelier-routage.py` with portfolio pricing and TD 1 justification strings.
  4. Analyze queue priority: explain why available subscription allocation is prioritized before deferring for a free quota refill, and define the conditions where this priority should reverse.

---

## 3. Directory File Manifest

```text
td2/
├── data/
│   ├── boutique.sqlite                 # Local copy of the verified SQLite database
│   ├── customers.csv                   # Raw customer table dump
│   ├── orders.csv                      # Raw order records table dump
│   ├── product.csv                     # Raw product catalog table dump
│   └── manifest.json                   # SHA-256 integrity checksums
├── PLAN.md                             # Detailed operational plan, task checklist, and schedule
├── skeleton-multi-llm-en.py            # Core orchestration client containing vote_k_sur_n
├── atelier-vote.py                     # Quorum voting test and benchmark harness
├── atelier-routage.py                  # Dynamic model routing and resource simulator
├── check_access.py                     # Gateway connectivity validator
├── modeles-autorises.json              # Authorized model configurations
├── questions-td1.json                  # 20 reference question specifications
├── reference-td1.csv                   # Ground-truth reference values in cents
├── sandbox_sqlite.py                   # Read-only SQLite execution sandbox
├── schema.sql                          # Database relational schema
└── traces-td1.csv                      # TD 1 master inference trace log
```

---

## 4. Reproduction Commands

### 1. Execute Voting Harness on Synthetic Test Cases
```powershell
python atelier-vote.py
```
*Expected*: Exercises unanimous consensus, split decision, tie/abstention, and error handling without network access.

### 2. Execute Voting Harness on Real Traces for a Specific Question
```powershell
python atelier-vote.py --traces traces-td1.csv --case C02
```

### 3. Run Dynamic Routing Simulator Across Scenarios
```powershell
python atelier-routage.py
```

### 4. Run Routing Simulator for a Single Scenario
```powershell
python atelier-routage.py --scenario deferrable
```

---

## 5. Deliverables & Documentation Links

- **Operational Action Plan**: [td2/PLAN.md](file:///c:/Users/louis/OneDrive/Desktop/Esilv/A4/Nextgen%20IA/nextgen-ai-dia3/td2/PLAN.md)
- **Session Report**: [reports/td2.md](file:///c:/Users/louis/OneDrive/Desktop/Esilv/A4/Nextgen%20IA/nextgen-ai-dia3/reports/td2.md)
- **Course Assignment Reference**: [enonce-td2-en.html](file:///c:/Users/louis/OneDrive/Desktop/Esilv/A4/Nextgen%20IA/course-materials/documentation/resource-index-en.html)
