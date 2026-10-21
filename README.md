# Trustworthy Generative AI - DIA 3

ESILV - Data & Artificial Intelligence Major (Year 4 / S7)  
Course: Next-Generation AI (Didier Parisot)  
Pack version: `2026-10-14-students-1`  

> Engineering repository for **Trustworthy Generative AI**: automatic model routing by request difficulty, k-of-n quorum consensus for high-stakes decision verification, and cost-performance trade-off modeling across an e-commerce database benchmark.

---

## 1. Sub-group Identification

- **Class / Group**: DIA 3
- **Sub-group Members (6 members)**:
  1. **Louis Le Forestier** (`louis.le_forestier@edu.devinci.fr`)
  2. **Maxime Laurent** (`maxime.laurent@edu.devinci.fr`)
  3. **Baptiste Noailhac** (`baptiste.noailhac@edu.devinci.fr`)
  4. **Jean Jaunet** (`jean.jaunet@edu.devinci.fr`)
  5. **Alexandre Jullien Gaildraud** (`alexandre.jullien_gaildraud@edu.devinci.fr`)
  6. **Valentin Gourmelon** (`valentin.gourmelon@edu.devinci.fr`)

---

## 2. Work Distribution & Task Allocation (6-Member Breakdown)

To ensure strict compliance with the course protocol, minimize rate-limiting hazards (HTTP 429), and guarantee high-accuracy deliverables, the workload across TD 1 is systematically partitioned among all six members.

### Phase 1: Ground-Truth SQL References (`reference-td1.csv`)
Each member is assigned primary ownership of specific questions from [`questions-td1.json`](kit-td1/questions-td1.json) along with mandatory cross-verification of another member's queries on `boutique.sqlite`:

| Member | Assigned Questions | Question Focus | Cross-Checked By |
|---|---|---|---|
| **Louis Le Forestier** | **C01, C02, C03** | Date periods (half-open intervals `[start, end)`) | Maxime Laurent |
| **Maxime Laurent** | **C04, C05, C06** | Customer age brackets (exact day/month calculation) | Louis Le Forestier |
| **Baptiste Noailhac** | **C07, C08, C09** | Product categories & item filters | Jean Jaunet |
| **Jean Jaunet** | **C10, C11, C12, C13** | Combined joins & multi-condition revenue queries | Baptiste Noailhac |
| **Alexandre Jullien Gaildraud** | **C14, C15, C16, C17** | Aggregations, order status & volume constraints | Valentin Gourmelon |
| **Valentin Gourmelon** | **C18, C19, C20** | Edge cases, boundary dates & zero-match scenarios | Alexandre Jullien Gaildraud |

*Rule*: All reference revenue values must be integers in cents excluding VAT (`revenue_cents`), defaulting to `0` when no records match.

---

### Phase 2: Multi-Model Inference Execution (100 Base Calls)
Five members operate one assigned model batch (20 questions each), while the sixth member coordinates execution to respect the single-request-at-a-time subgroup constraint and aggregate traces:

| Operator | Member | Gate | Exact Model Identifier | Account / Output File |
|---|---|---|---|---|
| **Operator A** | Louis Le Forestier | Groq (Free) | `openai/gpt-oss-120b` | `traces-A.csv` / `state-A.jsonl` |
| **Operator B** | Maxime Laurent | Groq (Free) | `openai/gpt-oss-20b` | `traces-B.csv` / `state-B.jsonl` |
| **Operator C** | Baptiste Noailhac | OpenRouter (Free) | `cohere/north-mini-code:free` | Personal Account 1 / `traces-C.csv` |
| **Operator D** | Jean Jaunet | Groq (Free) | `qwen/qwen3.8-27b` | `traces-D.csv` / `state-D.jsonl` |
| **Operator E** | Alexandre Jullien Gaildraud | OpenRouter (Free) | `dots-studio/dots-3-note-preview:free` | Personal Account 2 / `traces-E.csv` |
| **Coordinator / Auditor** | Valentin Gourmelon | Subgroup Hub | Trace auditing, sequential pacing, rate-limit supervisor | Master `traces-td1.csv` & `traces-td1.jsonl` |

*Execution Rules*:
- Strictly **one ongoing request at a time** across the entire subgroup.
- Minimum **3 seconds pause** between consecutive calls.
- Maximum **1 retry** per failed cell.
- Never exceed personal free-tier allowances.

---

### Phase 3: Analysis, Summaries & Reporting Deliverables

