#!/usr/bin/env python3
"""TD 2 and TD 3: read the decisions of a routing rule, then adapt it to your own.

Adapted by Pair C (DIA 3, Group 2) to the sub-group routing rule (reports/td2.md, section 4).

No API call, no key. The only input is the local TD 1 trace file (traces-td1.csv):
eligibility is recomputed from it at start-up, so every decision cites the TD 1 cells
that justify it. The supplied version of this file is kept in git history
(commit before "TD2 Pair C") and its output in pair-c/simulator-before.jsonl.

Costs are USD excluding tax per request, for a fixed token envelope of 641 input and
1024 output tokens (TD 1 mean prompt of gpt-oss-120b, and the max_completion_tokens cap),
priced with the portfolio file portefeuille-modeles-2026-09-28.csv.
Quota availability is supplied as a scenario, not measured from a provider.
"""
import argparse
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TRACES = os.path.join(HERE, "traces-td1.csv")

# Question families of TD 1 (questions-td1.json "type" field).
# A combination inherits the components listed in COMPONENTS.
FAMILIES = {
    "F1": ["C01", "C04", "C05", "C06", "C07", "C20"],   # period [start, end)
    "F2": ["C02", "C08", "C09", "C11"],                 # completed age at a reference date
    "F2b": ["C10"],                                     # age at the order date
    "F3": ["C03", "C12", "C13", "C14"],                 # product list (C03, C13, C14 also bound a period)
    "F1+F2": ["C15"],
    "F2+F3": ["C16"],
    "F1+F2+F3": ["C17", "C19"],
    "F1+F2b": ["C18"],
}
COMPONENTS = {f: f.split("+") for f in FAMILIES}

ENVELOPE_IN, ENVELOPE_OUT = 641, 1024


def per_request_usd(input_usd_m, output_usd_m):
    return round((ENVELOPE_IN * input_usd_m + ENVELOPE_OUT * output_usd_m) / 1e6, 6)


# Portfolio routes. "trace_model" links a route to the TD 1 cells measured for that model.
# preference: tie-break among equal-cost routes; small models first so that gpt-oss-120b,
# the only model correct on every family, keeps its Groq quota for F2 and combinations.
RESOURCES = [
    {"id": "qwen3.8-27b#groq", "trace_model": "groq:qwen/qwen3.8-27b", "access": "free",
     "available": True, "cash": 0.0, "allocation": 0.0, "reset_minutes": None, "preference": 1},
    {"id": "gpt-oss-20b#groq", "trace_model": "groq:openai/gpt-oss-20b", "access": "free",
     "available": True, "cash": 0.0, "allocation": 0.0, "reset_minutes": None, "preference": 2},
    {"id": "north-mini-code:free#openrouter", "trace_model": "openrouter:cohere/north-mini-code:free",
     "access": "free", "available": True, "cash": 0.0, "allocation": 0.0, "reset_minutes": None,
     "preference": 3},
    {"id": "dots-3-note-preview:free#openrouter",
     "trace_model": "openrouter:dots-studio/dots-3-note-preview:free", "access": "free",
     "available": True, "cash": 0.0, "allocation": 0.0, "reset_minutes": None, "preference": 4},
    {"id": "gpt-oss-120b#groq", "trace_model": "groq:openai/gpt-oss-120b", "access": "free",
     "available": True, "cash": 0.0, "allocation": 0.0, "reset_minutes": None, "preference": 5},
    # Same weights as the Groq route, paid on OpenRouter (portfolio G4: 0.15 / 0.60 USD per M).
    # TD 1 cells were measured on the Groq route, so this route never runs without a check.
    {"id": "gpt-oss-120b#openrouter", "trace_model": "groq:openai/gpt-oss-120b", "access": "tokens",
     "available": True, "cash": per_request_usd(0.15, 0.60), "allocation": per_request_usd(0.15, 0.60),
     "reset_minutes": None, "preference": 6, "measured_on_other_route": True},
    # Retained subscription in the portfolio (G3, 0.2 / 1.2 USD per M list price), but no TD 1 cell:
    # it stays ineligible until a TD 1-style batch measures it.
    {"id": "gpt-5.6-luna#codex", "trace_model": None, "access": "subscription",
     "available": True, "cash": 0.0, "allocation": per_request_usd(0.2, 1.2),
     "reset_minutes": None, "preference": 7},
]


