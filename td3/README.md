# TD 3: Cost Quantification, Configuration Benchmarking & Architectural Decision

**Sub-group**: DIA 3 - Group 2  
**Institution**: ESILV - Major Data & Artificial Intelligence (Year 4 / S7)  
**Course**: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
**Session Date**: 2026-12-11  
**Pack Version**: `2026-11-18-students-5`  
**Official Assignment**: `students/kit-td1/enonce-td3-en.html`  

---

## 1. Overview and Core Objectives

TD 3 concludes the module by synthesizing technical accuracy, voting consensus, and operational economics into a production architectural decision for a named business use case.

Key objectives:
1. **Configuration Costing & Accounting**: Building a multi-configuration benchmark table with dual-column cost tracking (API-equivalent token cost vs real cash expenditure) across five distinct serving strategies.
2. **Operational Decision for a Named Use Case**: Contextualizing model reliability against the financial and reputational cost of an error for a specific operational deployment.
3. **The Three-Slide Pitch & In-Person Defense**: Presenting the engineering recommendation on three concise slides and proving live at your table where every metric originates from stored trace records.

---

## 2. Session Schedule & Evaluation Structure

```
+---------------------------------------------------------------------------------------+
| 13:30 - 14:30 | Step 1: Configuration Benchmarking Table & Cost Accounting           |
+---------------------------------------------------------------------------------------+
| 14:30 - 15:15 | Step 2: Named Use Case Decision & Three-Slide Pitch Preparation       |
+---------------------------------------------------------------------------------------+
| 15:15 - 15:30 | Break                                                                 |
+---------------------------------------------------------------------------------------+
| 15:30 - 17:30 | Step 3: In-Person Table Review with Course Instructors (C1, C2, C3)   |
+---------------------------------------------------------------------------------------+
| 17:30 - 17:45 | Final Marking of the Session                                          |
+---------------------------------------------------------------------------------------+
| 17:45 - 18:00 | Individual Final Quiz on Moodle (15 minutes)                          |
+---------------------------------------------------------------------------------------+
```

---

## 3. Core Steps and Deliverables

### Step 1: The Configuration Table
Quantify at least five distinct architectural configurations across the 20 benchmark questions:
1. **Cheapest Single Model**: The lowest-cost model exhibiting 100% accuracy on the specific question family.
2. **Best Single Model Overall**: The highest-performing standalone model (`openai/gpt-oss-120b`).
3. **Fixed 2-of-3 Panel Quorum**: Majority vote across `openai/gpt-oss-120b`, `cohere/north-mini-code:free`, and `qwen/qwen3.8-27b` ($k=2$).
4. **3-of-5 Full Quorum**: Majority vote across all five evaluated models ($k=3$).
5. **Sub-group Dynamic Routing Policy**: The adaptive routing rule developed in TD 2.

*Costing Accounting Contract*:
- **API-Equivalent Cost**: Theoretical expenditure based on public per-million token pricing from `portefeuille-modeles-2026-09-28.csv`.
- **Real Spend**: Actual cash paid out during experiments (zero for free tiers/promotional grants).
- All pricing must be explicitly dated and sourced.

### Step 2: The Business Decision & Three-Slide Pitch
Select and formalize a specific business use case:
- **Internal Analytics Dashboard** (Low stakes): Internal operational reporting where an error carries low financial impact.
- **Customer-Facing Self-Service** (Medium stakes): Directly visible client figures where hallucinations harm brand reputation.
- **Financial Payout & Billing Engine** (Critical stakes): Automated financial transactions where errors result in immediate monetary loss.

*The Three Slides*:
- **Slide 1: Operational Context & Use Case**: Defined use case, error cost quantification, latency tolerance, and risk profile.
- **Slide 2: Configuration Benchmark Matrix**: Comparative table displaying accuracy, median latency, token costs, cash spend, and abstention rates across the five configurations.
- **Slide 3: Recommended Architecture & Production Policy**: The chosen configuration justified by error economics, safety checks, failover rules, and explicit documentation of what the 20-question benchmark does not cover.

### Step 3: In-Person Table Review
The instructor conducts table reviews from 15:30 to 17:30:
- Screen inspection of the live repository, configuration table, and three slides.
- Spot checks requiring students to trace specific figures back to exact lines in `traces-td1.csv` and SQL execution logs.
- Evaluation on criteria **C1** (Costing accuracy and trace evidence), **C2** (Relevance of the use case decision), and **C3** (Clarity and transparency of limitations).

---

## 4. Expected Artifacts in this Directory

```text
td3/
├── README.md                           # TD 3 specification and preparation guide
├── configuration-comparison-en.csv     # Multi-configuration accuracy and cost matrix
├── cost-calculation-en.csv             # Token consumption and pricing breakdown worksheet
└── slides/                             # Final three-slide presentation deck (PDF / Markdown / HTML)
```

---

## 5. Preparation Checklist

Before the start of TD 3 on 11 December 2026:
- [ ] Confirm all members have reviewed the token consumption metrics in `traces-td1.csv`.
- [ ] Validate model pricing in `portefeuille-modeles-2026-09-28.csv`.
- [ ] Align on the candidate business use case and error cost formula.
- [ ] Prepare template files in `templates/` and link to [reports/td3.md](file:///c:/Users/louis/OneDrive/Desktop/Esilv/A4/Nextgen%20IA/nextgen-ai-dia3/reports/td3.md).
