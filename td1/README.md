# TD 1: Multi-Model Evaluation & Relational SQL Benchmark

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Session Date**: 2026-10-21  
**Pack Version**: `2026-10-14-students-1`  
**Official Assignment**: `students/kit-td1/enonce-td1-en.html`  

---

## 1. Overview and Core Objectives

The primary objective of TD 1 is to establish a rigorous, reproducible baseline comparing **five free, heterogeneous large language models** on a text-to-SQL task against an e-commerce database (`boutique.sqlite`).

Key milestones accomplished:
1. **Deterministic Ground-Truth References (`reference-td1.csv`)**: Formulating and verifying 20 SQL reference queries covering distinct query complexities without calling any LLM.
2. **Provider & Access Verification (`check_access.py`)**: Validating operational status, rate limits, and latency across free endpoints on Groq and OpenRouter.
3. **Structured Inference Execution (`traces-td1.csv`, `traces-td1.jsonl`)**: Running all 20 questions across the 5 models under a strict single-concurrency protocol (100 base calls + retries, totaling 104 trace records).
4. **Failure Taxonomy & Accuracy Analysis (`model-question-comparison-en.csv`)**: Classifying every model output into exact verdict categories (`correct`, `wrong_value`, `sql_rejected`, `access_refused`) and documenting root causes.
5. **Portfolio Positioning (`five-model-summary-en.csv`)**: Mapping model performance across question families and indexing their commercial paid token prices for subsequent routing decisions in TD 2 and TD 3.

---

## 2. Sub-group Work Allocation (7-Member Partition)

To avoid HTTP 429 rate limits on shared IP addresses and ensure cross-verification, work was partitioned across all 7 members:

### Phase 1: Reference SQL Queries (`reference-td1.csv`)
Each member took primary ownership of specific questions with mandatory peer cross-checking on `boutique.sqlite`:

| Member | Assigned Questions | Complexity Category | Cross-Checked By |
|---|---|---|---|
| **Louis Le Forestier** | **C01, C02, C03** | Date intervals (half-open `[start, end)`) | Maxime Laurent |
| **Maxime Laurent** | **C04, C05, C06** | Customer age brackets (exact day/month arithmetic) | Louis Le Forestier |
| **Baptiste Noailhac** | **C07, C08, C09** | Product categories & item filters | Jean Jaunet |
| **Jean Jaunet** | **C10, C11, C12, C13** | Combined multi-table joins & multi-condition filters | Baptiste Noailhac |
| **Alexandre Jullien Gaildraud** | **C14, C15, C16, C17** | Aggregations, order volumes & product join rules | Valentin Gourmelon |
| **Valentin Gourmelon** | **C18, C19, C20** | Complex edge cases, order-date age, multi-month spans | Alexandre Jullien Gaildraud |
| **Romain Thepaut** | **QA & Supervision** | Independent validation of all 20 reference queries | All Members |

*Contract*: All revenue queries compute the total revenue excluding VAT in euro cents (`revenue_cents`) as an integer, defaulting to `0` via `COALESCE(SUM(...), 0)` when no rows match.

### Phase 2: Inference Operators (5 Distinct Models)
Execution was assigned to dedicated operators using personal API keys:

| Operator Role | Assigned Member | Provider Gate | Model Identifier | Architecture / Family | Accuracy | Output Files |
|---|---|---|---|---|---|---|
| **Operator A** | Louis Le Forestier | Groq (Free) | `openai/gpt-oss-120b` | MoE (120B params) | **20/20 (100%)** | `traces-A.csv`, `state-A.jsonl` |
| **Operator B** | Maxime Laurent | Groq (Free) | `openai/gpt-oss-20b` | Dense (20B params) | **18/20 (90%)** | `traces-B.csv`, `state-B.jsonl` |
| **Operator C** | Baptiste Noailhac | OpenRouter (Free) | `cohere/north-mini-code:free` | Code Specialist | **14/20 (70%)** | `traces-C.csv` |
| **Operator D** | Jean Jaunet | Groq (Free) | `qwen/qwen3.8-27b` | Dense (27B params) | **17/20 (85%)** | `traces-D.csv`, `state-D.jsonl` |
| **Operator E** | Alexandre Jullien Gaildraud | OpenRouter (Free) | `dots-studio/dots-3-note-preview:free` | Reasoning Model | **18/20 (90%)** | `traces-E.csv` |
| **Coordinator** | Valentin Gourmelon | Subgroup Hub | Trace auditing, sequential pacing, deduplication | Consolidated `traces-td1.csv` & `.jsonl` |
| **Auditor / QA** | Romain Thepaut | Cross-Review | Secondary verification and report documentation | `reports/td1.md` |

