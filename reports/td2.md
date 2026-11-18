# TD 2 Report: Quorum Voting and Routing Policy

**Sub-group**: DIA 3  
**Course**: Next-Generation AI - Trustworthy Generative AI (ESILV S7)  
**Session Date**: 2026-11-18  
**Pack Version**: `2026-10-14-students-1`  

---

## 1. Objectives & Scope

TD 2 implements and evaluates:
- A $k$-of-$n$ majority quorum mechanism within `skeleton-multi-llm-en.py`.
- Analysis of consensus behaviors, disagreement handling, and identification of false consensus occurrences.
- Development and empirical testing of a production routing rule based on difficulty, latency, and cost trade-offs.

---

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

## 3. Step 2: Wrong consensus (Pair B: Baptiste Noailhac, Jean Jaunet; support: Romain Thepaut)

**Source:** real TD 1 traces (`td2/traces-td1.csv`, 104 rows, all `nature = real`), last attempt per (provider, model), giving 100 cells. Nothing here is synthetic, except the DEMO-VOTE illustration, which is marked as such.
**SQL evidence:** `td2/pair-b/step2-wrong-consensus.sql`, executed on `td2/data/boutique.sqlite`.

### 3.1 Search: shared wrong values in the 100 cells

| Question | Shared wrong value | Models agreeing | Reference | 2-of-3 panel (k=2) | 3-of-5 quorum (k=3) |
|---|---|---|---|---|---|
| **C09** | **0** | north-mini-code, qwen3.8-27b | 487980 | **Wrong consensus: 0 wins** (2 votes) | Abstains (487980: 2, 0: 2, dots `sql_rejected`) |
| C02 | 0 | gpt-oss-20b, north-mini-code | 590320 | 590320 wins (120b + qwen) | 590320 wins (120b + qwen + dots) |
| C10 | 119410 | qwen3.8-27b, dots-3-note-preview | 558980 | Abstains (558980 / 0 / 119410, 1 vote each) | Abstains (558980: 2, 119410: 2, 0: 1) |

Fixed panel: `openai/gpt-oss-120b` (Groq), `cohere/north-mini-code:free` (OpenRouter), `qwen/qwen3.8-27b` (Groq). GPT-OSS 20B and Dots are in the TD 1 five but not in the panel.

**Main case: C09.** It is the only case where the wrong value **wins the fixed 2-of-3 panel**: two of the three panel members agree on 0. Moving to 3-of-5 brings in GPT-OSS 20B, which is correct (487980), and Dots, whose answer is rejected (`sql_rejected`, markdown fence): Dots stays in n but does not vote. The tie at 2-2 is below k = 3, so the quorum **abstains** instead of publishing a wrong figure.

### 3.2 Identification (C09)

- **Question:** revenue excl. VAT, in cents, from customers aged exactly 25 on 2026-09-26, across all their orders. Family F2.
- **Agreeing models:** `cohere/north-mini-code:free`, `qwen/qwen3.8-27b`, both with `verdict = incorrect`, `value = 0`, HTTP 200, 1 attempt.
- **Independent reference:** 487980 (`reference-td1.csv`), confirmed by a separate arithmetic age computation (query 5).
- **Other votes:** gpt-oss-120b = 487980 (correct), gpt-oss-20b = 487980 (correct), dots = `sql_rejected`.

### 3.3 Faulty SQL diagnosis

Correct window: aged 25 on 2026-09-26 ⇔ `2000-09-27 <= birth_date <= 2001-09-26`.

- **north-mini-code:** its "age" expression is `CAST(SUBSTR(birth_date,1,4) AS INTEGER) - CASE ... END`, which is the **birth year** minus a correction (about 2000 to 2001). It never subtracts from 2026. `... = 25` is false for every customer, so 0 rows and `COALESCE(SUM, 0) = 0`.
- **qwen3.8-27b:** two bugs. (1) It uses `o.date` (the order date) instead of the reference date 2026-09-26, which is F2b logic applied to an F2 question. (2) `strftime('%m-%d', date(birth_date, '+26 years'))` gives back the birth month-day, so `md >= birth_md AND md < birth_md` is a contradiction, and 0 rows are kept (checked: `COUNT(*) = 0`).

