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
