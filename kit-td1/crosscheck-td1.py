"""Independent cross-check of reference-td1.csv, computed from the CSV files without any SQL.

Usage (from the repository root): python3 kit-td1/crosscheck-td1.py
"""
import csv
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

price = {r["product_id"]: int(r["price"]) for r in csv.DictReader(open(DATA / "product.csv"))}
birth = {r["customer_id"]: date.fromisoformat(r["birth_date"]) for r in csv.DictReader(open(DATA / "customers.csv"))}
lines = []
for r in csv.DictReader(open(DATA / "orders.csv")):
    lines.append((datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S"), r["customer_id"], r["product_id"], int(r["quantity_product"])))


def age(born: date, day: date) -> int:
    """Completed years: subtract one when this year's anniversary has not been reached yet."""
    return day.year - born.year - ((day.month, day.day) < (born.month, born.day))


def revenue(start=None, end=None, age_on=None, products=None) -> int:
    """start/end: 'YYYY-MM-DD' (period [start, end)); age_on: 'order' or 'YYYY-MM-DD' (exactly 25)."""
    total = 0
    for when, customer, product, qty in lines:
        if products and product not in products:
            continue
        if start and not (datetime.fromisoformat(start) <= when < datetime.fromisoformat(end)):
            continue
        if age_on:
            day = when.date() if age_on == "order" else date.fromisoformat(age_on)
            if age(birth[customer], day) != 25:
                continue
        total += qty * price[product]
    return total


EXPECTED = {
    "C01": revenue("2026-03-01", "2026-06-01"),
    "C02": revenue(age_on="2026-09-25"),
    "C03": revenue("2026-01-01", "2026-07-01", products={"a", "b", "c"}),
    "C04": revenue("2026-01-01", "2026-10-01"),
    "C05": revenue("2026-06-01", "2026-06-02"),
    "C06": revenue("2025-01-01", "2026-01-01"),
    "C07": revenue("2026-05-31", "2026-06-01"),
    "C08": revenue(age_on="2026-09-24"),
    "C09": revenue(age_on="2026-09-26"),
    "C10": revenue(age_on="order"),
    "C11": revenue(age_on="2026-12-01"),
    "C12": revenue(products={"a", "b", "c"}),
    "C13": revenue("2026-04-01", "2026-05-01", products={"a", "c"}),
    "C14": revenue("2026-10-01", "2026-12-01", products={"a", "b", "c"}),
    "C15": revenue("2026-03-01", "2026-06-01", age_on="2026-09-25"),
    "C16": revenue(age_on="2026-09-25", products={"a", "b", "c"}),
    "C17": revenue("2026-01-01", "2026-07-01", age_on="2026-09-25", products={"a", "b", "c"}),
    "C18": revenue("2026-05-01", "2026-06-01", age_on="order"),
    "C19": revenue("2026-09-01", "2026-10-01", age_on="2026-09-25", products={"d"}),
    "C20": revenue("2026-06-01", "2026-09-01"),
}

ok = True
for row in csv.DictReader(open(HERE.parent / "reference-td1.csv")):
    cid, ref = row["case_id"], row["revenue_cents"]
    same = ref != "" and int(ref) == EXPECTED[cid]
    ok &= same
    print(f"{cid}  csv={ref:>9}  python={EXPECTED[cid]:>9}  {'OK' if same else 'MISMATCH'}")
print("All references confirmed." if ok else "Some references differ.")