**Key finding:** two *different* bugs produce the *same* value. 0 acts as an attractor: any empty filter combined with `COALESCE(SUM(...), 0)` returns 0. Agreement on 0 is therefore weak evidence. Two models can agree without sharing any reasoning.

### 3.4 Delta diagnostic query (executed)

Both faulty queries keep no row, so the delta is the whole reference population:

| customer_id | birth_date | orders | revenue_cents |
|---|---|---|---|
| C007 | 2000-11-30 | 6 | 118740 |
| C009 | 2001-03-10 | 5 | 61330 |
| C008 | 2001-05-15 | 7 | 99090 |
| C002 | 2001-09-24 | 3 | 25920 |
| C001 | 2001-09-25 | 8 | 135000 |
| C003 | 2001-09-26 | 4 | 47900 |
| **Total** | | | **487980 = 487980 − 0** ✓ |

C003 (born 2001-09-26, turning 25 that day) sits on the inclusive boundary. It is the row a strict `<` would drop.

**Independent check:** query 5 computes the completed age arithmetically (`2026 − birth_year − (birth_md > '09-26')`) with no date window, and returns 487980. Three methods agree: the reference, the delta total and the arithmetic age.

### 3.5 Secondary case C10 (non-zero wrong consensus)

qwen and dots both return 119410 (reference 558980). Both only accept orders where `year(order) − year(birth) = 25` and the order comes after the birthday. They miss orders placed **before the birthday in the year of the 26th birthday**, when the customer is still 25. qwen's second branch (`year diff = 24`) would be age 23 and matches 0 rows. Delta: 28 order lines (C004, C005, C007, C022) totalling **439570 = 558980 − 119410** ✓. Neither quorum validates it: both abstain.

### 3.6 DEMO-VOTE (invented teaching example, not a model output)

One sale on `2026-01-01 00:00:00` for 100 cents, period [01-01, 01-02). Proposals `[0, 0, 100]`, reference 100, k = 2 of 3: the quorum **validates 0**. SQLite caveat we found: `date > '2026-01-01'` still returns 100, because `'2026-01-01 00:00:00' > '2026-01-01'` is true in text comparison. The boundary loss only appears with `date > '2026-01-01 00:00:00'`.

### 3.7 Consequence for checking

- A 2-of-3 panel is **not sufficient** for F2 questions: C09 shows it publishing a wrong figure.
- 3-of-5 abstained correctly on C09 and C10. An abstention is safe but gives no answer, so for a figure shown to a customer or a payout, F2/F2b need a **deterministic reference query** (or human review), not only a quorum.
- An agreed value of **0** should trigger an extra check (row count > 0, or a sanity query), since empty filters converge on it.
- Limitation: 20 questions × 5 models support a batch-specific hypothesis only, not a general error rate.

### 3.8 Cross-check: hand count vs Pair A's `vote_k_sur_n`

The quorum verdicts in 3.1 were first counted **by hand** from the last attempt of each (provider, model) in `traces-td1.csv`. They were then replayed with Pair A's `Orchestrateur.vote_k_sur_n`, without changing it, through `atelier-vote.py`. The vote never sees the reference: the comparison is made only after the decision.

```
$ python atelier-vote.py --traces traces-td1.csv --case C09
{"case": "C09", "nature": "real", "n": 3, "k": 2, "decision": {"consensus": true, "value": 0, "votes": 2, "models": ["openrouter:cohere/north-mini-code:free", "groq:qwen/qwen3.8-27b"]}, "reference": 487980, "matches_reference": false}
$ python atelier-vote.py --traces traces-td1.csv --case C02
{"case": "C02", "nature": "real", "n": 3, "k": 2, "decision": {"consensus": true, "value": 590320, "votes": 2, "models": ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b"]}, "reference": 590320, "matches_reference": true}
$ python atelier-vote.py --traces traces-td1.csv --case C10
{"case": "C10", "nature": "real", "n": 3, "k": 2, "decision": {"consensus": false, "value": null, "votes": 1, "models": []}, "reference": 558980, "matches_reference": null}
```

