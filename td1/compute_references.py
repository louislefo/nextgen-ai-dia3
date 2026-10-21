"""
Compute and export all 20 reference SQL queries for TD 1.
Usage: python compute_references.py
"""
import sqlite3
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "boutique.sqlite"

QUERIES = {
    "C01": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2026-03-01 00:00:00' AND o.date < '2026-06-01 00:00:00';",
    "C02": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE date(c.birth_date, '+25 years') <= '2026-09-25' AND date(c.birth_date, '+26 years') > '2026-09-25';",
    "C03": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE p.product_id IN ('a', 'b', 'c') AND o.date >= '2026-01-01 00:00:00' AND o.date < '2026-07-01 00:00:00';",
    "C04": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2026-01-01 00:00:00' AND o.date < '2026-10-01 00:00:00';",
    "C05": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2026-06-01 00:00:00' AND o.date < '2026-06-02 00:00:00';",
    "C06": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2025-01-01 00:00:00' AND o.date < '2026-01-01 00:00:00';",
    "C07": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2026-05-31 00:00:00' AND o.date < '2026-06-01 00:00:00';",
    "C08": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE date(c.birth_date, '+25 years') <= '2026-09-24' AND date(c.birth_date, '+26 years') > '2026-09-24';",
    "C09": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE date(c.birth_date, '+25 years') <= '2026-09-26' AND date(c.birth_date, '+26 years') > '2026-09-26';",
    "C10": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE date(c.birth_date, '+25 years') <= date(o.date) AND date(c.birth_date, '+26 years') > date(o.date);",
    "C11": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE date(c.birth_date, '+25 years') <= '2026-12-01' AND date(c.birth_date, '+26 years') > '2026-12-01';",
    "C12": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE p.product_id IN ('a', 'b', 'c');",
    "C13": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE p.product_id IN ('a', 'c') AND o.date >= '2026-04-01 00:00:00' AND o.date < '2026-05-01 00:00:00';",
    "C14": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE p.product_id IN ('a', 'b', 'c') AND o.date >= '2026-10-01 00:00:00' AND o.date < '2026-12-01 00:00:00';",
    "C15": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE o.date >= '2026-03-01 00:00:00' AND o.date < '2026-06-01 00:00:00' AND date(c.birth_date, '+25 years') <= '2026-09-25' AND date(c.birth_date, '+26 years') > '2026-09-25';",
    "C16": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE p.product_id IN ('a', 'b', 'c') AND date(c.birth_date, '+25 years') <= '2026-09-25' AND date(c.birth_date, '+26 years') > '2026-09-25';",
    "C17": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE p.product_id IN ('a', 'b', 'c') AND o.date >= '2026-01-01 00:00:00' AND o.date < '2026-07-01 00:00:00' AND date(c.birth_date, '+25 years') <= '2026-09-25' AND date(c.birth_date, '+26 years') > '2026-09-25';",
    "C18": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE o.date >= '2026-05-01 00:00:00' AND o.date < '2026-06-01 00:00:00' AND date(c.birth_date, '+25 years') <= date(o.date) AND date(c.birth_date, '+26 years') > date(o.date);",
    "C19": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id JOIN customers c ON o.customer_id = c.customer_id WHERE p.product_id = 'd' AND o.date >= '2026-09-01 00:00:00' AND o.date < '2026-10-01 00:00:00' AND date(c.birth_date, '+25 years') <= '2026-09-25' AND date(c.birth_date, '+26 years') > '2026-09-25';",
    "C20": "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON o.product_id = p.product_id WHERE o.date >= '2026-06-01 00:00:00' AND o.date < '2026-09-01 00:00:00';"
}

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    rows = [["case_id", "sql", "revenue_cents"]]
    print("Executing all 20 reference queries on boutique.sqlite:\n")
    for case_id in sorted(QUERIES.keys()):
        sql = QUERIES[case_id]
        cur.execute(sql)
        val = cur.fetchone()[0]
        rows.append([case_id, sql, val])
        print(f"[{case_id}] {val:>10} cents  ({val/100:>8.2f} EUR)")
    conn.close()

    # Write to reference-td1.csv
    for target in [HERE / "reference-td1.csv"]:
        if target.parent.exists():
            with open(target, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            print(f"\nSaved 20 references to: {target.name}")

if __name__ == "__main__":
    main()