def load_td1(path=TRACES):
    """Last attempt per (provider, model, case) -> verdict. Same rule as Pairs A and B."""
    last = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = (f"{row['provider']}:{row['model_requested']}", row["case_id"])
            if key not in last or int(row["attempts"]) >= int(last[key]["attempts"]):
                last[key] = row
    return {key: row["verdict"] for key, row in last.items()}


TD1 = load_td1()


def tally(trace_model, family):
    """Exact TD 1 ratio on the family's own cells: (correct, cases, failing cells)."""
    cells = FAMILIES[family]
    verdicts = {c: TD1.get((trace_model, c), "missing") for c in cells}
    bad = {c: v for c, v in verdicts.items() if v != "correct"}
    return len(cells) - len(bad), len(cells), bad


def evidence(resource, family):
    """Eligibility of a route for a family, with the TD 1 cells behind it.

    Eligible only if the model is correct on 100 % of the family's cells AND of each
    component family's cells (a combination inherits the failures of its parts).
    A 429 (not_executed) counts as a miss: 100 % means correct / cases, not / executed.
    """
    if resource["trace_model"] is None:
        return False, f"{resource['id']}: no TD 1 cell"
    if family not in FAMILIES:
        return False, f"{resource['id']}: family {family} has no TD 1 cell"
    parts, ok = [], True
    for fam in dict.fromkeys([family] + COMPONENTS[family]):
        good, total, bad = tally(resource["trace_model"], fam)
        ok = ok and not bad
        detail = ", ".join(f"{c} {v}" for c, v in bad.items())
        parts.append(f"{fam} {good}/{total}" + (f" ({detail})" if detail else
                                                 f" ({','.join(FAMILIES[fam])} correct)"))
    return ok, f"{resource['id']}: " + "; ".join(parts)


def checks_for(request, resource, panel=()):
    """Checking tier from the cost of an error (use) and the TD 1 evidence of the family.

    panel: eligible free routes ordered by preference, chosen route first (quorum members).
    """
    use, family = request["use"], request["family"]
    simple = family in ("F1", "F3")  # every TD 1 model correct on every executed cell
    if use == "dashboard":
        if resource["access"] == "free" and not resource.get("measured_on_other_route"):
            check = "none (single free model at 100 % on the family in TD 1, low-stakes dashboard)"
            return check if simple else check + " + zero-value guard (C09: empty filters return 0)"
        return "deterministic reference query (route not measured as such in TD 1)"
    if use == "customer":
        if simple:
            return f"2-of-3 quorum ({', '.join(panel[:3])}; all 100 % on {family} in TD 1)"
        return ("deterministic reference query; abstain + human review on mismatch "
                "(2-of-3 panel published a wrong 0 on C09, 3-of-5 abstained on C09/C10)")
    # payout
    if simple:
        return (f"3-of-5 quorum ({', '.join(panel[:5])}) AND deterministic reference query; "
                "human sign-off on any mismatch")
    return "deterministic reference query AND human sign-off; abstain on any mismatch"