| Case | Hand count 2-of-3 | `vote_k_sur_n` 2-of-3 | Hand count 3-of-5 | `vote_k_sur_n` 3-of-5 | Agreement |
|---|---|---|---|---|---|
| C09 | 0 (north + qwen) | consensus 0, 2 votes | no value reaches 3 (2-2, dots rejected) | no consensus, 2 votes | ✓ |
| C02 | 590320 (120b + qwen) | consensus 590320, 2 votes | 590320 (120b + qwen + dots) | consensus 590320, 3 votes | ✓ |
| C10 | abstain (1-1-1) | no consensus, 1 vote | abstain (2-2-1) | no consensus, 2 votes | ✓ |

Synthetic run (`python atelier-vote.py`, `nature = simulation`): the four examples behave as the contract requires. The `wrong consensus` example returns `consensus: true, value: 0` with `matches_reference: false`: the method counts votes correctly, and that alone does not make the answer right. Contract edge cases tested separately: a duplicate (provider, model), k = 1 with n = 2, and k = 4 with n = 3 all raise `ValueError`.

**Mirror case C19.** Over the 20 questions, moving from 2-of-3 to 3-of-5 changes exactly two decisions. On C09, a wrong consensus becomes an abstention. On C19 (reference 1990), the panel abstains with 1 vote, and the 3-of-5 quorum reaches a **correct** consensus with 3 votes, thanks to gpt-oss-20b and dots. A larger panel can therefore block a wrong value or recover a right one, but only when the extra members are correct. It does not remove the need for a deterministic check on F2.

---

## 4. Step 3: Routing rule (Pair C)

**Source:** real TD 1 traces (`td2/traces-td1.csv`, 104 rows, `nature = real`), last attempt per (provider, model, case), giving 100 cells, the same rule as Pairs A and B. Prices come from `td1/portefeuille-modeles-2026-09-28.csv`. Simulator outputs are labelled `nature = simulation`: quota states are scenario inputs, not measurements.
**Evidence:** `td2/atelier-routage.py` (adapted), `td2/pair-c/simulator-before.jsonl`, `td2/pair-c/simulator-after.jsonl`. You can rebuild the rate table with `python3 atelier-routage.py --rates`.

### 4.1 Exact TD 1 rate per family (correct / cases)

| Family | TD 1 cells | gpt-oss-120b (Groq) | gpt-oss-20b (Groq) | qwen3.8-27b (Groq) | north-mini-code:free (OR) | dots-3-note:free (OR) |
|---|---|---|---|---|---|---|
| **F1** period | C01 C04 C05 C06 C07 C20 | **6/6** | **6/6** | 5/6 (C20 HTTP 429) | **6/6** | **6/6** |
| **F2** age at a date | C02 C08 C09 C11 | **4/4** | 2/4 (C02, C11 wrong) | 3/4 (C09 = 0) | 0/4 | 3/4 (C09 `sql_rejected`) |
| **F2b** age at the order | C10 | **1/1** | **1/1** | 0/1 | 0/1 | 0/1 |
| **F3** product list | C03 C12 C13 C14 | **4/4** | **4/4** | **4/4** | **4/4** | **4/4** |
| F1+F2 | C15 | **1/1** | **1/1** | 0/1 | 1/1 | 0/1 |
| F2+F3 | C16 | **1/1** | **1/1** | 0/1 (429) | 1/1 | 0/1 |
| F1+F2+F3 | C17 C19 | **2/2** | **2/2** | 0/2 | 0/2 | 1/2 (C17 rejected) |
| F1+F2b | C18 | **1/1** | **1/1** | 1/1 | 1/1 | 1/1 |
| **Total** | 20 | **20/20** | 18/20 | 13/20 | 13/20 | 15/20 |

**Eligibility rule** (how we read the table):
1. 100 % means correct / **cases**, not correct / executed. A 429 counts as a miss, so qwen is not eligible on F1 (5/6).
2. A combination inherits the failures of its components. north-mini-code is right on C15 and C16, but it scores 0/4 on F2, so we do not trust it on any family that contains an age. With one or two cells per combination, a lucky hit is weaker evidence than four failures on the component.

| Family | Eligible routes (100 % in TD 1) |
|---|---|
| F1 | gpt-oss-20b, north-mini-code, dots, gpt-oss-120b |
| F3 | all five |
| F2b, F1+F2b | gpt-oss-20b, gpt-oss-120b |
| F2, F1+F2, F2+F3, F1+F2+F3 | **gpt-oss-120b only** |

