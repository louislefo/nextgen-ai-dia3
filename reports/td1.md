# TD 1 Report: Multi-Model Evaluation & SQL Querying

**Sub-group**: DIA 3 (Sub-group 2)  
**Course**: Next-Generation AI - Trustworthy Generative AI (ESILV S7)  
**Session Date**: 2026-10-21  
**Pack Version**: `2026-10-14-students-1`  

---

## 1. Executive Summary & Experimental Scope

The first lab session evaluated the empirical capabilities, syntax reliability, rate-limit resilience, and token economics of five authorized free language models across twenty structured e-commerce revenue queries executed against `data/boutique.sqlite`. 

The session verified the core premise of Trustworthy Generative AI:
1. **Frontier open-weights models** (`openai/gpt-oss-120b`) achieve flawless accuracy (20/20, 100%) but consume substantial token budgets and reasoning overhead.
2. **Compact models** (`openai/gpt-oss-20b` at 18/20, `dots-3-note-preview` at 15/20, `cohere/north-mini-code` at 13/20, and `qwen3.8-27b` at 13/20) introduce failure modes ranging from rate-limiting saturation (HTTP 429), syntax enclosure hallucinations (markdown code fences), and domain-specific logic flaws (calendar date age arithmetic).

---

## 2. Environment Verification & Pre-flight Integrity

Prior to running model calls, the environment was validated end-to-end:
- **Runtime Environment**: Python 3.11.9 with standard library modules and `requests` in a dedicated virtual environment (`.venv`).
- **Database & Data Cryptographic Hashes**: All SHA-256 digests of `data/boutique.sqlite` (`0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2`) and associated CSV tables matched the official `data/manifest.json` seed (`20260925`).
- **Access Check**: Initial probe (`check_access.py`) confirmed 5/5 model availability on Groq and OpenRouter.

---

## 3. Results Summary & Evaluation Matrix

Across the 100 base cells (with 4 retries, yielding 104 total logged attempts), the observed model performance was:

| Gate | Model Identifier | Evaluated Cells | Correct | Incorrect | Syntax Rejected | Not Executed (429) | Accuracy |
|---|---|---:|---:|---:|---:|---:|---:|
| Groq | `openai/gpt-oss-120b` | 20 | 20 | 0 | 0 | 0 | **100.0%** (20/20) |
| Groq | `openai/gpt-oss-20b` | 20 | 18 | 2 | 0 | 0 | **90.0%** (18/20) |
| OpenRouter | `dots-studio/dots-3-note-preview:free` | 20 | 15 | 3 | 2 | 0 | **75.0%** (15/20) |
| OpenRouter | `cohere/north-mini-code:free` | 20 | 13 | 7 | 0 | 0 | **65.0%** (13/20) |
| Groq | `qwen/qwen3.8-27b` | 20 | 13 | 5 | 0 | 2 | **65.0%** (13/20) |
| **Total** | **5 Models** | **100** | **79** | **17** | **2** | **2** | **79.0%** |

### Breakdown by Question Family
- **Period Queries** (C01, C04, C05, C06, C07, C20): Highest success rate. Standard SQL timestamps with half-open intervals `[start, end)` are well mastered by all models except when provider rate-limits hit (Qwen on C20).
- **Product List Queries** (C03, C12, C13, C14): Highly reliable across all models. `IN ('a', 'b', 'c')` filters were consistently generated.
- **Customer Age Queries** (C02, C08, C09, C10, C11) & **Combined Queries** (C15–C19): The primary source of failure across compact models.

---

## 4. Root Cause Analysis of Observed Failures

A rigorous taxonomy distinguishes observable facts from hypotheses:

### Category 1: Provider Quota & Rate Limiting (Observed Facts)
- **Model**: `groq:qwen/qwen3.8-27b` on cases **C16** and **C20**.
- **Evidence**: Returned HTTP status `429` with error message:
  `Rate limit reached for model qwen/qwen3.8-27b in organization org_... on output tokens per minute (OTPM): Limit 1000, Used 865, Requested 186`.
- **Cause**: Groq enforces an aggressive 1,000 OTPM limit on the free tier for this model. Consecutive sequential calls exhausted the per-minute token refill window, leaving the cell in `not_executed` status as per the protocol retry bounds.

### Category 2: Formatting Instruction Violation (Observed Facts)
- **Model**: `openrouter:dots-studio/dots-3-note-preview:free` on cases **C09** and **C17**.
- **Evidence**: The model returned SQL wrapped in markdown backticks:
  ```sql
  SELECT COALESCE(...)
  ```
- **Cause**: The read-only SQLite sandbox authorizer requires raw executable SQL without markdown formatting. The parser strictly rejected the token ````sql`, resulting in `sql_rejected`.

### Category 3: Semantic Logic Errors on Completed Age (Observed Facts & Hypotheses)
- **Models**: `cohere/north-mini-code:free` (C02, C08, C09, C10, C11), `qwen/qwen3.8-27b` (C09, C10), `openai/gpt-oss-20b` (C02, C11).
- **Evidence**: Models computed age as a raw difference of years:
  `CAST(strftime('%Y', ref_date) AS INT) - CAST(strftime('%Y', birth_date) AS INT) = 25`
- **Cause**: This formulation ignores whether the birthday has already occurred in the reference year, violating the "completed age" convention. In contrast, `gpt-oss-120b` correctly incorporated the day/month boundary check:
  `strftime('%Y', ref_date) - strftime('%Y', birth_date) - (strftime('%m-%d', ref_date) < strftime('%m-%d', birth_date)) = 25`.

---

## 5. Team Contributions

| Member | Assigned Reference Questions | Model Batch Operated | Deliverables Ownership |
|---|---|---|---|
| **Louis Le Forestier** | C01, C02, C03 | Model A (`gpt-oss-120b`, 20/20) | Reference queries, comparison matrix, traces merge |
| **Maxime Laurent** | C04, C05, C06 | Model B (`gpt-oss-20b`, 18/20) | Comparison matrix authoring, cross-checks |
| **Baptiste Noailhac** | C07, C08, C09 | Model C (`cohere/north-mini-code`, 13/20) | Model summary, token price analysis |
| **Jean Jaunet** | C10, C11, C12, C13 | Model D (`qwen/qwen3.8-27b`, 13/20) | Cross-check automation, model summary |
| **Alexandre Jullien Gaildraud** | C14, C15, C16, C17 | Model E (`dots-3-note-preview`, 15/20) | Session report authoring, failure taxonomy |
| **Valentin Gourmelon** | C18, C19, C20 | Master Coordination & Audit | Sequential call supervisor, trace audit, reporting |
| **Romain Thepaut** | Secondary reviewer (supporting C01–C20) | Backup monitoring & observation | Deliverable quality assurance, proofreading, format validation |

---

## 6. Key Learnings & Preparation for TD 2

1. **Model Hierarchy**: `gpt-oss-120b` operates as a reliable baseline judge, whereas 20B and lightweight models require validation or routing safeguards on non-trivial logic.
2. **Quorum Hypothesis (TD 2)**: Querying three lightweight models (e.g., 20B, Dots, Cohere) on period questions will yield consistent agreement at low cost, while age-related questions will trigger abstention due to divergence in date arithmetic.
3. **Routing Rule Foundation**: Simple period and product queries can safely route to zero-cost or small models, reserving high-capability models for complex multi-condition queries.
