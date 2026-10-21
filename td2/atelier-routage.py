#!/usr/bin/env python3
"""TD 2 and TD 3: read the decisions of a routing rule, then adapt it to your own.

Synthetic resources, no API call, no key.

Costs are fictional USD excluding tax per request, with a fixed token envelope.
Capability levels 1/2/3 describe eligibility for this exercise, not model IQ.
Quota availability is supplied as a scenario, not measured from a provider.
"""
import argparse
import json

RESOURCES = [
    {"id": "small-free", "level": 1, "access": "free", "available": True,
     "cash": 0.0, "allocation": 0.0, "reset_minutes": None},
    {"id": "senior-subscription", "level": 3, "access": "subscription", "available": True,
     "cash": 0.0, "allocation": 0.04, "reset_minutes": None},
    {"id": "senior-api", "level": 3, "access": "tokens", "available": True,
     "cash": 0.30, "allocation": 0.30, "reset_minutes": None},
]


def choose(request, resources):
    """A deterministic routing policy, with a reason the user can inspect.

    Already paid capacity is preferred before new spending. A nonurgent request
    can wait for included capacity. At wake-up, availability must be measured
    again: reaching a reset time does not prove that capacity is available.
    """
    eligible = [r for r in resources if r["level"] >= request["difficulty"]]
    checks = "source verification and human review" if request["high_impact"] else "read-only execution and value check"
    included = [r for r in eligible if r["available"] and r["cash"] == 0]
    if included:
        chosen = min(included, key=lambda r: (r["allocation"], r["level"], r["id"]))
        return {"action": "run", "resource": chosen["id"], "cash": 0,
                "checks": checks, "reason": "eligible included capacity"}
    waiting = [r for r in eligible if not r["available"] and r["cash"] == 0
               and r["reset_minutes"] is not None
               and 0 < r["reset_minutes"] <= request["deadline_minutes"]]
    if waiting and request["can_wait"]:
        chosen = min(waiting, key=lambda r: r["reset_minutes"])
        return {"action": "defer", "resource": chosen["id"], "cash": 0,
                "checks": checks, "reason": "recheck availability at wake-up",
                "wake_in_minutes": chosen["reset_minutes"]}
    paid = [r for r in eligible if r["available"] and r["cash"] <= request["budget"]]
    if paid:
        chosen = min(paid, key=lambda r: (r["cash"], r["allocation"], r["id"]))
        return {"action": "run", "resource": chosen["id"], "cash": chosen["cash"],
                "checks": checks, "reason": "available route within the authorised budget"}
    return {"action": "abstain", "resource": None, "cash": 0,
            "checks": checks, "reason": "no eligible resource within deadline and budget"}


def scenarios():
    base = {"difficulty": 1, "high_impact": False, "can_wait": True,
            "deadline_minutes": 120, "budget": 0.30}
    exhausted = [dict(r, available=False, reset_minutes=60) if r["access"] == "subscription" else dict(r)
                 for r in RESOURCES]
    return [
        ("simple", base, RESOURCES),
        ("complex", {**base, "difficulty": 3}, RESOURCES),
        ("deferrable", {**base, "difficulty": 3}, exhausted),
        ("urgent", {**base, "difficulty": 3, "can_wait": False, "deadline_minutes": 5}, exhausted),
        ("budget exhausted", {**base, "difficulty": 3, "can_wait": False, "budget": 0}, exhausted),
        ("high impact", {**base, "difficulty": 3, "high_impact": True}, RESOURCES),
        ("unknown capability", {**base, "difficulty": 4}, RESOURCES),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="show only the named scenario")
    args = parser.parse_args()
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