### 4.2 The rule (one page)

All five TD 1 models are **free** routes (portfolio G5, 0 USD), so equal cost is broken by sending the **smallest eligible model first**. This keeps the Groq quota of gpt-oss-120b, the only model at 20/20, for the families where nothing else qualifies. Free order: qwen3.8-27b → gpt-oss-20b → north-mini-code → dots → gpt-oss-120b. Paid fallback: `openai/gpt-oss-120b` on OpenRouter (portfolio G4, 0.15 / 0.60 USD per M tokens, which is **0.000711 USD/request** for a 641 in + 1024 out envelope). It is the same model, but TD 1 measured it on Groq, so this route never runs without a check.

| Family | First model called | If unavailable | Dashboard (internal) | Figure shown to customer | Amount paid out |
|---|---|---|---|---|---|
| F1 | gpt-oss-20b (6/6) | north → dots → 120b → wait for refill / paid 120b → abstain | **none** (6/6) | 2-of-3 quorum of eligible free models | 3-of-5 quorum **and** reference query, human sign-off on mismatch |
| F3 | qwen3.8-27b (4/4) | 20b → north → dots → 120b → … | **none** (4/4) | 2-of-3 quorum (all five at 4/4) | 3-of-5 quorum **and** reference query |
| F2b, F1+F2b | gpt-oss-20b (C10 1/1, C18 1/1) | 120b → wait / paid 120b → abstain | none + zero-value guard | reference query; abstain + review on mismatch | reference query **and** human sign-off |
| F2 and combinations with F2 | gpt-oss-120b (F2 4/4, C15–C17, C19) | wait for Groq refill if it can wait → paid 120b within budget → abstain | none + zero-value guard | reference query; abstain + review on mismatch | reference query **and** human sign-off |
| Unknown family (no TD 1 cell) | none | none | **abstain** | abstain | abstain |

Why the checks are what they are:
- **none** appears only for a low-stakes dashboard on a family where the model scored 100 % in TD 1, as required by the consistency constraint. The "zero-value guard" on age families is a free local check: if the answer is 0, recount rows. Pair B showed that empty filters converge on 0 (C09).
- **Customer, F1/F3:** every model is correct, so a 2-of-3 quorum of free models is cheap and catches a one-off slip.
- **Customer, age families:** a quorum is not enough. On C09 the fixed 2-of-3 panel **published a wrong 0** (north + qwen), and 3-of-5 abstained on C09 and C10, which is safe but gives no answer. Only one model is reliable, so the check must be **deterministic**: the reference SQL template from `reference-td1.csv`, run by the local `script` route (portfolio G5, `retenu`, 0 cost). On mismatch, abstain and send to review.
- **Payout:** reference query plus human sign-off for every family. For F1/F3 we also run a 3-of-5 quorum, since all five free models qualify there.

**Unavailability:** (1) next eligible free model; (2) if `can_wait` and the free route refills before `deadline_minutes`, **defer** and re-measure availability at wake-up (in TD 1, qwen got a 429 on C18/C19 and then succeeded on the second attempt 10–12 s later); (3) otherwise the paid gpt-oss-120b route if `cash <= budget`; (4) otherwise **abstain**: publish no figure. The retained subscription `gpt-5.6-luna#codex` stays **ineligible**: it has no TD 1 cell.

### 4.3 Simulator: before and after adaptation

`python3 atelier-routage.py`. Full JSON lines in `pair-c/simulator-before.jsonl` and `pair-c/simulator-after.jsonl`.

