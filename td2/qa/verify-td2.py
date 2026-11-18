#!/usr/bin/env python3
"""Re-derive every figure of the TD 2 report from traces-td1.csv and boutique.sqlite,
independently of the deliverables that produced them. Offline, standard library only,
read-only through sandbox_sqlite. Exit code 1 if any check fails.

    python3 td2/qa/verify-td2.py              # all checks
    python3 td2/qa/verify-td2.py --matrix     # also print the 20-question matrix
"""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD2 = HERE.parent

DB = TD2 / "data" / "boutique.sqlite"
MANIFEST = TD2 / "data" / "manifest.json"
TRACES = TD2 / "traces-td1.csv"
REFERENCE = TD2 / "reference-td1.csv"
QUESTIONS = TD2 / "questions-td1.json"
SKELETON = TD2 / "skeleton-multi-llm-en.py"
SKELETON_TD1 = TD2.parent / "td1" / "skeleton-multi-llm-en.py"
ROUTER = TD2 / "atelier-routage.py"
PAIR_B_SQL = TD2 / "pair-b" / "step2-wrong-consensus.sql"
PAIR_C_AFTER = TD2 / "pair-c" / "simulator-after.jsonl"
PAIR_C_REPORT = TD2 / "pair-c" / "step3-report-section.md"

# Fingerprint published in README.md section 4 (seed 20260925).
README_DB_SHA256 = "0077e235adc2ca647b484e3083c98a6d7cae3ef3655ce366a299caf13398fec2"

# Fixed 2-of-3 panel of atelier-vote.py: three distinct model families.
PANEL_3 = [
    ("groq", "openai/gpt-oss-120b"),
    ("openrouter", "cohere/north-mini-code:free"),
    ("groq", "qwen/qwen3.8-27b"),
]

# Trace inventory expected for the TD 1 export used by TD 2.
EXPECTED_ROWS = 104
EXPECTED_CELLS = 100
EXPECTED_CASES = 20
EXPECTED_VERDICTS = {
    "openai/gpt-oss-120b": {"correct": 20},
    "openai/gpt-oss-20b": {"correct": 18, "incorrect": 2},
    "qwen/qwen3.8-27b": {"correct": 13, "incorrect": 5, "not_executed": 2},
    "cohere/north-mini-code:free": {"correct": 13, "incorrect": 7},
    "dots-studio/dots-3-note-preview:free": {"correct": 15, "incorrect": 3, "sql_rejected": 2},
}

# Claims of reports/td2.md section 3 that this harness must confirm or break.
EXPECTED_SHARED_WRONG = {
    "C02": (0, {"openai/gpt-oss-20b", "cohere/north-mini-code:free"}),
    "C09": (0, {"qwen/qwen3.8-27b", "cohere/north-mini-code:free"}),
    "C10": (119410, {"qwen/qwen3.8-27b", "dots-studio/dots-3-note-preview:free"}),
}
EXPECTED_2OF3 = {"consensus": 17, "wrong": {"C09": 0}, "abstentions": {"C10", "C17", "C19"}}
EXPECTED_3OF5 = {"consensus": 17, "wrong": {}, "abstentions": {"C09", "C10", "C17"}}

# Question families, as the `type` field of questions-td1.json names them.
FAMILIES = {
    "period": "F1",
    "age on a reference date": "F2",
    "age at the time of the order": "F2b",
    "product list": "F3",
    "period + age on a reference date": "F1+F2",
    "age on a reference date + product list": "F2+F3",
    "period + age on a reference date + product list": "F1+F2+F3",
    "period + age at the time of the order": "F1+F2b",
}

# Expected result of each statement of step2-wrong-consensus.sql, in file order.
# (label, expected 1x1 value) or (label, expected row count, expected total_gap_cents).
EXPECTED_SQL_EVIDENCE = [
    ("reference C09", 487980),
    ("north-mini-code C09", 0),
    ("qwen3.8-27b C09", 0),
    ("delta C09", 6, 487980),
    ("independent C09", 487980),
    ("delta C10", 28, 439570),
]



