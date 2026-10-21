# TD 1 Report: Multi-Model Evaluation & SQL Querying

**Sub-group**: DIA 3  
**Course**: Next-Generation AI - Trustworthy Generative AI (ESILV S7)  
**Session Date**: 2026-10-21  
**Pack Version**: `2026-10-14-students-1`  

---

## 1. Executive Summary & Objectives

The primary objective of TD 1 is to evaluate the behavior, accuracy, and operational cost of five authorized language models across twenty structured revenue queries applied to an e-commerce database (`boutique.sqlite`). 

The exercise addresses a central trade-off in generative AI engineering:
- Flagship frontier models are capable but costly and constrained by strict quotas.
- Lighter, economical models present higher failure rates, syntax hallucinations, and domain mismatches.
- TD 1 establishes the baseline accuracy and failure modes of each model against independently verified SQL reference calculations.

---

## 2. Environment Verification & Pre-flight Checks

Prior to the lab session, the runtime environment and network access were comprehensively validated:

- **Local Interpreter**: Python 3.11.9 with standard library dependencies and `requests` installed within an isolated virtual environment (`.venv`).
- **Database Integrity**: The cryptographic SHA-256 hash of `data/boutique.sqlite` (`0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2`) and associated CSV tables match the official `data/manifest.json` seed (`20260925`).
- **Model Access Status**: Execution of `check_access.py` verified operational connectivity across all five required free-tier routes (5/5 OK):
  1. `groq/openai/gpt-oss-120b` (Free tier)
  2. `groq/openai/gpt-oss-20b` (Free tier)
  3. `groq/qwen/qwen3.8-27b` (Free tier)
  4. `openrouter/cohere/north-mini-code:free` (Free tier)
  5. `openrouter/dots-studio/dots-3-note-preview:free` (Free tier)

The execution output has been archived in `ready-for-td1.txt` as verification proof.

---

## 3. Experimental Protocol & Batch Design

The evaluation protocol involves:
- **Reference Establishment**: Independent calculation of the twenty ground-truth revenue figures (`reference-td1.csv`) via manual SQL queries executed on `boutique.sqlite`.
- **Inference Batch**: 100 base calls (20 questions x 5 models), divided into 60 Groq requests and 40 OpenRouter requests to respect individual free-tier rate limits and prevent HTTP 429 quota exhaustion.
- **Sandboxed Execution**: Query responses are parsed and executed in read-only mode using `sandbox_sqlite.py`. Numerical outputs are automatically compared against the ground-truth reference values.
- **Trace Archiving**: Every attempt, timing, token count, and HTTP status is persisted in `traces-td1.jsonl` and `traces-td1.csv`.

---

## 4. Work Distribution & Initial Roles

| Member | Focus Area & Assigned Tasks | Environment Setup |
|---|---|---|
| Louis Le Forestier | Reference queries C01-C03, Operator A (`groq:openai/gpt-oss-120b`), comparison synthesis | Validated |
| Maxime Laurent | Reference queries C04-C06, Operator B (`groq:openai/gpt-oss-20b`), comparison synthesis | Validated |
| Baptiste Noailhac | Reference queries C07-C09, Operator C (`openrouter:cohere/north-mini-code:free`), model summary | Validated |
| Jean Jaunet | Reference queries C10-C13, Operator D (`groq:qwen/qwen3.8-27b`), model summary | Validated |
| Alexandre Jullien Gaildraud | Reference queries C14-C17, Operator E (`openrouter:dots-studio/dots-3-note-preview:free`), report authoring | Validated |
| Valentin Gourmelon | Reference queries C18-C20, sequential call coordination, master trace auditor & report authoring | Validated |

---

## 5. Next Steps for the On-site Session

1. Calculate and cross-verify the 20 ground-truth SQL reference values.
2. Execute the 100-cell evaluation matrix using `skeleton-multi-llm-en.py`.
3. Analyze syntax errors, schema misunderstandings, and numerical discrepancies.
4. Populate `model-question-comparison-en.csv` and `five-model-summary-en.csv` for plenary presentation.