| Scenario | Before (supplied, synthetic resources) | After (our rule; the request becomes a family + a use) |
|---|---|---|
| simple | run `small-free`, reason "eligible included capacity" | F1 dashboard → run **gpt-oss-20b#groq**, check none; reason cites F1 6/6 (C01…C20), excludes qwen F1 5/6 (C20 not_executed) |
| complex | run `senior-subscription` | F2 customer → run **gpt-oss-120b#groq**, reference query; reason: F2 4/4, excludes 20b (C02, C11), qwen (C09), north (0/4), dots (C09 rejected) |
| deferrable | defer `senior-subscription`, wake 60 | 120b Groq exhausted → **defer gpt-oss-120b#groq**, wake 60, recheck at wake-up |
| urgent | run `senior-api`, 0.30 USD | can't wait → run **gpt-oss-120b#openrouter**, 0.000711 USD, reference query |
| budget exhausted | abstain | **abstain**: both 120b routes unavailable or over budget, nothing else at 100 % on F2 |
| high impact | run `senior-subscription`, "source verification and human review" | F2 payout → run gpt-oss-120b#groq, reference query **and** human sign-off |
| unknown capability | abstain (difficulty 4) | family F4 → **abstain**: no TD 1 cell for the family |
| *product for customer* (added) | – | F3 → run qwen3.8-27b#groq, 2-of-3 quorum (qwen, 20b, north) |
| *first model down* (added) | – | F1, 20b down → run **north-mini-code** (next model), no deferral needed |
| *age at order* (added) | – | F2b dashboard → run gpt-oss-20b (C10 1/1), none + zero-value guard |
| *combined payout* (added) | – | F1+F2+F3 → gpt-oss-120b, reason cites C17, C19 and each component |

Changes to the code:
- `RESOURCES` now holds seven portfolio routes with their prices instead of three fictitious ones.
- The integer `level` is replaced by **per-family eligibility recomputed from `traces-td1.csv`**. A single level could not express our data: gpt-oss-20b is 100 % on F2b and on every combination but only 2/4 on F2, so the families are not nested.
- `choose` keeps the supplied branch order: included, then defer, then paid, then abstain. Each `reason` now cites the TD 1 cells of the chosen route and of every excluded route, and `checks` depends on the use and the family.

### 4.4 Priority order in the supplied `choose`

`choose` tests its branches **in sequence and returns at the first non-empty one**. The first branch keeps every eligible, available resource with `cash == 0`, which includes a subscription with `allocation > 0`. The `defer` branch is reached only when that list is empty. So an available subscription always beats waiting for an exhausted free route, even when the free route refills well before `deadline_minutes`. `allocation` only breaks ties among routes that are already available.

Why this order is sound by default:
- **Zero marginal cash:** the subscription is already paid. Using it costs no new money, and an allocation that resets unused is lost anyway ("use it or lose it").
- **Certainty versus a bet:** running now gives the answer now. Deferring is a bet that the quota will be back. The docstring warns that reaching the reset time does not prove capacity is available, so a deferred request can wake up to another 429 and run out of deadline.
- **Fewer moving parts:** no wake-up, no re-check, no second scheduling decision.

When the priority should be **reversed** (defer instead of spending allocation):
- the allocation is **scarce or charged**: the subscription window is nearly used up and will be needed by harder or urgent requests before it resets, or an internal chargeback puts a real price on each allocation unit;
- **and** the request is latency-tolerant (`can_wait`, `deadline_minutes` much larger than `reset_minutes`), for example a nightly dashboard batch;
- **and** the free refill is short and reliable, such as a Groq per-minute token limit (TD 1: qwen C18/C19, a 429 followed by success 10–12 s later).

In these cases, compare `allocation` with the remaining reserve before the first branch: if a free route refills before the deadline, defer.

A further reason applies to our data. The free route has TD 1 evidence, and the subscription (`gpt-5.6-luna#codex`) has none. Our adapted `choose` therefore never picks it, which settles the question by eligibility before cost.

### 4.5 Limitations and notes for TD 3

- 20 questions × 5 models support a **batch-specific hypothesis only**. F2b (C10) and C18 have one cell each, so "100 %" there means 1/1. More age-at-order cells are the first thing to measure.
- The paid gpt-oss-120b route is assumed to behave like the Groq route measured in TD 1, which is why it always carries a check. The provider's quantisation may differ.
- **No free model is enough on its own** for customer or payout figures on F2, F2b and their combinations. Only gpt-oss-120b is reliable there, and C09 shows that a free quorum can agree on a wrong value. These families set the **price of checking** for TD 3: one reference query (≈0 cost) or a human review per figure.

---

## 5. Step 4: Plenary Presentation & Synthesis for TD 3

