## 3. Step 2: Wrong consensus (Pair B: Baptiste Noailhac, Jean Jaunet; support: Romain Thepaut)

**Source:** Real TD 1 traces (`td2/traces-td1.csv`, 104 rows, all `nature = real`), taking the last attempt per `(provider, model)` pair to form 100 cells. All results below come directly from our runs, except for the synthetic `DEMO-VOTE` illustration (explicitly labeled as such).  
**SQL evidence:** `td2/pair-b/step2-wrong-consensus.sql`, executed on `td2/data/boutique.sqlite`.

### 3.1 Searching the 100 cells for shared wrong values

| Question | Shared wrong value | Agreeing models | Reference | 2-of-3 panel (k=2) | 3-of-5 quorum (k=3) |
|---|---|---|---|---|---|
| **C09** | **0** | north-mini-code, qwen3.8-27b | 487980 | **Wrong consensus: 0 wins** (2 votes) | Abstains (487980: 2, 0: 2, dots `sql_rejected`) |
| C02 | 0 | gpt-oss-20b, north-mini-code | 590320 | 590320 wins (120b + qwen) | 590320 wins (120b + qwen + dots) |
| C10 | 119410 | qwen3.8-27b, dots-3-note-preview | 558980 | Abstains (558980 / 0 / 119410, 1 vote each) | Abstains (558980: 2, 119410: 2, 0: 1) |

The fixed 2-of-3 panel consists of `openai/gpt-oss-120b` (Groq), `cohere/north-mini-code:free` (OpenRouter), and `qwen/qwen3.8-27b` (Groq). While GPT-OSS 20B and Dots are part of the five TD 1 models, they are excluded from this panel.

**Primary case: C09.** Among our traces, C09 is the only question where a wrong value actually **wins the fixed 2-of-3 vote**, as two of the three panel members agree on `0`. Expanding to the 3-of-5 quorum brings in GPT-OSS 20B, which returns the right answer (`487980`), alongside Dots, whose query is rejected (`sql_rejected` due to a Markdown code fence). Since Dots remains counted in `n = 5` without casting a vote, the resulting 2–2 tie falls short of `k = 3`. The quorum safely **abstains** rather than publishing an erroneous figure.

### 3.2 Identification (C09)

- **Question:** Total revenue excluding VAT (in cents) generated across all orders by customers aged exactly 25 on `2026-09-26` (Family F2).
- **Agreeing models:** `cohere/north-mini-code:free` and `qwen/qwen3.8-27b` (`verdict = incorrect`, `value = 0`, HTTP 200, 1 attempt each).
- **Independent reference:** `487980` (`reference-td1.csv`), double-checked via a separate arithmetic age query (Query 5).
- **Other votes:** `gpt-oss-120b` = `487980` (correct), `gpt-oss-20b` = `487980` (correct), `dots` = `sql_rejected`.

### 3.3 Faulty SQL diagnosis

To be 25 years old on `2026-09-26`, a customer must be born between `2000-09-27` and `2001-09-26` (inclusive). Both failing models miss this window entirely, though for completely different reasons:

- **`north-mini-code`:** Computes "age" as `CAST(SUBSTR(birth_date,1,4) AS INTEGER) - CASE ... END`. Instead of subtracting the birth year from `2026`, it subtracts a small adjustment directly from the birth year itself (yielding values around 2000–2001). Checking `... = 25` therefore matches zero customers, and `COALESCE(SUM(...), 0)` defaults to `0`.
- **`qwen3.8-27b`:** Makes two distinct mistakes. First, it checks the customer's age at the order date (`o.date`) rather than on `2026-09-26`, misapplying F2b logic to an F2 question. Second, calling `strftime('%m-%d', date(birth_date, '+26 years'))` simply returns the customer's birth month and day, turning `md >= birth_md AND md < birth_md` into an impossible condition that filters out every row (`COUNT(*) = 0`).

**Key takeaway:** Two *unrelated* bugs converged on the *exact same* output. Because `COALESCE(SUM(...), 0)` maps any empty filter to `0`, zero acts as a statistical attractor. Unanimous agreement on `0` is therefore weak evidence—models can agree on the number without sharing any valid reasoning.

### 3.4 Delta diagnostic query (executed)

Because both faulty queries filter out the entire table, the gap between their output and the reference corresponds to the full target population:

| customer_id | birth_date | orders | revenue_cents |
|---|---|---|---|
| C007 | 2000-11-30 | 6 | 118740 |
| C009 | 2001-03-10 | 5 | 61330 |
| C008 | 2001-05-15 | 7 | 99090 |
| C002 | 2001-09-24 | 3 | 25920 |
| C001 | 2001-09-25 | 8 | 135000 |
| C003 | 2001-09-26 | 4 | 47900 |
| **Total** | | | **487980 = 487980 − 0** ✓ |

Customer `C003` (born `2001-09-26`, turning 25 on the reference date) sits right on the upper inclusive boundary—the exact row a strict `<` comparison would mistakenly drop.

**Independent verification:** Query 5 computes completed age arithmetically (`2026 − birth_year − (birth_md > '09-26')`) without relying on date windows, returning `487980`. All three methods—the reference file, the delta query total, and the arithmetic check—align to the cent.

### 3.5 Secondary case: C10 (non-zero wrong consensus)

On C10, `qwen3.8-27b` and `dots-3-note-preview` both return `119410` against a reference of `558980`. Both models only capture orders placed *after* the customer's birthday during the calendar year they turn 25 (`year(order) − year(birth) = 25`), overlooking orders placed **earlier in the calendar year of their 26th birthday**, when the customer is still 25. Qwen's fallback branch (`year diff = 24`) checks for 23-year-olds and matches zero rows. The delta consists of 28 order lines across four customers (`C004`, `C005`, `C007`, `C022`) totaling **439570 = 558980 − 119410** ✓. Fortunately, neither quorum validates this error: both abstain.

### 3.6 DEMO-VOTE (synthetic teaching example, not a model output)

Consider a single sale on `2026-01-01 00:00:00` for `100` cents over the window `[01-01, 01-02)`. With proposals `[0, 0, 100]`, a reference of `100`, and a threshold of `k = 2` of 3, the quorum **wrongly validates `0`**. Notably, we observed a SQLite string-comparison quirk during testing: `date > '2026-01-01'` still returns `100` because `'2026-01-01 00:00:00' > '2026-01-01'` evaluates to true lexicographically. The boundary bug only surfaces when the full timestamp (`date > '2026-01-01 00:00:00'`) is used.

### 3.7 Implications for verification

- **A 2-of-3 panel is unsafe for F2 questions:** As C09 demonstrates, two models can fail independently yet converge on the same wrong answer, causing the panel to publish an inaccurate figure.
- **Abstention is safe, not sufficient:** While the 3-of
