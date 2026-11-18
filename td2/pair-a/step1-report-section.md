## 2. Quorum Implementation & Threshold Testing

### 2.1 Quorum Engine Architecture & Contract (`vote_k_sur_n`)

The consensus voting engine `Orchestrateur.vote_k_sur_n(self, traces_question, k)` has been implemented in `skeleton-multi-llm-en.py` (and synchronized in `td2/skeleton-multi-llm-en.py`) adhering strictly to the operational contract specified in TD 2:

1. **Strict Majority Constraint**: The threshold $k$ must represent an absolute strict majority of the total panel size $n = \text{len}(\text{traces\_question})$, defined by $\lfloor n / 2 \rfloor < k \le n$. Any configuration violating this (such as $k \le n//2$ or $k > n$) raises a `ValueError`. For $n=3$, $k$ must be $2$ or $3$; for $n=5$, $k$ must be $3, 4,$ or $5$.
2. **Provider-Model Unicity**: Duplicate proposals sharing identical `(provider, model_requested)` pairs are rejected with a `ValueError`. Duplicate responses from the same architecture cannot fabricate additional consensus weight.
3. **Safe Abstention & Error Isolation**: Proposals marked with non-executed verdicts (e.g. HTTP 429 rate limits, connection timeouts, or unparseable queries) or carrying `None`/empty values remain counted within total panel size $n$, but cast **zero votes**. This ensures an unavailable model cannot artificially deflate the denominator to produce an unsafe minority consensus.
4. **Deterministic Resolution**:
   - If a numerical candidate value receives $\ge k$ votes, the engine outputs:
     `{"consensus": True, "value": v, "votes": count, "models": ["provider:model", ...]}`
   - If no value reaches $k$, the engine returns:
     `{"consensus": False, "value": None, "votes": max_votes, "models": []}`
   - The engine never interpolates, averages, or invents values. Ground-truth references are evaluated strictly downstream of the vote decision.

---

### 2.2 Synthetic Validation Suite (`atelier-vote.py`)

The engine was validated against the four baseline synthetic test scenarios defined in `atelier-vote.py` ($n=3, k=2$), confirming strict conformity across all edge cases:

```bash
$ python atelier-vote.py
{"example": "agreement", "nature": "simulation", "n": 3, "k": 2, "decision": {"consensus": true, "value": 100, "votes": 2, "models": ["groq:openai/gpt-oss-120b", "openrouter:cohere/north-mini-code:free"]}, "reference": 100, "matches_reference": true}
{"example": "disagreement", "nature": "simulation", "n": 3, "k": 2, "decision": {"consensus": false, "value": null, "votes": 1, "models": []}, "reference": 100, "matches_reference": null}
{"example": "unavailable", "nature": "simulation", "n": 3, "k": 2, "decision": {"consensus": false, "value": null, "votes": 1, "models": []}, "reference": 100, "matches_reference": null}
{"example": "wrong consensus", "nature": "simulation", "n": 3, "k": 2, "decision": {"consensus": true, "value": 0, "votes": 2, "models": ["groq:openai/gpt-oss-120b", "openrouter:cohere/north-mini-code:free"]}, "reference": 100, "matches_reference": false}
```

- **Agreement**: 2 of 3 models propose `100` $\rightarrow$ Consensus reached ($2/3$), matching ground truth.
- **Disagreement**: Split proposals (`100`, `110`, `120`) $\rightarrow$ Abstention safely triggered (`consensus: False, value: None, votes: 1`).
- **Unavailable**: 2 members fail or time out (`[100, None, None]`) $\rightarrow$ Engine retains $n=3$, rejects solitary vote as insufficient ($1 < 2$), and abstains safely.
- **Wrong Consensus**: 2 models share an identical hallucinated output (`0` vs reference `100`) $\rightarrow$ Consensus forms ($2/3$), matching ground truth is `False`. This highlights that quorum eliminates independent hallucinations, but remains vulnerable to correlated multi-model failure modes.

Single-case verification on real TD 1 traces (`atelier-vote.py --traces traces-td1.csv --case C02`):
```bash
$ python atelier-vote.py --traces traces-td1.csv --case C02
{"case": "C02", "nature": "real", "n": 3, "k": 2, "decision": {"consensus": true, "value": 590320, "votes": 2, "models": ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b"]}, "reference": 590320, "matches_reference": true}
```

---

### 2.3 Twenty-Question Benchmark Matrix: 2-of-3 vs. 3-of-5 Quorum

The evaluation was executed across all twenty questions (C01 to C20) using stored TD 1 execution traces (`traces-td1.csv`):
- **Fixed 3-Model Panel ($2$-of-$3$, $k=2$)**: `openai/gpt-oss-120b` (Groq), `cohere/north-mini-code:free` (OpenRouter), `qwen/qwen3.8-27b` (Groq).
- **Full 5-Model Quorum ($3$-of-$5$, $k=3$)**: Adding `openai/gpt-oss-20b` (Groq) and `dots-studio/dots-3-note-preview:free` (OpenRouter).
- **Ground Truth**: Extracted from independently audited SQL references (`reference-td1.csv`).

| Case ID | Reference (cents) | 2-of-3 Decision ($k=2$) | 2-of-3 Kept Value | 2-of-3 Votes | 2-of-3 Match | 3-of-5 Decision ($k=3$) | 3-of-5 Kept Value | 3-of-5 Votes | 3-of-5 Match | Transition Classification |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **C01** | 792,800 | Consensus | 792,800 cts | 3/3 | **YES** | Consensus | 792,800 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C02** | 590,320 | Consensus | 590,320 cts | 2/3 | **YES** | Consensus | 590,320 cts | 3/5 | **YES** | Consensus Maintained (Margin +1) |
| **C03** | 936,350 | Consensus | 936,350 cts | 3/3 | **YES** | Consensus | 936,350 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C04** | 2,826,250 | Consensus | 2,826,250 cts | 3/3 | **YES** | Consensus | 2,826,250 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C05** | 38,480 | Consensus | 38,480 cts | 3/3 | **YES** | Consensus | 38,480 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C06** | 0 | Consensus | 0 cts | 3/3 | **YES** | Consensus | 0 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C07** | 13,970 | Consensus | 13,970 cts | 3/3 | **YES** | Consensus | 13,970 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C08** | 605,580 | Consensus | 605,580 cts | 2/3 | **YES** | Consensus | 605,580 cts | 4/5 | **YES** | Consensus Maintained (Margin +2) |
| **C09** | 487,980 | **Consensus** | **0 cts** | 2/3 | **NO (False Cons.)** | **Abstention** | **None** | 2/5 | **N/A** | **CRITICAL: False Consensus Overturned $\rightarrow$ Safe Abstention** |
| **C10** | 558,980 | Abstention | None | 1/3 | N/A | Abstention | None | 2/5 | N/A | Abstention Maintained (Split Disagreement) |
| **C11** | 446,690 | Consensus | 446,690 cts | 2/3 | **YES** | Consensus | 446,690 cts | 3/5 | **YES** | Consensus Maintained (Margin +1) |
| **C12** | 1,666,490 | Consensus | 1,666,490 cts | 3/3 | **YES** | Consensus | 1,666,490 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C13** | 107,740 | Consensus | 107,740 cts | 3/3 | **YES** | Consensus | 107,740 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C14** | 0 | Consensus | 0 cts | 3/3 | **YES** | Consensus | 0 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C15** | 168,680 | Consensus | 168,680 cts | 2/3 | **YES** | Consensus | 168,680 cts | 3/5 | **YES** | Consensus Maintained (Margin +1) |
| **C16** | 376,740 | Consensus | 376,740 cts | 2/3 | **YES** | Consensus | 376,740 cts | 3/5 | **YES** | Consensus Maintained (429 Handled, Margin +1) |
| **C17** | 258,180 | Abstention | None | 1/3 | N/A | Abstention | None | 2/5 | N/A | Abstention Maintained (Split Disagreement) |
| **C18** | 62,480 | Consensus | 62,480 cts | 3/3 | **YES** | Consensus | 62,480 cts | 5/5 | **YES** | Unanimous (5/5) |
| **C19** | 1,990 | **Abstention** | **None** | 1/3 | **N/A** | **Consensus** | **1,990 cts** | 3/5 | **YES** | **CRITICAL: Abstention $\rightarrow$ True Consensus Recovered** |
| **C20** | 1,106,090 | Consensus | 1,106,090 cts | 2/3 | **YES** | Consensus | 1,106,090 cts | 4/5 | **YES** | Consensus Maintained (429 Handled, Margin +2) |

---

### 2.4 In-Depth Analysis of Decision Transitions and Vote Dynamics

The shift from a 2-of-3 panel to a 3-of-5 quorum alters the operational decision on **2 out of 20 questions (C09 and C19)**, and reinforces vote margins on **6 questions (C02, C08, C11, C15, C16, C20)**.

#### 1. Case C09: Elimination of False Consensus through Quorum Expansion
- **Question Prompt**: Total revenue excluding VAT in cents generated by customers exactly 25 years old on 2026-09-26.
- **Reference Ground Truth**: `487,980` cents.
- **Trace Audit & Verdicts**:
  - `openai/gpt-oss-120b`: `487,980` cents (`verdict: correct`)
  - `cohere/north-mini-code:free`: `0` cents (`verdict: incorrect`)
  - `qwen/qwen3.8-27b`: `0` cents (`verdict: incorrect`)
  - `openai/gpt-oss-20b`: `487,980` cents (`verdict: correct`)
  - `dots-studio/dots-3-note-preview:free`: `None` (`verdict: sql_rejected` due to multi-block markdown formatting)
- **2-of-3 Failure Mechanism**: In the 3-model panel, both `cohere` and `qwen` generated faulty age-calculation clauses (Cohere used substring operations resulting in empty filters; Qwen miscalculated order-date year intervals). Both executed queries cleanly returned `0`. Because $k=2$ in 2-of-3, the shared erroneous value `0` reached majority ($2/3$), resulting in a **False Consensus** (`matches_reference: False`).
- **3-of-5 Recovery**: When evaluated across 5 models, `openai/gpt-oss-20b` correctly identified the boundary dates (`BETWEEN '2000-09-27' AND '2001-09-26'`) and voted `487,980`. `dots-studio` failed validation and cast no vote. The vote distribution formed a $2$ vs $2$ deadlock (`0`: 2 votes, `487,980`: 2 votes). Neither value reached the required threshold $k=3$.
- **Impact**: Expanding to 3-of-5 prevented a severe business failure: an incorrect automated financial decision was suppressed and converted into a **safe abstention** (`consensus: False, value: None`).

#### 2. Case C19: Recovery of True Consensus from an Abstention
- **Question Prompt**: Revenue from product `d` placed between 2026-09-01 and 2026-10-01 by customers exactly 25 years old on 2026-09-25.
- **Reference Ground Truth**: `1,990` cents.
- **Trace Audit & Verdicts**:
  - `openai/gpt-oss-120b`: `1,990` cents (`verdict: correct`)
  - `cohere/north-mini-code:free`: `13,930` cents (`verdict: incorrect` - missing product constraint)
  - `qwen/qwen3.8-27b`: `83,580` cents (`verdict: incorrect` - inverted anniversary clause)
  - `openai/gpt-oss-20b`: `1,990` cents (`verdict: correct`)
  - `dots-studio/dots-3-note-preview:free`: `1,990` cents (`verdict: correct`)
- **2-of-3 Failure Mechanism**: Each of the three initial models returned a distinct value (`1,990`, `13,930`, `83,580`). The maximum vote count was $1 < 2$, forcing the 2-of-3 system into an **Abstention**.
- **3-of-5 Recovery**: Both `openai/gpt-oss-20b` and `dots-studio/dots-3-note-preview:free` correctly modeled both the product filter and the customer anniversary window, voting `1,990`. Combined with `gpt-oss-120b`, the ground-truth value achieved **3 out of 5 votes** (60%), satisfying $k=3$.
- **Impact**: The larger quorum successfully gathered sufficient collective intelligence to **recover true consensus** from an unnecessary abstention.

#### 3. Operational Resilience to HTTP 429 Rate Limits (Cases C16 and C20)
- On cases **C16** and **C20**, `qwen/qwen3.8-27b` experienced provider-side quota exhaustion on Groq (`http_status: 429`, `verdict: not_executed`).
- Under our voting engine implementation, Qwen remained in $n$ ($n=3$ and $n=5$), but contributed zero votes.
- In **2-of-3**: `gpt-oss-120b` and `cohere` both voted correctly (`376,740` on C16, `1,106,090` on C20), securing the minimal $2/3$ majority despite the missing member.
- In **3-of-5**: With Qwen unavailable and threshold elevated to $k=3$:
  - On **C16**: `gpt-oss-20b` supplied the needed 3rd vote (`376,740`), ensuring consensus survived the loss of Qwen and the hallucination of Dots (`211,260`).
  - On **C20**: Both `gpt-oss-20b` and `dots-studio` voted `1,106,090`, securing a robust $4/5$ supermajority (80%).

#### 4. Persistent Disagreements on Complex Queries (Cases C10 and C17)
- **Case C10** (Dynamic customer age evaluated at order date):
  - 2-of-3: `gpt-120b` (`558,980`), `cohere` (`0`), `qwen` (`119,410`). All three disagreed ($1/3$).
  - 3-of-5: `gpt-120b` and `gpt-20b` voted `558,980` (2 votes); `qwen` and `dots` voted `119,410` (2 votes); `cohere` voted `0` (1 vote). Max votes = 2 < 3.
  - Abstention is maintained, accurately reflecting model disagreement on correlated subquery joins.
- **Case C17** (Multi-table join combining product IDs, date period, and static age):
  - 2-of-3: Split 1-1-1 (`258,180`, `197,080`, `248,490`).
  - 3-of-5: `gpt-20b` joined `gpt-120b` with `258,180` (2 votes), but `dots` failed SQL execution (`sql_rejected`). Max votes = 2 < 3. Abstention is cleanly maintained.

---

### 2.5 Quantitative Performance Summary: 2-of-3 vs 3-of-5

| Metric | Fixed Panel (2-of-3, $k=2$) | Extended Quorum (3-of-5, $k=3$) | Net Operational Impact |
|---|:---:|:---:|---|
| **Total Evaluated Cases** | 20 | 20 | Benchmark standard |
| **Consensus Decisions** | 17 (85.0%) | 17 (85.0%) | Identical automated throughput |
| **Correct Consensus** | 16 (80.0%) | **17 (85.0%)** | **+1 Ground Truth Decision** |
| **False Consensus (Critical Errors)** | **1 (5.0%)** | **0 (0.0%)** | **100% Elimination of Hallucinated Quorum** |
| **Abstention Count** | 3 (15.0%) | 3 (15.0%) | Stable fail-safe rate |
| **Precision on Consensus** | 94.1% (16/17) | **100.0% (17/17)** | **Zero Fault Tolerance Achieved** |
| **Unanimous Decisions** | 10 (50.0%) | 10 (50.0%) | Perfect alignment on simpler queries |

**Conclusion for Pair A**: The 3-of-5 quorum demonstrates decisive structural superiority over the 2-of-3 panel. While maintaining the exact same operational automation rate (85% consensus, 15% abstention), the 3-of-5 configuration **completely eliminates false consensus** (reducing critical financial errors from 5% to 0%) and achieves **100% precision** on all accepted decisions.

---