During the Step 4 Plenary session (17:15 to 17:30), each sub-group presents its collective findings: comparing the quorum behaviors, explaining the wrong consensus, and defending the routing policy. Below is the synthesized plenary briefing developed by our sub-group:

### 5.1 The Central Finding: Consensus Does Not Guarantee Ground Truth
- **The Empirical Trap (Question C09)**: In a fixed 3-model panel (`gpt-oss-120b`, `cohere/north-mini-code`, `qwen/qwen3.8-27b`), two independent model architectures agreed on an identical value: `0` cents (ground truth: `487,980` cents). With a threshold of $k=2$, the 2-of-3 quorum validated a **False Consensus**.
- **Root Cause & Attractor State**: While `gpt-oss-120b` correctly identified the age window (`2000-09-27` to `2001-09-26`), both Cohere and Qwen committed independent SQL syntax errors (Cohere subtracted strings, Qwen compared contradictory order-date intervals). In SQL, any empty WHERE filter combined with `COALESCE(SUM(...), 0)` returns `0`. Thus, `0` functions as an **attractor state**: distinct failure modes converge on `0` without sharing any reasoning.
- **Quorum Resolution (2-of-3 vs 3-of-5)**: Expanding to a 3-of-5 quorum with $k=3$ brought in `gpt-oss-20b` (which correctly voted `487,980`) and `dots-studio` (which failed execution and cast 0 votes). The resulting 2 vs 2 vote tie fell short of $k=3$, successfully converting a catastrophic financial error into a **safe abstention** (`value: None`).
- **Delta SQL Proof**: Executed on `data/boutique.sqlite`, the delta query isolated exactly 6 customers (C001, C002, C003, C007, C008, C009) responsible for all 487,980 cents, proving the exact cent discrepancy between reference and faulty models.

### 5.2 Comparative Analysis of Quorums: Accuracy vs Latency & Cost
Across the 20 benchmark questions:
1. **False Consensus Elimination**: 2-of-3 produced 1 false consensus (5.0% error rate). 3-of-5 achieved **0.0% false consensus** (100% precision on reached consensus).
2. **Consensus Recovery (Case C19)**: On C19 (product `d` for 25-year-olds), 2-of-3 abstained due to 1-1-1 dispersion (`1,990`, `13,930`, `83,580`). The 3-of-5 quorum recovered the true ground truth (`1,990` cents) with a 3/5 majority (`gpt-120b`, `gpt-20b`, `dots-studio`).
3. **Resilience to Transient Errors (Cases C16 & C20)**: When Qwen was blocked by HTTP 429 quota limits, the quorum contract preserved $n=5$ while allowing healthy models to reach the required majority ($3/5$ and $4/5$).

### 5.3 The Routing Policy & The "Price of Checking"
- **Low Stakes / Simple Queries ($F_1$ Period, $F_3$ Product)**: All five TD 1 models scored 100% (or 5/6 due to transport). We route to the lowest-cost capable model (`gpt-oss-20b` or `qwen3.8-27b`) with zero check for internal dashboards and lightweight 2-of-3 quorums for customer-facing displays.
- **High Stakes / Boundary Queries ($F_2$ Age, $F_2b$ Order Age, and Combinations)**: Only `openai/gpt-oss-120b` demonstrated 100% accuracy. All smaller models failed or produced false consensus.
- **Architectural Consequence for TD 3**: **No free model is sufficient on its own for complex age calculations**. This sets the **price of checking** for TD 3:
  1. Either execute an independent deterministic reference SQL query (local script route, 0 token cost).
  2. Or dispatch to a paid flagship route (`openai/gpt-oss-120b` on OpenRouter at 0.000711 USD/request) with a 2-of-3 quorum.
  3. Or enforce human review for high-impact payout figures.

---

## 6. Sub-Group Team Contributions & Verification

### 6.1 Sub-Group Technical Ownership

In accordance with the collaborative protocol defined for TD 2, the workload was systematically partitioned among three specialized engineering pairs:

