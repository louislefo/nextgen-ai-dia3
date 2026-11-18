# Peer Cross-Check & Technical Review Logs

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  

---

## 1. Overview and Quality Assurance Framework

In accordance with the course protocol, all deliverables, reference queries, execution traces, voting algorithms, and routing rules undergo mandatory peer cross-verification across sub-group members.

This directory formally archives **6 dedicated cross-check logs**, each capturing **2 rigorous peer reviews** (totaling 12 structured technical evaluations):

| Log File | Target Scope & Session | Review 1 Focus | Review 2 Focus | Audit Status |
|---|---|---|---|---|
| [crosscheck-01.md](crosscheck-01.md) | **TD 1**: Reference Queries (C01–C06) | **C01–C03**: Half-open date intervals `[start, end)` (Auditor: Maxime Laurent) | **C04–C06**: Customer age arithmetic & order-date age (Auditor: Louis Le Forestier) | **APPROVED** |
| [crosscheck-02.md](crosscheck-02.md) | **TD 1**: Reference Queries (C07–C13) | **C07–C09**: Product filtering & multi-item queries (Auditor: Jean Jaunet) | **C10–C13**: Three-way joins & compound age/product rules (Auditor: Baptiste Noailhac) | **APPROVED** |
| [crosscheck-03.md](crosscheck-03.md) | **TD 1**: Reference Queries (C14–C20) | **C14–C17**: Volume thresholds, aggregations & postcodes (Auditor: Valentin Gourmelon) | **C18–C20**: Boundary date intervals & zero-match cases (Auditor: Alexandre Jullien Gaildraud) | **APPROVED** |
| [crosscheck-04.md](crosscheck-04.md) | **TD 1**: Traces & Concurrency Audit | **Operators A & B**: Groq 3s pacing & rate-limit audit (Auditor: Romain Thepaut) | **Operators C, D, E**: OpenRouter quota, retries & error taxonomy (Auditor: Romain Thepaut) | **APPROVED** |
| [crosscheck-05.md](crosscheck-05.md) | **TD 2**: Voting Engine & Benchmark | **`vote_k_sur_n`**: Contract compliance & synthetic tests (Auditors: Group B - Baptiste, Jean, Romain) | **20-Question Matrix**: 2-of-3 vs 3-of-5 transitions (Auditors: Pair C - Alexandre, Valentin) | **APPROVED** |
| [crosscheck-06.md](crosscheck-06.md) | **TD 2**: False Consensus & Routing | **False Consensus C11**: Delta SQL query on `boutique.sqlite` (Auditors: Pair A - Louis, Maxime) | **Routing Policy**: TD 1 accuracy rates & simulator adaptation (Auditors: Group B - Romain, Jean, Baptiste) | **APPROVED** |

---

## 2. Review Methodology & Criteria

Every logged cross-check evaluates the following quality gates:
1. **Semantic Correctness**: SQL queries conform to relational algebra requirements without accidental cartesian joins or incorrect boundary comparisons.
2. **Deterministic Verification**: Independent query execution on `data/boutique.sqlite` matches the certified ground-truth values down to the exact cent.
3. **Contract Adherence**: Code implementations (`skeleton-multi-llm-en.py`, `atelier-routage.py`) satisfy all interface constraints and error-handling requirements.
4. **Trace Backing**: All metrics and error classifications cite exact line numbers from `traces-td1.csv`.