def load_sandbox():
    spec = importlib.util.spec_from_file_location("sandbox_sqlite", TD2 / "sandbox_sqlite.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_traces():
    with TRACES.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def last_attempts(rows):
    """One cell per (provider, model, case): the last attempt wins, as in atelier-vote.py."""
    cells = {}
    for row in rows:
        cells[(row["provider"], row["model_requested"], row["case_id"])] = row
    return cells


def normalize_sql(sql):
    """Comments out, whitespace collapsed, lowercase: compares SQL text, not layout."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").strip().lower()


def sql_statements(path):
    """SELECT statements of a .sql file, dot-commands and comments removed."""
    text = re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))
    statements = []
    for chunk in text.split(";"):
        body = "\n".join(line for line in chunk.splitlines() if not line.strip().startswith("."))
        if re.match(r"^\s*(select|with)\b", body, flags=re.I):
            statements.append(body.strip())
    return statements



def vote_oracle(proposals, k):
    """k-of-n majority vote over (provider, model, value, executed) tuples, per the TD 2 contract."""
    n = len(proposals)
    if not n // 2 < k <= n:
        raise ValueError(f"k={k} is not a strict majority of n={n}")
    seen = set()
    for provider, model, _value, _executed in proposals:
        if (provider, model) in seen:
            raise ValueError(f"duplicate proposal for {provider}:{model}")
        seen.add((provider, model))
    tally = collections.defaultdict(list)
    for provider, model, value, executed in proposals:
        if executed and value is not None:
            tally[value].append(f"{provider}:{model}")
    if not tally:
        return {"consensus": False, "value": None, "votes": 0, "models": []}
    value, models = max(tally.items(), key=lambda item: len(item[1]))
    if len(models) >= k:
        return {"consensus": True, "value": value, "votes": len(models), "models": models}
    return {"consensus": False, "value": None, "votes": len(models), "models": []}


def proposals_for(cells, panel, case):
    """Panel proposals for one case. An unavailable member stays in n without voting."""
    proposals = []
    for provider, model in panel:
        row = cells.get((provider, model, case))
        executed = bool(row) and row["verdict"] in {"correct", "incorrect"} and row["value"] not in {None, ""}
        proposals.append((provider, model, int(row["value"]) if executed else None, executed))
    return proposals



class Report:
    def __init__(self):
        self.results = []

    def add(self, name, ok, detail):
        self.results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:22} {detail}")

    @property
    def failed(self):
        return [name for name, ok, _ in self.results if not ok]


def check_db_fingerprint(report):
    digest = hashlib.sha256(DB.read_bytes()).hexdigest()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ok = digest == README_DB_SHA256 == manifest["sqlite_file_sha256"]
    report.add("db_fingerprint", ok, f"sha256 {digest[:16]}... vs README and manifest")


def check_trace_inventory(report, rows, cells):
    natures = {row["nature"] for row in rows}
    models = {row["model_requested"] for row in rows}
    cases = {row["case_id"] for row in rows}
    ok = (len(rows) == EXPECTED_ROWS and len(cells) == EXPECTED_CELLS
          and natures == {"real"} and len(cases) == EXPECTED_CASES
          and models == set(EXPECTED_VERDICTS))
    report.add("trace_inventory", ok,
               f"{len(rows)} rows, {len(cells)} cells, {len(cases)} cases, "
               f"{len(models)} models, nature={sorted(natures)}")


def load_reference():
    with REFERENCE.open(encoding="utf-8", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def check_reference_queries(report, sandbox):
    """Ground truth must be re-derivable: each reference SQL re-run on this database."""
    failures = []
    reference = load_reference()
    for case, row in sorted(reference.items()):
        result = sandbox.execute_query(DB, row["sql"], max_rows=1)
        if not result["shape_ok"] or result["value"] != int(row["revenue_cents"]):
            failures.append((case, row["revenue_cents"], result.get("value"), result.get("reason")))
    report.add("reference_queries", not failures,
               f"{len(reference)} reference queries re-executed, every value reproduced"
               if not failures else f"{failures}")


def check_reference_consistency(report, rows, cells):
    published = {case: int(row["revenue_cents"]) for case, row in load_reference().items()}
    per_case = collections.defaultdict(set)
    for row in rows:
        if row["reference"] not in {None, ""}:
            per_case[row["case_id"]].add(int(row["reference"]))
    conflicts = {case for case, values in per_case.items() if len(values) > 1}
    mismatches = {case: (values, published.get(case))
                  for case, values in per_case.items()
                  if not conflicts and published.get(case) not in values}
    ok = not conflicts and not mismatches and len(per_case) == EXPECTED_CASES
    report.add("reference_consistency", ok,
               f"{len(per_case)} cases, conflicts={sorted(conflicts)}, mismatches={sorted(mismatches)}")


def check_model_accuracy(report, cells):
    observed = collections.defaultdict(collections.Counter)
    for (_provider, model, _case), row in cells.items():
        observed[model][row["verdict"]] += 1
    diffs = {model: dict(counts) for model, counts in observed.items()
             if dict(counts) != EXPECTED_VERDICTS.get(model)}
    report.add("model_accuracy", not diffs,
               "per-model verdict counts match the TD 1 report" if not diffs else f"drift: {diffs}")


def check_offline_replay(report, sandbox, cells):
    """Every recorded value must come back from the recorded SQL on this database."""
    replayed = rejected = 0
    mismatches = []
    for (provider, model, case), row in sorted(cells.items()):
        result = sandbox.execute_query(DB, row["sql"], max_rows=1)
        executed = row["verdict"] in {"correct", "incorrect"}
        if executed:
            if result["shape_ok"] and str(result["value"]) == row["value"]:
                replayed += 1
            else:
                mismatches.append((case, model, row["value"], result.get("value"), result.get("reason")))
        elif result["shape_ok"]:
            mismatches.append((case, model, f"expected {row['verdict']}", result.get("value"), "executed"))
        else:
            rejected += 1
    report.add("offline_replay", not mismatches,
               f"{replayed} values reproduced, {rejected} non-executed cells still refused"
               + (f", {len(mismatches)} mismatches: {mismatches[:3]}" if mismatches else ""))


def check_shared_wrong_values(report, cells):
    """Wrong consensus candidates: distinct models returning the same wrong value."""
    found = {}
    for case in sorted({case for _p, _m, case in cells}):
        by_value = collections.defaultdict(set)
        for (provider, model, cell_case), row in cells.items():
            if cell_case == case and row["verdict"] == "incorrect" and row["value"] not in {None, ""}:
                by_value[int(row["value"])].add(model)
        for value, models in by_value.items():
            if len(models) > 1:
                found[case] = (value, models)
    ok = found == EXPECTED_SHARED_WRONG
    report.add("shared_wrong_values", ok,
               f"{sorted(found)} " + (f"as reported" if ok else f"but report claims {sorted(EXPECTED_SHARED_WRONG)}: {found}"))
    return found


def quorum_matrix(cells):
    """Both quorums over the 20 questions, decided by the oracle, scored afterwards."""
    all_models = sorted({(provider, model) for provider, model, _case in cells})
    matrix = []
    for case in sorted({case for _p, _m, case in cells}):
        reference = int(next(row["reference"] for (_p, _m, c), row in cells.items() if c == case))
        small = vote_oracle(proposals_for(cells, PANEL_3, case), 2)
        full = vote_oracle(proposals_for(cells, all_models, case), 3)
        matrix.append({"case": case, "reference": reference, "2of3": small, "3of5": full,
                       "votes": proposals_for(cells, all_models, case)})
    return matrix


def score(matrix, key):
    consensus = [row for row in matrix if row[key]["consensus"]]
    wrong = {row["case"]: row[key]["value"] for row in consensus if row[key]["value"] != row["reference"]}
    abstentions = {row["case"] for row in matrix if not row[key]["consensus"]}
    return {"consensus": len(consensus), "wrong": wrong, "abstentions": abstentions}


def check_quorum_matrix(report, matrix):
    for key, expected in (("2of3", EXPECTED_2OF3), ("3of5", EXPECTED_3OF5)):
        observed = score(matrix, key)
        ok = observed == expected
        report.add(f"quorum_{key}", ok,
                   f"{observed['consensus']}/20 consensus, wrong={observed['wrong']}, "
                   f"abstentions={sorted(observed['abstentions'])}"
                   + ("" if ok else f" (expected {expected})"))


def check_pair_a_vote(report, cells, matrix):
    """Pair A's vote_k_sur_n must satisfy the contract and agree with the oracle."""
    spec = importlib.util.spec_from_file_location("student_skeleton", SKELETON)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class Proposal:
        def __init__(self, provider, model, value, executed):
            self.provider = provider
            self.model_requested = model
            self.value = value
            self.verdict = "executed" if executed else "error"

    def call(proposals, k):
        return module.Orchestrateur.vote_k_sur_n(None, [Proposal(*p) for p in proposals], k)

    sample = proposals_for(cells, PANEL_3, "C01")
    try:
        call(sample, 2)
    except NotImplementedError:
        report.add("pair_a_vote", False,
                   "Orchestrateur.vote_k_sur_n still raises NotImplementedError: TD 2 step 1 not delivered")
        return

    failures = []
    for k in (1, 0, 4):                                  # 3 // 2 < k <= 3 only
        try:
            call(sample, k)
            failures.append(f"k={k} accepted, ValueError expected")
        except ValueError:
            pass
    duplicate = sample + [sample[0]]
    try:
        call(duplicate, 3)
        failures.append("duplicate (provider, model) accepted, ValueError expected")
    except ValueError:
        pass
    all_models = sorted({(provider, model) for provider, model, _case in cells})
    for row in matrix:
        for panel, k, key in ((PANEL_3, 2, "2of3"), (all_models, 3, "3of5")):
            try:
                result = call(proposals_for(cells, panel, row["case"]), k)
            except Exception as error:                   # noqa: BLE001 - audit must report, not crash
                failures.append(f"{row['case']} {key}: {type(error).__name__}: {error}")
                continue
            expected = row[key]
            if not isinstance(result, dict) or {"consensus", "value", "votes", "models"} - result.keys():
                failures.append(f"{row['case']} {key}: return shape {result}")
            elif (result["consensus"], result["value"]) != (expected["consensus"], expected["value"]):
                failures.append(f"{row['case']} {key}: {result['consensus']}/{result['value']} "
                                f"vs oracle {expected['consensus']}/{expected['value']}")
    report.add("pair_a_vote", not failures,
               "contract honoured and 40 decisions agree with the oracle" if not failures
               else f"{len(failures)} deviations: {failures[:4]}")


def parse_report_rates(path):
    """Rate table of section 4.1, read from the report itself rather than restated here."""
    models, rates = [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not models:
            for cell in cells[2:]:
                match = [model for model in EXPECTED_VERDICTS
                         if model.split("/")[-1].split(":")[0].rstrip("-preview") in cell]
                if match:
                    models.append(match[0])
            continue
        family = re.match(r"\*{0,2}(F\d+b?(?:\+F\d+b?)*)\b", cells[0])
        if not family or len(cells) < 2 + len(models):
            continue
        scores = [re.search(r"(\d+)/(\d+)", cell) for cell in cells[2:2 + len(models)]]
        if all(scores):
            rates[family.group(1)] = {model: score.group(0) for model, score in zip(models, scores)}
    return rates


def check_pair_c_rates(report, cells):
    """Pair C's per-family rate table, recomputed from the traces and the question types."""
    published = parse_report_rates(PAIR_C_REPORT)
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    by_family = collections.defaultdict(list)
    for question in questions:
        by_family[FAMILIES[question["type"]]].append(question["id"])
    if set(by_family) != set(published):
        report.add("pair_c_rates", False,
                   f"families of questions-td1.json {sorted(by_family)} "
                   f"differ from the report table {sorted(published)}")
        return
    diffs = {}
    for family, ids in by_family.items():
        for model in EXPECTED_VERDICTS:
            provider = "groq" if "gpt-oss" in model or "qwen" in model else "openrouter"
            correct = sum(1 for case in ids if cells[(provider, model, case)]["verdict"] == "correct")
            measured = f"{correct}/{len(ids)}"
            if measured != published[family][model]:
                diffs[f"{family}/{model}"] = f"report {published[family][model]}, traces {measured}"
    report.add("pair_c_rates", not diffs,
               f"{len(by_family)} families x {len(EXPECTED_VERDICTS)} models: "
               f"the section 4.1 table matches the traces cell for cell"
               if not diffs else f"{diffs}")


def check_pair_c_simulator(report):
    """The captured routing decisions must be what the committed simulator produces today."""
    try:
        completed = subprocess.run([sys.executable, ROUTER.name], cwd=ROUTER.parent,
                                   capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        report.add("pair_c_simulator", False, f"{type(error).__name__}: {error}")
        return
    if completed.returncode != 0:
        report.add("pair_c_simulator", False,
                   f"atelier-routage.py exited {completed.returncode}: {completed.stderr.strip()[:160]}")
        return
    produced = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    captured = [json.loads(line) for line in PAIR_C_AFTER.read_text(encoding="utf-8").splitlines() if line.strip()]
    drift = [produced[i].get("scenario") for i in range(min(len(produced), len(captured)))
             if produced[i] != captured[i]]
    ok = len(produced) == len(captured) and not drift
    report.add("pair_c_simulator", ok,
               f"{len(produced)} scenarios, simulator-after.jsonl reproduces exactly" if ok
               else f"{len(produced)} produced vs {len(captured)} captured, drift on {drift}")


def check_skeleton_sync(report):
    """The vote lives in two skeletons but only the td2 copy is exercised by atelier-vote.py."""
    def vote_source(path):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name == "vote_k_sur_n":
                return ast.unparse(node)
        return None

    try:
        in_td2, in_td1 = vote_source(SKELETON), vote_source(SKELETON_TD1)
    except (OSError, SyntaxError) as error:
        report.add("skeleton_sync", False, f"{type(error).__name__}: {error}")
        return
    if in_td2 is None or in_td1 is None:
        missing = [str(path) for path, source in ((SKELETON, in_td2), (SKELETON_TD1, in_td1))
                   if source is None]
        report.add("skeleton_sync", False, f"vote_k_sur_n not found in {missing}")
        return
    report.add("skeleton_sync", in_td2 == in_td1,
               "the td1 and td2 copies of vote_k_sur_n are the same code" if in_td2 == in_td1
               else "the td1 and td2 copies of vote_k_sur_n have diverged; "
                    "atelier-vote.py only exercises the td2 one")


def check_sql_evidence(report, sandbox):
    """Re-run Pair B's delta SQL and compare every figure quoted in the report."""
    statements = sql_statements(PAIR_B_SQL)
    if len(statements) != len(EXPECTED_SQL_EVIDENCE):
        report.add("sql_evidence", False,
                   f"{len(statements)} statements, {len(EXPECTED_SQL_EVIDENCE)} expected: review the mapping")
        return
    failures = []
    for statement, expected in zip(statements, EXPECTED_SQL_EVIDENCE):
        label = expected[0]
        result = sandbox.execute_query(DB, statement, max_rows=50)
        if not result["ok"]:
            failures.append(f"{label}: {result['reason']} {result['detail']}")
            continue
        if len(expected) == 2:
            value = result["rows"][0][-1] if result["rows"] else None
            if value != expected[1]:
                failures.append(f"{label}: {value} vs {expected[1]} expected")
        else:
            _label, rows_expected, total_expected = expected
            total = result["rows"][0][-1] if result["rows"] else None
            if len(result["rows"]) != rows_expected or total != total_expected:
                failures.append(f"{label}: {len(result['rows'])} rows / total {total} "
                                f"vs {rows_expected} rows / {total_expected} expected")
    report.add("sql_evidence", not failures,
               f"{len(statements)} statements re-executed read-only, all figures match"
               if not failures else f"{failures}")


def check_sql_verbatim(report, cells):
    """The faulty queries quoted by Pair B must be the ones in the traces."""
    quoted = {}
    for statement in sql_statements(PAIR_B_SQL):
        match = re.search(r"'(north-mini-code|qwen3\.8-27b)'\s+AS\s+q", statement, flags=re.I)
        if match:
            quoted[match.group(1)] = statement
    pairs = [("north-mini-code", ("openrouter", "cohere/north-mini-code:free")),
             ("qwen3.8-27b", ("groq", "qwen/qwen3.8-27b"))]
    failures = []
    for label, (provider, model) in pairs:
        statement = quoted.get(label)
        if statement is None:
            failures.append(f"{label}: not quoted in {PAIR_B_SQL.name}")
            continue
        traced = cells[(provider, model, "C09")]["sql"]
        where_quoted = normalize_sql(statement).split(" where ", 1)[-1]
        where_traced = normalize_sql(traced).split(" where ", 1)[-1]
        if where_quoted != where_traced:
            failures.append(f"{label}: WHERE clause differs from the trace")
    report.add("sql_verbatim", not failures,
               "both faulty WHERE clauses are verbatim from traces-td1.csv"
               if not failures else f"{failures}")


def print_matrix(matrix):
    print("\n20-question quorum matrix (oracle vote, reference compared after the decision)")
    print(f"{'case':5} {'reference':>9} | {'2-of-3 panel':>26} | {'3-of-5 quorum':>26}")
    for row in matrix:
        def cell(key):
            result = row[key]
            if not result["consensus"]:
                return f"abstain (max {result['votes']}v)"
            flag = "ok" if result["value"] == row["reference"] else "WRONG"
            return f"{result['value']} ({result['votes']}v) {flag}"
        print(f"{row['case']:5} {row['reference']:>9} | {cell('2of3'):>26} | {cell('3of5'):>26}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", action="store_true", help="print the 20-question quorum matrix")
    args = parser.parse_args()

    sandbox = load_sandbox()
    rows = load_traces()
    cells = last_attempts(rows)
    report = Report()

    check_db_fingerprint(report)
    check_trace_inventory(report, rows, cells)
    check_reference_queries(report, sandbox)
    check_reference_consistency(report, rows, cells)
    check_model_accuracy(report, cells)
    check_offline_replay(report, sandbox, cells)
    check_shared_wrong_values(report, cells)
    matrix = quorum_matrix(cells)
    check_quorum_matrix(report, matrix)
    check_pair_a_vote(report, cells, matrix)
    check_skeleton_sync(report)
    check_sql_evidence(report, sandbox)
    check_sql_verbatim(report, cells)
    check_pair_c_rates(report, cells)
    check_pair_c_simulator(report)

    if args.matrix:
        print_matrix(matrix)

    failed = report.failed
    print(f"\n{len(report.results) - len(failed)}/{len(report.results)} checks passed"
          + (f", failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