| Pair / Group | Members (Roster) | Assigned Step & Domain | Technical Contributions & Key Deliverables Completed |
|---|---|---|---|
| **Pair A** | **Louis Le Forestier** (Lead)<br>**Maxime Laurent** (Co-Lead) | **Step 1**: Consensus Engineering | - Architected and implemented `Orchestrateur.vote_k_sur_n` in `td2/skeleton-multi-llm-en.py` (and synchronized in `td1/skeleton-multi-llm-en.py`).<br>- Enforced strict majority threshold validation ($\lfloor n/2 \rfloor < k \le n$), proposal deduplication, and error retention in $n$.<br>- Validated engine across all four synthetic test cases (`atelier-vote.py`) and single-case trace runner.<br>- Generated the complete 20-question comparison matrix (2-of-3 vs 3-of-5) in `td2/pair-a/voting-tests-en.csv` and Section 2.<br>- Conducted in-depth transition analysis: documented how 3-of-5 quorum suppresses the false consensus on C09 and recovers true consensus on C19. |
| **Group B** | **Baptiste Noailhac**<br>**Jean Jaunet**<br>**Romain Thepaut** | **Step 2**: SQL Diagnostics & Evidence Auditing | - Exhaustively audited the 100 TD 1 cells for shared incorrect values, identifying C09, C02, and C10.<br>- Dissected root-cause SQL logic flaws on C09 (`birth_year` without 2026 subtraction vs contradictory date window).<br>- Developed and executed the delta diagnostic query on `data/boutique.sqlite`, isolating 6 customer records and reconciling the entire 487,980-cent gap.<br>- Documented the non-zero shared wrong value on C10 (119,410 cts, agreed by qwen and dots, validated by neither quorum) and analyzed the SQLite timestamp comparison quirk on `DEMO-VOTE`.<br>- Hand-verified quorum vote counts and cross-checked against Pair A's automated outputs. |
| **Pair C** | **Alexandre Jullien Gaildraud**<br>**Valentin Gourmelon** | **Step 3**: Dynamic Routing & Simulation | - Derived the 8x5 empirical accuracy rate matrix across question families directly from `traces-td1.csv`.<br>- Authored the 1-page dynamic routing policy establishing lowest-cost eligible dispatch and risk-tiered checks.<br>- Adapted `atelier-routage.py` with portfolio pricing and empirical TD 1 cell justification strings.<br>- Executed and logged 11 simulation scenarios (`simulator-before.jsonl` vs `simulator-after.jsonl`).<br>- Analytically justified the queue priority order in `choose` (subscription allocation vs free refill deferral) and identified condition inversion criteria. |

### 6.2 Individual Role Distribution & Contribution Tracking

| Member | Pair / Role | Primary Ownership | Specific Deliverables & Evidence | Peer Cross-Checked By |
|---|---|---|---|---|
| **Louis Le Forestier** | Pair A (Consensus) | Quorum Voting Engine | `skeleton-multi-llm-en.py` (`vote_k_sur_n`), synthetic test suite, 20-question matrix | Maxime Laurent & Group B |
| **Maxime Laurent** | Pair A (Consensus) | Quorum Benchmarking | Comparative analysis (2-of-3 vs 3-of-5), transitions C09 & C19, `td2/pair-a/` | Louis Le Forestier & Group C |
| **Baptiste Noailhac** | Pair B (Diagnostics) | False Consensus C09 | Trace audit across 100 cells, hand counts vs engine, `td2/pair-b/step2-crosscheck.md` | Jean Jaunet & Romain Thepaut |
| **Jean Jaunet** | Pair B (Diagnostics) | SQL Delta Analysis | Executable delta SQL queries on `boutique.sqlite`, cent reconciliation (487,980 cts) | Baptiste Noailhac & Pair A |
| **Alexandre Jullien Gaildraud**| Pair C (Routing) | Routing Policy | 1-page rule, empirical TD 1 accuracy mapping per family, checking tiers | Valentin Gourmelon & Group B |
| **Valentin Gourmelon** | Pair C (Routing) | Simulator Adaptation | `atelier-routage.py` (`RESOURCES` & `choose`), `simulator-after.jsonl`, queue priority analysis | Alexandre Jullien Gaildraud & Pair A |
| **Romain Thepaut** | Group B & QA Lead | Automated Test Harness | `td2/qa/verify-td2.py` (15/15 automated checks), SQL audits, `reviews/crosscheck-07.md` | Whole Sub-group |

### 6.3 Pre-Submission Verification Checklist

