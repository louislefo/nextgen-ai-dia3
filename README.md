# Trustworthy Generative AI - DIA 3

ESILV - Data & Artificial Intelligence Major (Year 4 / S7)  
Course: Next-Generation AI (Didier Parisot)  
Pack version: `2026-10-14-students-1`  

> Engineering repository for **Trustworthy Generative AI**: automatic model routing by request difficulty, k-of-n quorum consensus for high-stakes decision verification, and cost-performance trade-off modeling across an e-commerce database benchmark.

## Sub-group Identification

- **Class / Group**: DIA 3
- **Sub-group Members**:
  - Louis Le Forestier (louis.le_forestier@edu.devinci.fr)
  - Maxime Laurent (maxime.laurent@edu.devinci.fr)
  - Baptiste Noailhac (baptiste.noailhac@edu.devinci.fr)
  - Jean Jaunet (jean.jaunet@edu.devinci.fr)
  - Alexandre Jullien Gaildraud (alexandre.jullien_gaildraud@edu.devinci.fr)
  - Valentin Gourmelon (valentin.gourmelon@edu.devinci.fr)

## Environment & Prerequisites

- **Python**: >= 3.10 (verified on Python 3.11.9, SQLite 3.45.1)
- **Dependencies**: Python standard library + `requests`
- **Database Fingerprint (`boutique.sqlite`)**:
  `0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2` (seed `20260925`)
- **Access Verification Status**: 5/5 models verified and active (Groq and OpenRouter free tiers).

## Setup & Execution Instructions

1. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install requests
   ```

2. Set API keys in your environment (never commit keys to git):
   ```powershell
   $env:GROQ_API_KEY = "gsk_..."
   $env:OPENROUTER_API_KEY = "sk-or-v1-..."
   ```

3. Run data integrity and access checks:
   ```powershell
   cd kit-td1
   python verify-data.py
   python check_access.py
   ```

## Repository Structure

```text
├── .gitignore                          # Excludes secrets, virtual environments, and local files
├── README.md                           # Sub-group identification and reproduction instructions
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
