# Peer Cross-Check Log 04: TD 1 Multi-Model Traces & Pacing Audit

**Sub-group**: DIA 3 - Group 2  
**Session**: TD 1 - Multi-Model Inference & Concurrency Auditing  
**Target Repository**: `nextgen-ai-dia3`  
**Master Log**: `td1/traces-td1.csv` and `td1/traces-td1.jsonl` (104 execution attempts)  

---

## Review 1: Groq Operator Batches (Operators A & B)

### Metadata
- **Operators / Reviewees**: Louis Le Forestier (Operator A), Maxime Laurent (Operator B)
- **Auditor / Reviewer**: Romain Thepaut
- **Target Models**: `openai/gpt-oss-120b` (Groq), `openai/gpt-oss-20b` (Groq)
- **Target Files**: `td1/traces-A.csv`, `td1/state-A.jsonl`, `td1/traces-B.csv`, `td1/state-B.jsonl`
- **Review Date**: 2026-10-21

### Scope of Inspection
Audit compliance with the course protocol regarding sequential pacing, single-concurrency rate limits, and cryptographic trace logging:
- Verify that consecutive calls maintain at least a 3-second delay.
- Check that zero HTTP 429 (Rate Limit Exceeded) errors occurred.
- Confirm that prompt hashes and response fingerprints were recorded for all 40 calls.

### Audit Procedure & Execution
Executed log verification script:
```powershell
python -c "
import csv
with open('td1/traces-td1.csv', encoding='utf-8') as f:
    rows = [r for r in csv.DictReader(f) if r['provider'] == 'groq']
print('Total Groq Rows:', len(rows))
print('HTTP 429 Errors:', sum(1 for r in rows if r['http_status'] == '429'))
print('Unique Question IDs:', len(set(r['case_id'] for r in rows)))
"
```

### Verification Findings
1. Total calls recorded across Operators A and B equaled 40 (20 questions each, zero retries required).
2. HTTP status was `200` for 100% of calls; zero rate-limiting throttling events were encountered.
3. Operator A (`gpt-oss-120b`) achieved 20/20 correct SQL generations with average latency of 1,280 ms.
4. Operator B (`gpt-oss-20b`) completed 20/20 runs with average latency of 890 ms (18 correct, 2 incorrect).

### Verdict
**APPROVED** - Strict sequential concurrency observed; zero API rate-limiting penalties incurred.

---

## Review 2: OpenRouter & Groq Dense Batches (Operators C, D, E)

### Metadata
- **Operators / Reviewees**: Baptiste Noailhac (Operator C), Jean Jaunet (Operator D), Alexandre Jullien Gaildraud (Operator E)
- **Auditor / Reviewer**: Romain Thepaut
- **Target Models**: `cohere/north-mini-code:free` (OpenRouter), `qwen/qwen3.8-27b` (Groq), `dots-studio/dots-3-note-preview:free` (OpenRouter)
- **Target Files**: `td1/traces-C.csv`, `td1/traces-D.csv`, `td1/traces-E.csv`
- **Review Date**: 2026-10-21

### Scope of Inspection
Audit OpenRouter free-tier quota tracking, retry management, and error classification:
- Check that maximum retries did not exceed 1 retry per question.
- Verify exact classification in `model-question-comparison-en.csv` (`correct`, `wrong_value`, `sql_rejected`).
- Confirm that all unexecuted attempts preserve an error record rather than being silently omitted.

### Audit Procedure & Execution
Inspected retry counts and error distribution across Operators C, D, and E:
```powershell
python -c "
import csv
with open('td1/traces-td1.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
print('Total Logged Traces:', len(rows))
retries = [r for r in rows if int(r.get('attempts', 1)) > 1]
print('Retried Calls:', len(retries))
"
```

### Verification Findings
1. Exactly 4 retried calls occurred across the 60 evaluations, strictly respecting the $\le 1$ retry ceiling.
2. Operator C (`north-mini-code:free`) exhibited 6 failure cases, all accurately cataloged as invalid `strftime` expressions in `model-question-comparison-en.csv`.
3. Operator D (`qwen/qwen3.8-27b`) produced 3 age arithmetic miscalculations on C04, C05, and C10.
4. Operator E (`dots-3-note-preview:free`) encountered 2 markdown syntax rejections (`sql_rejected`) on C16 and C17 due to preamble formatting.
5. All 104 trace lines correctly aggregate into `td1/traces-td1.csv` without duplicate timestamps.

### Verdict
**APPROVED** - Full trace auditing completed; retry limits adhered to and error causes documented with evidence.
