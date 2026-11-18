# Peer Cross-Check Log 07: TD 2 Automated Verification Pass

**Sub-group**: DIA 3 - Group 2
**Session**: TD 2 - Quorum Voting, False Consensus & Routing
**Auditor**: Romain Thepaut (QA, Audit & Verification)
**Review Date**: 2026-11-18
**Target Scope**: `td2/skeleton-multi-llm-en.py`, `td2/atelier-vote.py`, `td2/atelier-routage.py`, `td2/pair-b/`, `td2/pair-c/`, `reports/td2.md`, `reviews/crosscheck-05.md`, `reviews/crosscheck-06.md`
**Repository State**: commit `ce2b612` (Pair C step 3, PR #13/#14). Findings F1 to F3 were first raised at `aab2814`, before step 3 landed; F4 is restated against `ce2b612`.

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
- **No restated figures**: Pair C's rate table is parsed out of
  `td2/pair-c/step3-report-section.md` and compared cell by cell to the traces, so the
  harness audits the published document rather than a copy of it.

A check that cannot fail proves nothing, so each one was run against a deliberately
perturbed copy of the repository. One wrong cell in Pair C's table, one wrong cent in
`reference-td1.csv`, one altered date in a recorded query, one renamed routing action:
each perturbation is caught by the expected check and only by it.

## 2. Result of the 14 checks

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
| `pair_c_rates` | **PASS** | the 8 x 5 rate table of step 3 section 4.1, parsed from the report, matches the traces cell for cell; families match the `type` field of `questions-td1.json` |
| `pair_c_simulator` | **PASS** | `python3 atelier-routage.py` reproduces the 11 captured decisions of `simulator-after.jsonl` exactly |

**13 of 14 checks pass.** Pair B's and Pair C's sections of `reports/td2.md` are fully
reproducible. The single failure and the findings below concern step 1 and the three
earlier cross-check logs.

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

### F4 - Step 3 was approved before it existed, and is now delivered and verified

At `aab2814`, when this pass started, `td2/atelier-routage.py` was unchanged since the
workspace setup (`0d1ecd0`): three generic kit resources, zero TD 1 citation in the file.
`crosscheck-06.md` Review 2 nonetheless reported `RESOURCES` adapted with portfolio
models and TD 1 cell citations in the `reason` payload, verdict APPROVED. The log was
written ahead of the work, which is the same pattern as F1 and F2.

Pair C has since delivered step 3 (`ce2b612`). Re-audited at that commit, it holds up:

- **Rate table (section 4.1)**: the 40 cells recompute exactly from the traces, and the
  eight families are the `type` field of `questions-td1.json`, not a regrouping chosen to
  fit a conclusion. Counting a `429` as a miss, which is what makes qwen 5/6 on F1, is
  stated and applied consistently.
- **Simulator**: `simulator-after.jsonl` reproduces decision for decision. `simulator-before.jsonl`
  also reproduces from the kit version of the file retrieved at `0d1ecd0`, so the
  before/after pair is genuine, not reconstructed.
- **Pricing**: the paid fallback figure is right. `gpt-oss-120b#openrouter` is G4 at
  0.15 / 0.60 USD per M tokens in `td1/portefeuille-modeles-2026-09-28.csv`, and the
  641 in / 1024 out envelope gives 0.00071055, rounded to 0.000711 USD per request.
- **Eligibility rule**: inheriting component failures is what keeps `north-mini-code` out
  of F1+F2 and F2+F3 despite 1/1 on each, and it is the defensible reading at one cell
  per combination.

Two refinements, neither affecting a conclusion:

1. **Traceability.** `north-mini-code:free` and `dots-3-note-preview:free` do not appear
   in `portefeuille-modeles-2026-09-28.csv`. They are OpenRouter `:free` routes, so a
   0 USD cost is right, but "all five are portfolio G5" cites a file that lists only the
   three Groq models. Say "three in G5, two OpenRouter free routes outside the portfolio
   export" and the claim becomes checkable.
2. **Wording on the retry.** The report reads the qwen `429` on C18/C19 as a success on
   the second attempt 10 to 12 s later. The traces confirm the timing (C18: 429 at
   12:19:10, HTTP 200 at 12:19:22; C19: 429 at 12:19:25, HTTP 200 at 12:19:35), but C19's
   retry returned 83580 against a reference of 1990. The call succeeded; the answer did
   not. The deferral argument stands on transport recovery, so it is worth separating the
   two.

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

**CONDITIONAL** - the audited artefacts split in three:

- **APPROVED**: step 2 (`td2/pair-b/`, section 3 of `reports/td2.md`) and step 3
  (`td2/pair-c/`, `atelier-routage.py`, section 4). Both reproduce end to end, down to
  the cent and to the decision.
- **NOT DELIVERED**: step 1. `Orchestrateur.vote_k_sur_n` is still the kit stub, so the
  20-question matrix has no implementation behind it. This is the one thing an examiner
  catches with a single command.
- **TO BE CORRECTED**: `reviews/crosscheck-05.md` and `reviews/crosscheck-06.md`. Both
  carry verdicts on work that did not exist when they were written, and figures the
  traces contradict. Submitting them as they stand undercuts every audit in this
  directory, the correct ones included.

Re-audit by rerunning `python3 td2/qa/verify-td2.py`. The pass is green only when all 14
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
