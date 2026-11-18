# Trustworthy Generative AI - DIA 3 - Group 2 

**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Academic Year**: 2026 - 2027  
**Official Portal**: [https://louislefo.github.io/nextgen-ai-dia3/](https://louislefo.github.io/nextgen-ai-dia3/)  

---

## 1. Sub-group Identification

- **Major / Group**: DIA 3 (Data & Artificial Intelligence) - Sub-group 2
- **Team Members (7 members)**:
  1. **Louis Le Forestier** (`louis.le_forestier@edu.devinci.fr`) - Lead Engineer & Consensus System
  2. **Maxime Laurent** (`maxime.laurent@edu.devinci.fr`) - Evaluation & Co-Lead Engineer
  3. **Baptiste Noailhac** (`baptiste.noailhac@edu.devinci.fr`) - SQL Diagnostics & Data Integrity
  4. **Jean Jaunet** (`jean.jaunet@edu.devinci.fr`) - Database Investigation & SQL Modeling
  5. **Alexandre Jullien Gaildraud** (`alexandre.jullien_gaildraud@edu.devinci.fr`) - Routing Policy Architect
  6. **Valentin Gourmelon** (`valentin.gourmelon@edu.devinci.fr`) - Simulator & Concurrency Coordinator
  7. **Romain Thepaut** (`romain.thepaut@edu.devinci.fr`) - SQL Investigation & Evidence Auditor (Group B)

---

## 2. Course Roadmap & Session Index

The module is structured around three sequential laboratory sessions combining empirical benchmark evaluation, consensus engineering, and operational cost optimization:

| Session | Date | Theme & Core Focus | Deliverables & Artifacts | Status |
|---|---|---|---|---|
| **TD 1** | **2026-10-21** | **Compare**: Multi-model evaluation across 5 free heterogeneous LLMs against a deterministic relational SQL benchmark. | [td1/README.md](td1/README.md)<br>[reports/td1.md](reports/td1.md) | **Completed** |
| **TD 2** | **2026-11-18** | **Vote & Route**: $k$-of-$n$ majority voting quorum, false consensus SQL diagnostics, dynamic model routing rules. | [td2/README.md](td2/README.md)<br>[td2/PLAN.md](td2/PLAN.md)<br>[reports/td2.md](reports/td2.md) | **Active** |
| **TD 3** | **2026-12-11** | **Quantify & Decide**: Configuration costing (token pricing vs real spend), named business use case decision, 3-slide pitch. | [td3/README.md](td3/README.md)<br>[reports/td3.md](reports/td3.md) | **Upcoming** |

---

## 3. Repository Architecture

```text
nextgen-ai-dia3/
├── .github/
│   └── workflows/
│       └── deploy-pages.yml            # Automated CI/CD deploying website to GitHub Pages
├── .gitignore                          # Excludes secrets (.env), virtual environments, and caches
├── .gitattributes                     # Enforces LF endings across platforms for dataset hashing
├── README.md                           # Executive course overview, team roster & roadmap (this file)
├── reports/                            # Official session markdown reports for Moodle submission
│   ├── td1.md                          # TD 1 report: model comparison, failure taxonomy & evidence
│   ├── td2.md                          # TD 2 report: quorum implementation & false consensus proof
│   └── td3.md                          # TD 3 report: costing synthesis & architectural decision
├── td1/                                # TD 1: Baseline evaluation workspace
│   ├── README.md                       # TD 1 comprehensive guide, operator allocation & reproduction
│   ├── data/                           # Verified SQLite database (boutique.sqlite) and CSV tables
│   ├── check_access.py                 # Provider and access validation script
│   ├── compute_references.py           # Automated reference SQL calculation script
│   ├── crosscheck-td1.py               # Deterministic reference validator
│   ├── sandbox_sqlite.py               # Read-only SQLite execution sandbox
│   ├── skeleton-multi-llm-en.py        # Core multi-model orchestration client
│   ├── verify-data.py                  # Cryptographic SHA-256 integrity verification
│   ├── reference-td1.csv               # 20 ground-truth SQL queries and revenue values
│   ├── traces-td1.csv                  # Master log of all 104 inference attempts
│   ├── traces-td1.jsonl                # Raw JSONL execution traces with fingerprints
│   ├── model-question-comparison-en.csv# 100-cell evaluation matrix and error taxonomy
│   └── five-model-summary-en.csv       # Model family accuracy & token price index
├── td2/                                # TD 2: Quorum consensus and dynamic routing workspace
│   ├── README.md                       # TD 2 comprehensive guide, pair breakdown & instructions
│   ├── PLAN.md                         # Detailed action plan, pair assignments, and schedule
│   ├── skeleton-multi-llm-en.py        # Orchestration client containing vote_k_sur_n
│   ├── atelier-vote.py                 # Quorum voting test and benchmark harness
│   ├── atelier-routage.py              # Dynamic model routing and resource simulator
│   ├── pair-b/                         # Step 2: false consensus diagnosis & delta SQL evidence
│   ├── qa/verify-td2.py                # Offline verification harness: 12 checks, exit 1 on failure
│   ├── data/                           # Local copy of the verified SQLite database
│   ├── reference-td1.csv               # Ground-truth reference values in cents
│   └── traces-td1.csv                  # TD 1 master inference trace log
├── td3/                                # TD 3: Costing and business decision workspace
│   └── README.md                       # TD 3 preparation guide, costing model & pitch framework
├── reviews/                            # Peer cross-check logs & quality audits
│   ├── README.md                       # Cross-check directory index and methodology
│   ├── crosscheck-01.md ... 03.md      # TD 1 SQL reference cross-checks (6 reviews)
│   ├── crosscheck-04.md                # TD 1 multi-model trace & pacing audits (2 reviews)
│   ├── crosscheck-05.md                # TD 2 voting quorum engine audits (2 reviews)
│   ├── crosscheck-06.md                # TD 2 false consensus & routing audits (2 reviews)
│   └── crosscheck-07.md                # TD 2 automated verification pass (12 scripted checks)
├── website/                            # GitHub Pages live interactive portal
│   ├── css/style.css                   # Custom responsive stylesheet
│   ├── index.html                      # Executive project dashboard & team presentation
│   ├── td1.html                        # TD 1 benchmark visualization & error taxonomy
│   ├── td2.html                        # TD 2 voting quorum & routing rule analysis
│   └── td3.html                        # TD 3 costing & live decision framework
└── templates/                          # Templates for worksheets and submissions
    ├── configuration-comparison-en.csv # Architecture comparison matrix template
    ├── cost-calculation-en.csv         # Token and cash accounting worksheet template
    ├── contributions-en.csv            # Member contribution log template
    ├── voting-tests-en.csv             # Consensus test cases template
    └── routing-rule-en.md              # Routing rule specification template
```

---

## 4. Environment & Prerequisites

- **Python**: `>= 3.10` (tested on Python 3.11.9, SQLite 3.45.1)
- **Dependencies**: Python standard library + `requests`
- **Database Fingerprint (`boutique.sqlite`)**:
  `0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2` (seed `20260925`)

### Environment Setup
```powershell
# Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install runtime dependencies
pip install requests
```

### API Credentials (Required only for live inference in TD 1)
Keys must be exported strictly into the current shell session memory and never committed to version control:
```powershell
$env:GROQ_API_KEY = "gsk_..."
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
```

---

## 5. Engineering Principles & Guidelines

1. **Trace-Backed Evidence**: Every assertion, accuracy rate, or failure classification must point directly to a verifiable line in `traces-td1.csv` or an executed query on `data/boutique.sqlite`.
2. **Deterministic Ground Truth**: Model answers are never used to establish reference values. All ground truth is verified independently through peer-audited SQL.
3. **Fail-Safe Abstention**: When confidence is insufficient or a voting quorum is not reached, systems must abstain rather than fabricate unverified answers.
4. **Offline Reproducibility**: After TD 1, all consensus voting and routing evaluations run 100% offline using recorded traces, requiring zero API credits.