| Deliverable | Lead Owners | Scope & Responsibilities |
|---|---|---|
| **`reference-td1.csv`** | All Members | 20 verified SQL queries and ground-truth values matching the instructor answer key. |
| **`traces-td1.csv` & `.jsonl`** | Valentin Gourmelon & Louis Le Forestier | Consolidation of all operator runs into a unified trace log, preserving all attempts. |
| **`model-question-comparison-en.csv`** | Maxime Laurent & Louis Le Forestier | Long-format comparison matrix (100 rows), verdict classification (`ok`, `wrong_value`, `sql_error`, `access_refused`), and root cause analysis in `explanation`. |
| **`five-model-summary-en.csv`** | Baptiste Noailhac & Jean Jaunet | Synthesis of the 5 models: documented public index, paid-route token prices (from portfolio), and accuracy breakdown by question family. |
| **`reports/td1.md`** | Alexandre Jullien Gaildraud & Valentin Gourmelon | Comprehensive session report detailing successes, failure taxonomy, SQL syntax divergences, and experimental evidence. |

---

## 3. Environment & Prerequisites

- **Python**: `>= 3.10` (verified on Python 3.11.9, SQLite 3.45.1)
- **Dependencies**: Python standard library + `requests`
- **Database Fingerprint (`boutique.sqlite`)**:
  `0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2` (seed `20260925`)
- **Access Verification Status**: 5/5 authorized models validated operational via `check_access.py`.

---

## 4. Setup & Execution Instructions

### A. Environment Initialization
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests
```

### B. Setting API Keys (in terminal memory only)
```powershell
$env:GROQ_API_KEY = "gsk_..."
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
```

### C. Running Integrity & Readiness Checks
```powershell
cd kit-td1
python verify-data.py
python check_access.py --no-network
```

### D. Operator Batch Commands (run from `kit-td1/`)

- **Operator A (Louis)**:
  ```powershell
  python skeleton-multi-llm-en.py --run --models groq:openai/gpt-oss-120b --cases C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C12,C13,C14,C15,C16,C17,C18,C19,C20 --state state-A.jsonl --out traces-A.csv
  ```

- **Operator B (Maxime)**:
  ```powershell
  python skeleton-multi-llm-en.py --run --models groq:openai/gpt-oss-20b --cases C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C12,C13,C14,C15,C16,C17,C18,C19,C20 --state state-B.jsonl --out traces-B.csv
  ```

- **Operator C (Baptiste)**:
  ```powershell
  python skeleton-multi-llm-en.py --run --models openrouter:cohere/north-mini-code:free --cases C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C12,C13,C14,C15,C16,C17,C18,C19,C20 --state state-C.jsonl --out traces-C.csv
  ```

- **Operator D (Jean)**:
  ```powershell
  python skeleton-multi-llm-en.py --run --models groq:qwen/qwen3.8-27b --cases C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C12,C13,C14,C15,C16,C17,C18,C19,C20 --state state-D.jsonl --out traces-D.csv
  ```

- **Operator E (Alexandre)**:
  ```powershell
  python skeleton-multi-llm-en.py --run --models openrouter:dots-studio/dots-3-note-preview:free --cases C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C12,C13,C14,C15,C16,C17,C18,C19,C20 --state state-E.jsonl --out traces-E.csv
  ```

---

## 5. Repository Structure

```text
nextgen-ai-dia3/
├── .gitignore                          # Excludes secrets, virtual environments, and local files
├── README.md                           # Team identification, work distribution & reproduction guide
├── prompts-en.md                       # Verbatim system messages and question prompt templates
├── reference-td1.csv                   # Reference queries and values for questions C01-C20 (TD1 hand-in)
├── model-question-comparison-en.csv    # Granular model-question comparison and traces pointers (TD1 hand-in)
├── five-model-summary-en.csv           # Sourced index, dated prices, and family summaries (TD1 hand-in)
├── reports/
│   ├── td1.md                          # Session 1 report: model comparison & trace analysis
│   ├── td2.md                          # Session 2 report: voting quorum & routing rule
│   └── td3.md                          # Session 3 report: costing & architectural decision
├── templates/                          # Templates and worksheets for subsequent sessions (TD2 & TD3)
│   ├── configuration-comparison-en.csv # Architecture and trade-off comparison matrix (TD3)
│   ├── cost-calculation-en.csv         # Token consumption and operational cost accounting (TD3)
│   ├── contributions-en.csv            # Member responsibilities and contribution tracking
│   ├── voting-tests-en.csv             # Consensus and quorum test suites (TD2)
│   └── routing-rule-en.md              # Routing policy specifications (TD2)
└── kit-td1/
    ├── data/                           # Verified boutique.sqlite database and CSV tables
    ├── schema.sql                      # Database relational schema (3 tables)
    ├── questions-td1.json              # 20 reference revenue questions
    ├── modeles-autorises.json          # Authorized model configurations and rate constraints
    ├── skeleton-multi-llm-en.py        # Core orchestration engine
    ├── sandbox_sqlite.py               # Read-only SQLite execution sandbox
    ├── check_access.py                 # Provider and access validation script
    ├── verify-data.py                  # Cryptographic SHA-256 data integrity check
    ├── atelier-vote.py                 # Voting workshop module (TD2)
    └── atelier-routage.py              # Routing workshop module (TD2)
```
