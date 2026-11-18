# TD 2 Individual Moodle Quiz Preparation Guide (17:45 - 18:00)

**Target**: Individual 15-minute Moodle Quiz  
**Sub-group**: DIA 3 - Group 2  
**Key Goal**: Master cross-cutting concepts across Steps 1, 2, and 3.

---

### Question 1: Why must the quorum threshold $k$ be strictly greater than $n // 2$?
* **Mathematical Answer**: $\lfloor n / 2 \rfloor < k \le n$.
* **Rationale**: If $k \le n // 2$, two distinct, contradictory answers could both reach $k$ votes simultaneously within the same panel of $n$ members (e.g. for $n=4, k=2$, answer A could get 2 votes and answer B could get 2 votes). A strict majority ($k > n//2$) mathematically guarantees that **at most one candidate value can ever reach the threshold**, eliminating the risk of conflicting consensus.

---

### Question 2: Why does an unavailable model or HTTP 429 remain in $n$ but cast zero votes?
* **Concept**: Abstention Safety & Anti-Dilution Principle.
* **Rationale**: If an unavailable model were removed from $n$ (shrinking $n$ from 3 to 2, or 5 to 4), the required threshold $k$ would artificially drop. For example, if $n$ dropped to 2, a single remaining model with 2 votes (or even 1 vote) could dictate a decision. By preserving the denominator $n$, the system ensures that transient infrastructure failures (such as rate limits) raise the barrier to consensus, biasing the system towards **safe abstention** rather than reckless decision-making on incomplete evidence.

---

### Question 3: How does the SQL delta query on `boutique.sqlite` isolate the false consensus rows?
* **Case Reference**: Question C09 (Reference date: `2026-09-26`, Reference: `487,980` cents).
* **Models**: `cohere/north-mini-code` and `qwen/qwen3.8-27b` both returned `0` cents.
* **The SQL Mechanism**:
  - Exactly 25 years old on `2026-09-26` requires birth dates between `2000-09-27` and `2001-09-26` inclusive.
  - Cohere used a string subtraction formula that compared birth years to 25 without subtracting from 2026 $\rightarrow$ matched 0 rows.
  - Qwen used contradictory month-day comparisons on the order date $\rightarrow$ matched 0 rows.
  - Both queries evaluated `COALESCE(SUM(...), 0)` on an empty set, returning `0`.
* **The Delta Query**: Reconciles the missing records by querying customers born in the true window:
  ```sql
  SELECT c.customer_id, c.birth_date, COUNT(o.order_id) AS orders, SUM(o.quantity_product * p.price) AS revenue_cents
  FROM customers c
  JOIN orders o ON c.customer_id = o.customer_id
  JOIN product p ON o.product_id = p.product_id
  WHERE c.birth_date >= '2000-09-27' AND c.birth_date <= '2001-09-26'
  GROUP BY c.customer_id;
  ```
  Isolates exactly 6 customers (C001, C002, C003, C007, C008, C009) whose order revenue sums to **487,980 cents** ($487,980 - 0 = 487,980$).

---

### Question 4: Why is model accuracy so high on $F_1$ (Period) but low on $F_2$ (Customer Age)?
* **$F_1$ (Date Period)**: Translates to standard SQL timestamp range comparisons (`WHERE o.date >= '...' AND o.date < '...'`). Models encounter millions of identical examples in open-source pre-training corpora. Accuracy across our 5 models was near **100% (6/6)**.
* **$F_2$ (Customer Age at Reference Date)**: Requires completed calendar age arithmetic, accounting for whether the birthday has occurred yet in the reference year. Models frequently hallucinate invalid SQLite date functions (like `DATEDIFF`), confuse order date with reference date, or fail leap-year boundary edge cases. Only `openai/gpt-oss-120b` achieved 100% (4/4); lighter models scored 0% to 50%.

---

### Question 5: Why does `choose()` prioritize an included subscription over deferring for a free refill?
* **Supplied Priority**: Available Subscription (`cash == 0, allocation > 0`) $\rightarrow$ Defer for free refill (`cash == 0, allocation == 0`) $\rightarrow$ Paid Route (`cash > 0`).
* **Why this is optimal by default**:
  1. **Zero Marginal Cost**: Subscription capacity is prepaid; unused allocations expire and reset ("use it or lose it").
  2. **Execution Certainty**: Running immediately delivers a result now, whereas deferring is a speculative bet that quota will be available at wake-up (a deferred request can wake up to another HTTP 429).
  3. **Operational Simplicity**: Avoids queue scheduling complexity, timeouts, and state management.
* **When to Invert Priority (Defer instead of Spending Allocation)**:
  - When subscription allocation units are **scarce or metered** (internal corporate budget chargeback).
  - AND the request is **latency-tolerant** (`can_wait=True`, long deadline).
  - AND the free refill window is **short and deterministic** (e.g. Groq 10–12 second rolling window).
