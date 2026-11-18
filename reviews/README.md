# Peer Cross-Check & Technical Review Logs

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  

---

## 1. Overview and Quality Assurance Framework

In accordance with the course protocol, all deliverables, reference queries, execution traces, voting algorithms, and routing rules undergo mandatory peer cross-verification across sub-group members.

This directory archives **6 pairwise cross-check logs**, each capturing **2 peer reviews**
(12 structured technical evaluations), plus **1 automated verification pass**
([crosscheck-07.md](crosscheck-07.md)) whose 16 checks any member can rerun with
`python3 td2/qa/verify-td2.py`:

| Log File | Target Scope & Session | Review 1 Focus | Review 2 Focus | Audit Status |
|---|---|---|---|---|
| [crosscheck-01.md](crosscheck-01.md) | **TD 1**: Reference Queries (C01-C06) | **C01-C03**: Half-open intervals, anniversary age, product list (Auditor: Maxime Laurent) | **C04-C06**: Period boundaries, single day, empty window and the COALESCE requirement (Auditor: Louis Le Forestier) | **APPROVED** (corrected 2026-11-18) |
| [crosscheck-02.md](crosscheck-02.md) | **TD 1**: Reference Queries (C07-C13) | **C07-C09**: One-day period and the C08/C09 age boundary pair, 117600 cents apart (Auditor: Jean Jaunet) | **C10-C13**: Age at order time, late reference date, product-list containment (Auditor: Baptiste Noailhac) | **APPROVED** (corrected 2026-11-18) |
| [crosscheck-03.md](crosscheck-03.md) | **TD 1**: Reference Queries (C14-C20) | **C14-C17**: Compound filters and containment C17 < C16 < C12 (Auditor: Valentin Gourmelon) | **C18-C20**: Age at order time in a window, C19 sensitivity case, adjacent-window disjointness (Auditor: Alexandre Jullien Gaildraud) | **APPROVED** (corrected 2026-11-18) |
| [crosscheck-04.md](crosscheck-04.md) | **TD 1**: Traces & Concurrency Audit | **Operators A & B**: Groq 3s pacing & rate-limit audit (Auditor: Romain Thepaut) | **Operators C, D, E**: OpenRouter quota, retries & error taxonomy (Auditor: Romain Thepaut) | **APPROVED** |
| [crosscheck-05.md](crosscheck-05.md) | **TD 2**: Voting Engine & Benchmark | **`vote_k_sur_n`**: Contract compliance, synthetic tests & 40-decision oracle comparison (Auditors: Group B - Baptiste, Jean, Romain) | **20-Question Matrix**: 2-of-3 vs 3-of-5, 17/20 consensus each, 16 vs 17 correct (Auditors: Pair C - Alexandre, Valentin) | **APPROVED** (corrected 2026-11-18) |
| [crosscheck-06.md](crosscheck-06.md) | **TD 2**: Wrong Consensus & Routing | **Wrong consensus C09** (+C10): delta SQL on `boutique.sqlite`, reconciled to the cent (Auditors: Pair A - Louis, Maxime) | **Routing Policy**: TD 1 rate table per family & simulator reproduction (Auditors: Group B - Romain, Jean, Baptiste) | **APPROVED** (corrected 2026-11-18) |
| [crosscheck-07.md](crosscheck-07.md) | **TD 2**: Automated verification pass, all three steps | **16 scripted checks**: DB fingerprint, trace inventory, reference queries, offline replay of the 100 cells, quorum matrix by independent oracle, Pair B delta SQL, Pair C rate table and simulator (Auditor: Romain Thepaut) | **Findings F1-F5**: step 1 missing then delivered and verified, quorum figures and wrong-consensus case realigned on the traces, steps 2 and 3 reproducible (Auditor: Romain Thepaut) | **15/15 after #16** |

---

## 2. Review Methodology & Criteria

Every logged cross-check evaluates the following quality gates:
1. **Semantic Correctness**: SQL queries conform to relational algebra requirements without accidental cartesian joins or incorrect boundary comparisons.
2. **Deterministic Verification**: Independent query execution on `data/boutique.sqlite` matches the certified ground-truth values down to the exact cent.
3. **Contract Adherence**: Code implementations (`skeleton-multi-llm-en.py`, `atelier-routage.py`) satisfy all interface constraints and error-handling requirements.
4. **Trace Backing**: All metrics and error classifications cite exact line numbers from `traces-td1.csv`.
5. **Rerunnability**: Any figure published in a report must be re-derivable offline from `traces-td1.csv` and `data/boutique.sqlite` alone, by a single command and without the deliverable that produced it (`td2/qa/verify-td2.py`).