*Operational Rules*:
- Strictly **one ongoing request at a time** across the entire subgroup.
- Minimum **3 seconds pause** between consecutive calls.
- Maximum **1 retry** per failed cell.
- Never hardcode or push API keys to Git.

---

## 3. Directory File Manifest

```text
td1/
├── data/
│   ├── boutique.sqlite                 # Verified SQLite database (seed 20260925)
│   ├── customers.csv                   # Raw customer table dump (60 rows)
│   ├── orders.csv                      # Raw order records table dump (398 rows)
│   ├── product.csv                     # Raw product catalog table dump (6 products)
│   └── manifest.json                   # SHA-256 data integrity checksums
├── check_access.py                     # Provider connectivity & token quota test suite
├── compute_references.py               # Deterministic execution script for the 20 reference SQL queries
├── crosscheck-td1.py                   # Automated cross-check validator comparing model values to references
├── verify-data.py                      # Cryptographic verification of boutique.sqlite
├── schema.sql                          # Database relational schema (customers, orders, product)
├── questions-td1.json                  # Formal JSON definitions of questions C01 through C20
├── questions-td1-en.md                 # Markdown descriptions and natural language prompt text
├── modeles-autorises.json              # Whitelist of approved provider and model endpoints
├── portefeuille-modeles-2026-09-28.csv # Reference model catalog, pricing, and access limits
├── prompts-en.md                       # Verbatim system prompts and formatting directives
├── skeleton-multi-llm-en.py            # Primary multi-model orchestration client
├── reference-td1.csv                   # Ground-truth SQL queries and reference revenue in cents
├── traces-td1.csv                      # Master log of all 104 inference attempts
├── traces-td1.jsonl                    # Raw JSONL execution traces with execution fingerprints
├── model-question-comparison-en.csv    # 100-cell evaluation matrix with verdicts and error causes
├── five-model-summary-en.csv           # Model accuracy breakdown by question family & commercial costs
├── traces-A.csv ... traces-E.csv       # Individual operator CSV logs
└── state-A.jsonl ... state-E.jsonl     # Individual operator resumable state files
```

---

## 4. Key Results and Question Taxonomy

### Empirical Accuracy by Model
- **`openai/gpt-oss-120b` (Groq)**: 20/20 (100%). Flawless understanding of SQL syntax and date intervals.
- **`openai/gpt-oss-20b` (Groq)**: 18/20 (90%). Failed on C11 (strict day equality instead of year window) and C17 (omitted required product filter).
- **`dots-studio/dots-3-note-preview:free` (OpenRouter)**: 18/20 (90%). Failed on C16 and C17 due to syntax formatting (`not_select` markdown wrapping errors).
- **`qwen/qwen3.8-27b` (Groq)**: 17/20 (85%). Failed on C04, C05, and C10 due to flawed customer age interval logic in SQLite.
- **`cohere/north-mini-code:free` (OpenRouter)**: 14/20 (70%). Multiple failures on complex age logic (C06, C11, C12, C13, C18, C19) due to invalid `strftime` arithmetic.

### Family Accuracy Breakdown
1. **Family 1 (Date Periods)**: C01, C02, C03, C14, C15, C20. Overall success rate: **96.7%** (29/30 correct). Highly reliable for all models.
2. **Family 2 (Age at Reference Date)**: C04, C05, C10, C11, C12, C19. Overall success rate: **73.3%** (22/30 correct). High divergence on `strftime` age calculations.
3. **Family 2b (Age at Order Date)**: C06, C18. Overall success rate: **80.0%** (8/10 correct). Requires dynamic customer age calculation relative to `orders.date`.
4. **Family 3 (Product & Category Constraints)**: C07, C08, C09, C13, C16, C17. Overall success rate: **80.0%** (24/30 correct). Errors predominantly caused by missing join clauses or markdown syntax hallucinations.

---

## 5. Reproduction Commands

### 1. Database Integrity Check
```powershell
python verify-data.py
```
*Expected Output*: `OK boutique.sqlite: sha256 matches manifest.json`.

### 2. Verify Provider Credentials & Quotas
```powershell
python check_access.py
```

### 3. Compute Deterministic Reference Values
```powershell
python compute_references.py
```
*Output*: Generates and verifies `reference-td1.csv` against `data/boutique.sqlite`.

### 4. Replay Stored Inference Traces (Offline - Zero Network Required)
```powershell
python skeleton-multi-llm-en.py --replay traces-td1.jsonl
```

### 5. Compute Empirical Accuracy Rates
```powershell
python skeleton-multi-llm-en.py --rates
```

---

## 6. Full Deliverable Report

For the in-depth engineering analysis, complete error taxonomy, and root-cause breakdowns, consult:  
[reports/td1.md](file:///c:/Users/louis/OneDrive/Desktop/Esilv/A4/Nextgen%20IA/nextgen-ai-dia3/reports/td1.md).
