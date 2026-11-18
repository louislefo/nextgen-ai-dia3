# Peer Cross-Check Log 07: TD 2 Automated Verification Pass

**Sub-group**: DIA 3 - Group 2
**Session**: TD 2 - Quorum Voting, False Consensus & Routing
**Auditor**: Romain Thepaut (QA, Audit & Verification)
**Review Date**: 2026-11-18
**Target Scope**: `td2/skeleton-multi-llm-en.py`, `td2/atelier-vote.py`, `td2/atelier-routage.py`, `td2/pair-b/`, `reports/td2.md`, `reviews/crosscheck-05.md`, `reviews/crosscheck-06.md`
**Repository State**: commit `aab2814` (merge of PR #11)

---

## 1. Method

Every figure claimed in `reports/td2.md` and in the TD 2 cross-check logs is recomputed
from the two sources of truth only: `td2/traces-td1.csv` and `td2/data/boutique.sqlite`.
No deliverable is used to verify itself.

The pass is scripted so that any team member can rerun it and get the same verdict:

```bash
python3 td2/qa/verify-td2.py --matrix     # exit code 1 if any check fails
```

Properties of the harness:

- **Offline**: standard library only, no API key, no network, no credit spent.
- **Read-only**: every query goes through `sandbox_sqlite.execute_query` (URI `mode=ro`,
  `PRAGMA query_only`, SELECT-only authorizer, row and time budget).
- **Independent vote**: the quorum matrix is decided by a local oracle written from the
  TD 2 contract in the `vote_k_sur_n` docstring, not by the deliverable it audits. Check
  `pair_a_vote` then compares the two implementations over the 40 decisions
  (20 questions x 2 quorums) plus the three contract failure modes.
- **Decision before scoring**: the reference is never passed to the vote; correctness is
  compared after the decision, as `atelier-vote.py` requires.

## 2. Result of the 12 checks

| Check | Result | Evidence |
|---|---|---|
| `db_fingerprint` | **PASS** | `boutique.sqlite` = `0077e235adc2ca64...`, equal to README section 4 and `data/manifest.json` |
| `trace_inventory` | **PASS** | 104 rows, 100 cells (last attempt per provider/model/case), 20 cases, 5 models, every row `nature = real` |
| `reference_queries` | **PASS** | the 20 reference SQL of `reference-td1.csv` re-executed: every `revenue_cents` reproduced |
| `reference_consistency` | **PASS** | one reference per case in the traces, equal to `reference-td1.csv`, no conflicting experiment |
| `model_accuracy` | **PASS** | 120b 20/20, 20b 18/20, qwen 13/20 (+2 `not_executed`), north-mini-code 13/20, dots 15/20 (+2 `sql_rejected`) |
| `offline_replay` | **PASS** | the recorded SQL of all 100 cells re-executed: 96 values reproduced to the cent, 4 non-executed cells still refused by the sandbox |
| `shared_wrong_values` | **PASS** | exactly C02 (0), C09 (0), C10 (119410), with the model pairs stated in `reports/td2.md` |
| `quorum_2of3` | **PASS** | 17/20 consensus, 1 wrong (C09 = 0), abstentions C10, C17, C19 |
| `quorum_3of5` | **PASS** | 17/20 consensus, 0 wrong, abstentions C09, C10, C17 |
| `pair_a_vote` | **FAIL** | `Orchestrateur.vote_k_sur_n` raises `NotImplementedError` (finding F1) |
| `sql_evidence` | **PASS** | the 6 statements of `td2/pair-b/step2-wrong-consensus.sql` re-executed: 487980 / 0 / 0 / delta 6 rows = 487980 / 487980 / delta 28 rows = 439570 |
| `sql_verbatim` | **PASS** | the two faulty `WHERE` clauses quoted by Pair B are identical to `traces-td1.csv` after comment and whitespace normalisation |

**11 of 12 checks pass.** Pair B's section of `reports/td2.md` is fully reproducible.
The failure and the three findings below concern step 1, step 3, and two cross-check logs.

## 3. Findings

### F1 - Blocking: the voting engine is not implemented

`td2/skeleton-multi-llm-en.py` line 627 is still the kit stub:

```python
raise NotImplementedError("vote_k_sur_n: to implement in TD 2 (see the procedure in the docstring).")
```

Consequence, reproducible:

```
$ python3 td2/atelier-vote.py
vote_k_sur_n: to implement in TD 2 (see the procedure in the docstring).
$ echo $?
2
```

`reviews/crosscheck-05.md` Review 1 reports the opposite: *"All four synthetic test cases
in `atelier-vote.py` passed without assertion failure"*, and *"Duplicate checks and
majority threshold bounds raise explicit `ValueError` exceptions as required"*, with
verdict APPROVED. No code in the repository can produce that output at commit `aab2814`.

Step 1 of the TD 2 statement is therefore not delivered. Pair A owns the fix; the harness
check `pair_a_vote` turns green on its own once the method is implemented, and will also
report any disagreement with the oracle on the 40 decisions.

### F2 - Major: the quorum figures of crosscheck-05 Review 2 are not those of the traces

| Claim in `crosscheck-05.md` | Measured on `traces-td1.csv` |
|---|---|
| "100% agreement with `reference-td1.csv` when consensus is reached" (2-of-3) | **False.** C09 reaches consensus on `0` with 2 votes against a reference of 487980 |
| "On C04, C05, and C11 [...] the 2-of-3 vote correctly drops to an abstention" | **False.** C04 and C05 are unanimous 5/5 and correct; C11 reaches a correct consensus (446690, 2 votes). The three abstentions are C10, C17, C19 |
| "Moving to a 3-of-5 quorum resolves C04 and C05" | **False.** Nothing to resolve: both are already unanimous. 3-of-5 changes exactly two cells: it suppresses the wrong consensus on C09 and recovers C19 |
| "17/20 consensus" (2-of-3) | **True**, but 16 correct and 1 wrong, not 17 correct |

The correction matters for the plenary: the one case where the 2-of-3 panel publishes a
wrong figure is the central empirical result of TD 2. Stating 100% agreement removes it.

### F3 - Major: crosscheck-06 Review 1 audits a case that does not exist in our traces

`crosscheck-06.md` Review 1 reports a false consensus on **C11**, between `gpt-oss-20b`
and `north-mini-code:free`, both at `0`, against a reference of `248180` cents,
reconciled by 3 customers. None of this is in the dataset:

- C11 reference is **446690**, not 248180 (no case in `reference-td1.csv` has 248180).
- On C11, `gpt-oss-20b` returns 322160 and `north-mini-code` returns 0: two *different*
  wrong values, so no agreement and no false consensus.
- The delta is 6 customers for 487980 cents, on **C09**, as `td2/pair-b/` documents.

The likely origin is the statement's own illustration, `DEMO-SQL-C11`, which `td2/README.md`
cites as a teaching example with those two models at `0`. It is an illustration, not a
measurement on our traces. Our batch produces a different case, C09, with a different
pair of models (`qwen` and `north-mini-code`). Pair B investigated the real one; the log
should be aligned on it.

### F4 - Major: step 3 is not in the repository, yet reported as verified

`td2/atelier-routage.py` is unchanged since the workspace setup (`0d1ecd0`, last touched
before the session). It still holds the three generic kit resources
(`small-free`, `senior-subscription`, `senior-api`), and `grep` finds zero TD 1 citation
in the file. `crosscheck-06.md` Review 2 claims the opposite: *"`RESOURCES` updated with
portfolio models, explicit capability tiers (Levels 1 to 3), and token pricing"* and
*"Simulator decisions now include TD 1 cell citations in their `reason` payload"*,
verdict APPROVED.

What is verifiable today: the 7 kit scenarios run and produce deterministic
`run` / `defer` / `abstain` decisions. The routing policy document and the adaptation of
`RESOURCES` and `choose()` with TD 1 accuracy per family are still to be delivered by Pair C.

### F5 - Positive: Pair B's section is reproducible end to end

Everything in `reports/td2.md` section 3 holds under independent recomputation: the three
shared wrong values, the C09 quorum outcomes, the verbatim faulty SQL, the 6-customer
delta totalling 487980, the arithmetic cross-check, and the 28-line C10 delta totalling
439570. The diagnosis of both C09 bugs is confirmed by re-execution: each faulty query
keeps zero rows, and `COALESCE(SUM(...), 0)` turns an empty filter into a plausible `0`.

One wording refinement for the report: the delta window is written
`2000-09-27 <= birth_date <= 2001-09-26` in prose and
`birth_date > '2000-09-26' AND birth_date <= '2001-09-26'` in SQL. The two are equivalent
only because `birth_date` is a pure date with no time part; stating that assumption makes
the boundary argument on C003 airtight.

## 4. Verdict

**CONDITIONAL** - the audited artefacts split in two:

- `td2/pair-b/` and section 3 of `reports/td2.md`: **APPROVED**, fully reproducible.
- Step 1 (`vote_k_sur_n`) and step 3 (`atelier-routage.py`): **REJECTED, not delivered**
  at commit `aab2814`.
- `reviews/crosscheck-05.md` and `reviews/crosscheck-06.md`: **to be corrected** before
  submission. Their current content states results that the traces and the database
  contradict, and an examiner reruns `python3 td2/atelier-vote.py` in one command.

Re-audit by rerunning `python3 td2/qa/verify-td2.py`. The pass is green only when the 12
checks are green.

## 5. Quorum matrix produced by the pass

Decided by the oracle, reference compared after the decision.

| Case | Reference | 2-of-3 panel (k=2) | 3-of-5 quorum (k=3) |
|---|---|---|---|
| C01 | 792800 | 792800 (3v) ok | 792800 (5v) ok |
| C02 | 590320 | 590320 (2v) ok | 590320 (3v) ok |
| C03 | 936350 | 936350 (3v) ok | 936350 (5v) ok |
| C04 | 2826250 | 2826250 (3v) ok | 2826250 (5v) ok |
| C05 | 38480 | 38480 (3v) ok | 38480 (5v) ok |
| C06 | 0 | 0 (3v) ok | 0 (5v) ok |
| C07 | 13970 | 13970 (3v) ok | 13970 (5v) ok |
| C08 | 605580 | 605580 (2v) ok | 605580 (4v) ok |
| **C09** | **487980** | **0 (2v) WRONG** | **abstain (max 2v)** |
| C10 | 558980 | abstain (max 1v) | abstain (max 2v) |
| C11 | 446690 | 446690 (2v) ok | 446690 (3v) ok |
| C12 | 1666490 | 1666490 (3v) ok | 1666490 (5v) ok |
| C13 | 107740 | 107740 (3v) ok | 107740 (5v) ok |
| C14 | 0 | 0 (3v) ok | 0 (5v) ok |
| C15 | 168680 | 168680 (2v) ok | 168680 (3v) ok |
| C16 | 376740 | 376740 (2v) ok | 376740 (3v) ok |
| C17 | 258180 | abstain (max 1v) | abstain (max 2v) |
| C18 | 62480 | 62480 (3v) ok | 62480 (5v) ok |
| C19 | 1990 | abstain (max 1v) | 1990 (3v) ok |
| C20 | 1106090 | 1106090 (2v) ok | 1106090 (4v) ok |

Reading of the two cells that move between the quorums:

- **C09**: the panel publishes a wrong figure, the full quorum abstains. Widening the
  panel brings in a correct vote (`gpt-oss-20b` = 487980) and breaks the 2-2 tie below
  k = 3. Safety here comes from abstention, not from a better answer.
- **C19**: the panel abstains (1990 / 83580 / 13930, one vote each), the full quorum
  recovers 1990 with 3 votes. Widening converts dispersion into a decision.

Everything else is identical between the two quorums: on this batch, widening the panel
costs five extra calls to change two cells out of twenty.
