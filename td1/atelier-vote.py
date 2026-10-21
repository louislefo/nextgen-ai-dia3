#!/usr/bin/env python3
"""TD 2: run your vote on four synthetic examples, or on the stored traces of one question.

No network, no key. The panel is fixed to three distinct model families. The
reference is compared AFTER the decision: the vote never receives it.

    python3 atelier-vote.py                                    # four synthetic examples
    python3 atelier-vote.py --traces traces-td1.csv --case C02  # the real traces of one question
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

PANEL = [
    ("groq", "openai/gpt-oss-120b"),
    ("openrouter", "cohere/north-mini-code:free"),
    ("groq", "qwen/qwen3.8-27b"),
]


def load_vote():
    spec = importlib.util.spec_from_file_location("student_skeleton", Path(__file__).with_name("skeleton-multi-llm-en.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return lambda proposals, k: module.Orchestrateur.vote_k_sur_n(None, proposals, k)


def proposals_for(rows, case, nature):
    """Fixed panel: an unavailable member keeps its place but casts no vote.

    The last CSV row per panel member is its last attempt. Use one chronological
    export per experiment; reject mixed experiments rather than merging them.
    References and correctness verdicts are not passed to the student's vote.
    """
    selected = {}
    for row in rows:
        key = (row["provider"], row["model_requested"])
        if row["case_id"] == case and row["nature"] == nature and key in PANEL:
            selected[key] = row
    proposals = []
    for provider, model in PANEL:
        row = selected.get((provider, model), {})
        value = row.get("value", "")
        valid = row.get("verdict") in {"correct", "incorrect"} and value not in {None, ""}
        proposals.append(SimpleNamespace(provider=provider, model_requested=model,
                                         value=int(value) if valid else None,
                                         verdict="executed" if valid else "error"))
    return proposals


def evaluate(vote, proposals, reference=None):
    result = vote(proposals, 2)
    required = {"consensus", "value", "votes", "models"}
    if not isinstance(result, dict) or not required <= result.keys():
        raise ValueError("Return consensus, value, votes and models as specified in TD2.")
    # Correctness is evaluated AFTER the decision, never used to choose a vote.
    return {"decision": result, "reference": reference,
            "matches_reference": (result["value"] == reference)
            if reference is not None and result["consensus"] else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path)
    parser.add_argument("--case", default="C01")
    parser.add_argument("--nature", choices=["real", "replay", "simulation"], default="real")
    args = parser.parse_args()
    vote = load_vote()
    try:
        if args.traces:
            with args.traces.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            relevant = [r for r in rows if r["case_id"] == args.case and r["nature"] == args.nature]
            if not relevant:
                raise ValueError("No rows for this case and nature.")
            refs = {int(r["reference"]) for r in relevant if r.get("reference") not in {None, ""}}
            if len(refs) > 1:
                raise ValueError("Conflicting references: check the experiment before voting.")
            result = evaluate(vote, proposals_for(rows, args.case, args.nature), next(iter(refs), None))
            print(json.dumps({"case": args.case, "nature": args.nature, "n": 3, "k": 2, **result}))
        else:
            # Synthetic values in cents. These are not results on the shop data.
            for name, values, reference in [
                ("agreement", [100, 100, 120], 100),
                ("disagreement", [100, 110, 120], 100),
                ("unavailable", [100, None, None], 100),
                ("wrong consensus", [0, 0, 100], 100),
            ]:
                proposals = [SimpleNamespace(provider=p, model_requested=m, value=v,
                                             verdict="executed" if v is not None else "error")
                             for (p, m), v in zip(PANEL, values)]
                print(json.dumps({"example": name, "nature": "simulation", "n": 3, "k": 2,
                                  **evaluate(vote, proposals, reference)}))
    except (NotImplementedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