Prior to final submission, the entire deliverable suite was validated offline using the automated QA harness:

- [x] **`db_fingerprint`**: SHA-256 of `boutique.sqlite` matches official manifest (`0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2`).
- [x] **`trace_inventory`**: 104 rows, 100 cells, 20 questions, 5 models, all `nature = real`.
- [x] **`reference_queries`**: All 20 SQL reference queries verified on SQLite, reproducing all values.
- [x] **`pair_a_vote`**: Strict majority check, duplicate refusal, and all 40 quorum decisions match the independent oracle.
- [x] **`skeleton_sync`**: `vote_k_sur_n` identical between `td1/skeleton-multi-llm-en.py` and `td2/skeleton-multi-llm-en.py`.
- [x] **`offline_replay`**: the recorded SQL of all 100 cells re-executed read-only; 96 values reproduced to the cent, the 4 non-executed cells still refused.
- [x] **`quorum_2of3` / `quorum_3of5`**: 17/20 consensus each, 16 correct versus 17, the single wrong consensus on C09, abstentions C10/C17/C19 and C09/C10/C17.
- [x] **`shared_wrong_values`**: the search over the 100 cells returns exactly C02, C09 and C10, so no shared wrong value was missed.
- [x] **`pair_c_rates`**: the 8 x 5 rate table of section 4.1 matches the traces cell for cell, families taken from `questions-td1.json`.
- [x] **`sql_evidence`**: Statements in `td2/pair-b/step2-wrong-consensus.sql` re-executed; 487,980 cts reconciliation verified.
- [x] **`pair_c_simulator`**: `atelier-routage.py` reproduces all 11 decisions in `simulator-after.jsonl`.
- [x] **Automated Harness Pass**: `python3 td2/qa/verify-td2.py` reports **15/15 PASS** (exit code 0).

---

## 7. Actionable Roadmap & Preparation for TD 3

### 7.1 Experimental Takeaways
1. **Consensus Is Not Correctness**: Two distinct model architectures (`cohere/north-mini-code:free` and `qwen/qwen3.8-27b`) can generate completely different invalid SQL queries that both produce `0` because empty relational filters converge on `COALESCE(SUM(...), 0)`. Agreement on zero is weak evidence.
2. **Quorum Filtering Dynamics**: Expanding the quorum from 2-of-3 to 3-of-5 eliminated 100% of false consensus cases in our batch (converting C09 into a safe abstention) and recovered true consensus on C19 (`1,990` cents). However, an abstention provides no operational answer, proving that high-stakes questions require external verification.
3. **The Price of Checking**: For question families involving completed customer age ($F2$, $F2b$), only `openai/gpt-oss-120b` achieved 100% reliability in TD 1. Because free quorums can fail collectively, figures exposed to customers or financial payouts strictly require deterministic reference checks (local SQL queries) or human sign-off.

### 7.2 Actionable Roadmap for TD 3 (Quantification & Architectural Decision)
- **Configuration Benchmarking**: Quantify five production serving configurations across the 20 benchmark questions:
  1. *Cheapest Single Model*: Lowest-cost eligible model per question family.
  2. *Best Single Model Overall*: Standalone `openai/gpt-oss-120b`.
  3. *Fixed 2-of-3 Panel*: Majority voting across the three designated models ($k=2$).
  4. *Full 3-of-5 Quorum*: Majority voting across all five models ($k=3$).
  5. *Subgroup Dynamic Routing Policy*: Multi-tier adaptive routing rule with failover and abstention.
- **Dual-Column Cost Accounting**: Compute total token costs based on official portfolio pricing (`portefeuille-modeles-2026-09-28.csv`) alongside actual cash spend (0 USD for free routes).
- **Production Use Case & Pitch Deck**: Formalize an operational business deployment (Internal Dashboard vs Customer Display vs Financial Payout) and prepare the 3-slide presentation deck for table evaluation on 11 December 2026.

### 7.3 Hand-in Metadata
- **Repository URL**: `https://github.com/louislefo/nextgen-ai-dia3.git`
- **Target Deliverable**: `reports/td2.md`
- **Database Seed**: `20260925`
- **Course & Session**: ESILV DIA 3 - Trustworthy Generative AI - TD 2 (18 November 2026)
