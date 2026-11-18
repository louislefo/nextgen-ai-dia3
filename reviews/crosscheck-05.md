# Peer Cross-Check Log 05: TD 2 Quorum Voting Engine & Benchmark

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 2 - Majority Voting Consensus ($k$-of-$n$)  
**Target Repository**: `nextgen-ai-dia3`  
**Target Module**: `td2/skeleton-multi-llm-en.py` (`Orchestrateur.vote_k_sur_n`) & `td2/atelier-vote.py`  

> **Corrected on 2026-11-18 by Romain Thepaut (QA)** after the automated pass recorded in
> [crosscheck-07.md](crosscheck-07.md). This log was first written before the engine was
> implemented, and its Review 2 figures did not match `traces-td1.csv`. Both reviews below
> are now the audit as actually performed, against commit `ebc6135` (merge of PR #16), and
> every figure is reproducible with `python3 td2/qa/verify-td2.py --matrix`. The original
> review scopes and auditor assignments are unchanged.

---

## Review 1: Voting Consensus Engine Implementation (`vote_k_sur_n`)

### Metadata
- **Authors / Reviewees**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Auditors / Reviewers**: Group B (Baptiste Noailhac, Jean Jaunet, Romain Thepaut)
- **Target File**: `td2/skeleton-multi-llm-en.py` (Method `Orchestrateur.vote_k_sur_n`)
- **Review Date**: 2026-11-18, on the delivered engine (PR #16). The audit of the kit stub,
  which raised `NotImplementedError`, is recorded as finding F1 of crosscheck-07.

### Scope of Inspection
Audit compliance of `vote_k_sur_n` against the five specifications of its own docstring:
1. **Majority threshold**: $k$ must be a strict majority ($len(proposals) // 2 < k \le len(proposals)$); raise `ValueError` otherwise.
2. **Duplicate detection**: Multiple proposals with identical `(provider, model_requested)` must raise `ValueError`.
3. **Error retention**: Proposals with errors or unexecuted status remain in the total proposal count $n$ without casting a vote.
4. **Standardized return dictionary**:
   - Consensus: `{"consensus": True, "value": v, "votes": count, "models": [...]}`
   - Abstention: `{"consensus": False, "value": None, "votes": max_votes, "models": []}`
5. **No fabrication**: Never invent a value when quorum is not reached.

### Audit Procedure & Execution
Three independent levels, all offline:

```bash
python3 td2/atelier-vote.py                                      # 4 synthetic examples
cd td2 && python3 atelier-vote.py --traces traces-td1.csv --case C09   # real traces, one case
python3 td2/qa/verify-td2.py                                     # check pair_a_vote
```

`pair_a_vote` compares the delivered method against an oracle written separately from the
same contract, over the 40 decisions (20 questions x 2 quorums), and exercises the three
contract failure modes.

### Verification Findings
1. The four synthetic examples of `atelier-vote.py` behave as specified:
   - *agreement* `[100, 100, 120]` -> consensus on 100, 2 votes.
   - *disagreement* `[100, 110, 120]` -> abstention, `value: null`, `votes: 1`.
   - *unavailable* `[100, None, None]` -> $n$ stays 3, the lone vote is insufficient, abstention.
   - *wrong consensus* `[0, 0, 100]` -> consensus on 0 against a reference of 100. The vote
     is right to return it: a quorum filters independent errors, not correlated ones.
2. On the real traces, C09 returns
   `{"consensus": true, "value": 0, "votes": 2, "models": ["openrouter:cohere/north-mini-code:free", "groq:qwen/qwen3.8-27b"]}`
   against a reference of 487980. The engine reproduces the session's central result unaided.
3. `ValueError` is raised for $k$ = 0, 1 and 4 with $n$ = 3, and for a duplicate
   `(provider, model_requested)` pair. Verified by the harness, not by inspection.
4. All 40 decisions agree with the independent oracle, and every return carries the four
   required keys.
5. Standard library only, no third-party dependency.
6. **Observation**: `vote_k_sur_n` is duplicated in `td1/skeleton-multi-llm-en.py` and
   `td2/skeleton-multi-llm-en.py`. The two copies are identical today, but `atelier-vote.py`
   loads only the `td2` one. The `skeleton_sync` check now fails the pass if they diverge.

### Verdict
**APPROVED** - full adherence to the TD 2 quorum voting contract, verified by execution.

---

## Review 2: 20-Question Quorum Comparison Matrix (2-of-3 vs 3-of-5)

### Metadata
- **Authors / Reviewees**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Auditors / Reviewers**: Pair C (Alexandre Jullien Gaildraud, Valentin Gourmelon)
- **Target Evaluation**: 20-question comparison across C01-C20 on the TD 1 trace dataset
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit the 20-question comparative benchmark contrasting:
- **Fixed 2-of-3 Panel**: `openai/gpt-oss-120b` (Groq), `cohere/north-mini-code:free` (OpenRouter), `qwen/qwen3.8-27b` (Groq), $k=2$.
- **3-of-5 Full Quorum**: all five models of `traces-td1.csv`, $k=3$.
- Verify alignment with the ground truth of `reference-td1.csv`, which is compared only
  after each decision.
- Ensure every decision transition is explained by a root cause in the traces.

### Audit Procedure & Execution
The matrix is recomputed from the traces by an independent oracle and compared to Pair A's
table cell by cell:

```bash
python3 td2/qa/verify-td2.py --matrix
```

Checks `quorum_2of3` and `quorum_3of5` assert the consensus count, the wrong consensus and
the abstention set for each quorum.

### Verification Findings
1. **The 2-of-3 panel reaches consensus on 17 of 20 questions, of which 16 match the
   reference and 1 does not.** Consensus is not a proof of correctness on this batch:
   precision on accepted decisions is 16/17, not 17/17.
2. **C09 is the wrong consensus.** `north-mini-code` and `qwen` both return `0` against a
   reference of 487980, which is 2 votes out of 3, so the panel publishes a wrong figure.
   Two unrelated SQL bugs produce the same value, both through an empty filter wrapped in
   `COALESCE(SUM(...), 0)`. Diagnosis and delta SQL in `td2/pair-b/`.
3. **The three abstentions of the 2-of-3 panel are C10, C17 and C19**, each a 1-1-1 split.
   C04 and C05 are unanimous 5/5 and correct; C11 reaches a correct consensus at 446690
   with 2 votes.
4. **Moving to 3-of-5 changes exactly two cells of twenty**, and both changes are safe:
   - **C09**: `gpt-oss-20b` adds a correct vote and Dots is `sql_rejected`, so the tally is
     2-2 below $k=3$. The wrong consensus becomes an abstention. Safety here comes from
     abstaining, not from a better answer.
   - **C19**: the panel abstained on a 1-1-1 split (1990 / 83580 / 13930); `gpt-oss-20b` and
     Dots both vote 1990, reaching 3 votes. Dispersion becomes a correct decision.
5. Both quorums therefore reach 17/20 consensus. The 3-of-5 quorum has 17 correct out of
   17, and the 2-of-3 panel 16 out of 17. Identical automation rate, one error removed.
6. On C16 and C20, qwen is `not_executed` (HTTP 429). It stays in $n$ and casts no vote,
   and both quorums still reach the correct value, which is the error-retention rule
   working as specified.
7. Every transition above is traceable to a `(case_id, provider, model_requested)` row of
   `traces-td1.csv`, and Pair A's table matches the recomputation on all 20 cases.

### Verdict
**APPROVED** - the 20-question matrix is exact. The empirical result to carry to the
plenary is that a 2-of-3 panel published one wrong figure out of twenty, and that widening
to 3-of-5 suppressed it on this batch, with these five models. A third model sharing the
`0` on C09 would have carried the wrong value to $k=3$.
