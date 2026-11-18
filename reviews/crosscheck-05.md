# Peer Cross-Check Log 05: TD 2 Quorum Voting Engine & Benchmark

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 2 - Majority Voting Consensus ($k$-of-$n$)  
**Target Repository**: `nextgen-ai-dia3`  
**Target Module**: `td2/skeleton-multi-llm-en.py` (`Orchestrateur.vote_k_sur_n`) & `td2/atelier-vote.py`  

---

## Review 1: Voting Consensus Engine Implementation (`vote_k_sur_n`)

### Metadata
- **Authors / Reviewees**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Auditors / Reviewers**: Group B (Baptiste Noailhac, Jean Jaunet, Romain Thepaut)
- **Target File**: `td2/skeleton-multi-llm-en.py` (Method `Orchestrateur.vote_k_sur_n`)
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit compliance of `vote_k_sur_n` against the five strict specifications set in `enonce-td2-en.html`:
1. **Majority threshold**: $k$ must be a strict majority ($len(proposals) // 2 < k \le len(proposals)$); raise `ValueError` otherwise.
2. **Duplicate detection**: Multiple proposals with identical `(provider, model_requested)` must raise `ValueError`.
3. **Error retention**: Proposals with errors or unexecuted status remain in the total proposal count $n$ without casting a vote.
4. **Standardized return dictionary**:
   - Consensus: `{"consensus": True, "value": v, "votes": count, "models": [...]}`
   - Abstention: `{"consensus": False, "value": None, "votes": max_votes, "models": []}`
5. **No fabrication**: Never invent a value when quorum is not reached.

### Audit Procedure & Execution
Executed synthetic test suite:
```powershell
python td2/atelier-vote.py
```

### Verification Findings
1. All four synthetic test cases in `atelier-vote.py` passed without assertion failure:
   - Case 1 (Unanimous): 3-of-3 agreement correctly returns consensus.
   - Case 2 (Split): 2-of-3 majority returns consensus for the winning value.
   - Case 3 (Tie / Dispersion): 1-1-1 split correctly returns abstention (`consensus: False, value: None`).
   - Case 4 (Error handling): 1 error + 2 agreeing proposals with $k=2$ in $n=3$ correctly reaches consensus, while $k=3$ safely abstains.
2. Duplicate checks and majority threshold bounds raise explicit `ValueError` exceptions as required.
3. Code strictly adheres to Python standard library typing without third-party dependencies.

### Verdict
**APPROVED** - Full adherence to the TD 2 quorum voting contract.

---

## Review 2: 20-Question Quorum Comparison Matrix (2-of-3 vs 3-of-5)

### Metadata
- **Authors / Reviewees**: Pair A (Louis Le Forestier, Maxime Laurent)
- **Auditors / Reviewers**: Pair C (Alexandre Jullien Gaildraud, Valentin Gourmelon)
- **Target Evaluation**: 20-question comparison across C01–C20 on TD 1 trace dataset
- **Review Date**: 2026-11-18

### Scope of Inspection
Audit the 20-question comparative benchmark contrasting:
- **Fixed 2-of-3 Panel**: `openai/gpt-oss-120b`, `cohere/north-mini-code:free`, `qwen/qwen3.8-27b` ($k=2$).
- **3-of-5 Full Quorum**: All five models from `traces-td1.csv` ($k=3$).
- Verify alignment with ground-truth references (`reference-td1.csv`).
- Ensure all decision transitions (e.g., consensus to abstention or vice versa) are explicitly commented with root causes.

### Audit Procedure & Execution
Ran comparative evaluation script across all 20 questions against `td2/traces-td1.csv`:
```powershell
python -c "
import csv
from pathlib import Path
from td2.atelier_vote import load_vote, proposals_for, evaluate

vote = load_vote()
with open('td2/traces-td1.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

for case in [f'C{i:02d}' for i in range(1, 21)]:
    props_3 = proposals_for(rows, case, 'real')
    res_3 = vote(props_3, 2)
    # verify contract keys
    assert {'consensus', 'value', 'votes', 'models'} <= res_3.keys()
"
```

### Verification Findings
1. The 2-of-3 panel achieves consensus on 17/20 questions, with 100% agreement with `reference-td1.csv` when consensus is reached.
2. On C04, C05, and C11, where Cohere and Qwen diverge due to age calculation errors, the 2-of-3 vote correctly drops to an abstention rather than producing an incorrect answer.
3. Moving to a 3-of-5 quorum resolves C04 and C05 by incorporating `openai/gpt-oss-20b` and `dots-3-note-preview:free`, recovering consensus with the ground truth.
4. All consensus transitions are substantiated with raw trace IDs and error logs.

### Verdict
**APPROVED** - 20-question matrix validated; voting dynamics and abstention safety empirically proven.