def choose(request, resources):
    """Sub-group routing rule, deterministic, with a reason that cites TD 1 cells.

    Order kept from the supplied version: included capacity (cash == 0) first, then
    deferral to a route whose refill falls before the deadline, then paid tokens within
    budget, then abstention. At wake-up, availability must be measured again.
    """
    family = request["family"]
    judged = [(r, *evidence(r, family)) for r in resources]
    eligible = [r for r, ok, _ in judged if ok]
    excluded = "; ".join(why for _, ok, why in judged if not ok)
    base = {"family": family, "use": request["use"]}

    def decide(action, chosen, why, **extra):
        cash = chosen["cash"] if (chosen and action == "run") else 0
        panel = [chosen["id"]] + [r["id"] for r in sorted(eligible, key=lambda r: r["preference"])
                                  if r is not chosen and r["available"] and r["cash"] == 0] if chosen else []
        out = {**base, "action": action, "resource": chosen["id"] if chosen else None, "cash": cash,
               "checks": checks_for(request, chosen, panel) if chosen else "none (nothing published)",
               "reason": why, **extra}
        out["reason"] += f" | excluded: {excluded}" if excluded else ""
        return out

    def cites(r):
        return next(why for x, ok, why in judged if x is r)

    included = [r for r in eligible if r["available"] and r["cash"] == 0]
    if included:
        chosen = min(included, key=lambda r: (r["allocation"], r["preference"], r["id"]))
        skipped = [r["id"] for r in eligible if not r["available"]]
        why = f"cheapest eligible included route: {cites(chosen)}"
        if skipped:
            why += f"; first choice unavailable, next model taken (down: {', '.join(skipped)})"
        return decide("run", chosen, why)
    waiting = [r for r in eligible if not r["available"] and r["cash"] == 0
               and r["reset_minutes"] is not None
               and 0 < r["reset_minutes"] <= request["deadline_minutes"]]
    if waiting and request["can_wait"]:
        chosen = min(waiting, key=lambda r: (r["reset_minutes"], r["preference"]))
        return decide("defer", chosen, f"free route exhausted, refill before deadline; recheck "
                      f"availability at wake-up: {cites(chosen)}", wake_in_minutes=chosen["reset_minutes"])
    paid = [r for r in eligible if r["available"] and 0 < r["cash"] <= request["budget"]]
    if paid:
        chosen = min(paid, key=lambda r: (r["cash"], r["allocation"], r["preference"]))
        return decide("run", chosen, f"no free route in time, paid route within budget "
                      f"({chosen['cash']} <= {request['budget']} USD): {cites(chosen)}")
    if not eligible:
        why = f"no route at 100 % on {family} in TD 1"
    else:
        why = (f"eligible routes ({', '.join(r['id'] for r in eligible)}) unavailable, "
               f"no refill before deadline or no budget")
    return decide("abstain", None, why)


def exhaust(resource_ids, reset_minutes=60):
    return [dict(r, available=False, reset_minutes=reset_minutes) if r["id"] in resource_ids else dict(r)
            for r in RESOURCES]


def scenarios():
    base = {"family": "F1", "use": "dashboard", "can_wait": True,
            "deadline_minutes": 120, "budget": 0.30}
    # Groq daily quota of gpt-oss-120b exhausted (TD 1 saw 429s on the same Groq org, qwen C16-C20).
    groq120_down = exhaust({"gpt-oss-120b#groq"})
    return [
        ("simple", base, RESOURCES),
        ("complex", {**base, "family": "F2", "use": "customer"}, RESOURCES),
        ("deferrable", {**base, "family": "F2", "use": "customer"}, groq120_down),
        ("urgent", {**base, "family": "F2", "use": "customer", "can_wait": False,
                    "deadline_minutes": 5}, groq120_down),
        ("budget exhausted", {**base, "family": "F2", "use": "customer", "can_wait": False,
                              "budget": 0}, groq120_down),
        ("high impact", {**base, "family": "F2", "use": "payout"}, RESOURCES),
        ("unknown capability", {**base, "family": "F4"}, RESOURCES),
        # Added by Pair C.
        ("product for customer", {**base, "family": "F3", "use": "customer"}, RESOURCES),
        ("first model down", base, exhaust({"gpt-oss-20b#groq"}, reset_minutes=1)),
        ("age at order", {**base, "family": "F2b"}, RESOURCES),
        ("combined payout", {**base, "family": "F1+F2+F3", "use": "payout"}, RESOURCES),
    ]


def rates_table():
    """Exact TD 1 correct / cases per (model, family), straight from traces-td1.csv."""
    models = sorted({m for m, _ in TD1})
    return {m: {f: "{}/{}".format(*tally(m, f)[:2]) for f in FAMILIES} for m in models}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="show only the named scenario")
    parser.add_argument("--rates", action="store_true", help="print the TD 1 rate per family and exit")
    args = parser.parse_args()
    if args.rates:
        print(json.dumps({"nature": "real TD 1 traces", "families": FAMILIES,
                          "rates": rates_table()}, indent=1))
        return
    found = False
    for name, request, resources in scenarios():
        if args.scenario and name != args.scenario:
            continue
        found = True
        print(json.dumps({"scenario": name, "nature": "simulation", "request": request,
                          "result": choose(request, resources)}))
    if not found:
        parser.error("unknown scenario")


if __name__ == "__main__":
    main()
