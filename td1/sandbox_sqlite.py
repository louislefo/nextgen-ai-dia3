#!/usr/bin/env python3
"""Read-only SQLite sandbox for model-generated queries.

Every query produced by a model runs through `execute_query`:
    - the file is opened read-only (URI mode=ro) and `PRAGMA query_only = 1` is set;
    - an authorizer allows only SELECT, reads of the three tables and a short list
      of scalar and aggregate functions; ATTACH, PRAGMA, writes, schema reads,
      recursive CTEs and every other operation are denied;
    - only one statement is executed (sqlite3 refuses a second one);
    - the number of returned rows is capped;
    - a progress handler interrupts a query that does too much work or takes too long.
A rejected query returns a structured reason so that the trace stays usable.
Functions that do not exist in the Python build (readfile, writefile) fail as
"no such function" before the authorizer sees them; they are refused either way.

    python3 sandbox_sqlite.py --db data/seed-20260925/boutique.sqlite   # self-tests
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

ALLOWED_TABLES = {"product", "customers", "orders"}
ALLOWED_FUNCTIONS = {
    "sum", "total", "count", "min", "max", "avg", "coalesce", "ifnull", "nullif", "iif",
    "date", "datetime", "time", "strftime", "julianday", "unixepoch", "timediff",
    "abs", "round", "substr", "substring", "lower", "upper", "length", "trim", "ltrim",
    "rtrim", "instr", "replace", "printf", "format", "typeof", "sign", "ceil", "ceiling",
    "floor", "char", "unicode", "hex", "quote", "like", "glob", "group_concat",
    "string_agg", "concat", "concat_ws", "cast", "exists",
}
STEP_SIZE = 5_000          # VM instructions between two progress callbacks
MAX_STEPS = 4_000          # about 20 million instructions
MAX_SECONDS = 5.0
MAX_ROWS = 10


class Guard:
    """Progress handler: interrupts a query past the work or time budget."""

    def __init__(self, max_steps=MAX_STEPS, max_seconds=MAX_SECONDS):
        self.max_steps, self.max_seconds = max_steps, max_seconds
        self.steps, self.started = 0, time.monotonic()
        self.tripped = None

    def __call__(self):
        self.steps += 1
        if self.steps > self.max_steps:
            self.tripped = "work budget exceeded"
            return 1
        if time.monotonic() - self.started > self.max_seconds:
            self.tripped = "time budget exceeded"
            return 1
        return 0


def authorizer(action, arg1, arg2, db_name, trigger):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if arg1 in ALLOWED_TABLES else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK if (arg2 or "").lower() in ALLOWED_FUNCTIONS else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY   # ATTACH, DETACH, PRAGMA, INSERT, UPDATE, DELETE, CREATE, DROP, RECURSIVE...


def strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql.strip()


def open_readonly(db_path, guard):
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=1.0, isolation_level=None)
    conn.execute("PRAGMA query_only = 1")
    conn.set_progress_handler(guard, STEP_SIZE)
    conn.set_authorizer(authorizer)
    return conn


def classify_error(message, guard):
    text = message.lower()
    if "not authorized" in text or "is prohibited" in text:
        return "not_authorized"
    if text.startswith("no such "):
        return "runtime_error"
    if "interrupted" in text:
        return "interrupted:" + (guard.tripped or "unknown")
    if "one statement at a time" in text:
        return "multiple_statements"
    if "syntax error" in text or "incomplete input" in text or "unrecognized token" in text:
        return "syntax_error"
    if "attempt to write" in text or "readonly" in text:
        return "write_refused"
    return "runtime_error"


def execute_query(db_path, sql, *, max_rows=MAX_ROWS, max_steps=MAX_STEPS, max_seconds=MAX_SECONDS):
    """Run one SELECT under the sandbox. Never raises for a bad query."""
    started = time.perf_counter()
    result = {"ok": False, "rejected": False, "reason": "", "detail": "", "columns": [], "rows": [],
              "value": None, "shape_ok": False, "elapsed_ms": 0.0}
    cleaned = strip_comments(sql or "")
    cleaned = cleaned.rstrip().rstrip(";").strip()
    if not cleaned:
        result.update(rejected=True, reason="empty", detail="no SQL text")
        return result
    if not re.match(r"^(select|with)\b", cleaned, flags=re.I):
        result.update(rejected=True, reason="not_select", detail=cleaned[:80])
        return result
    guard = Guard(max_steps, max_seconds)
    conn = None
    try:
        conn = open_readonly(db_path, guard)
        cursor = conn.execute(cleaned)
        rows = cursor.fetchmany(max_rows + 1)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        if len(rows) > max_rows:
            result.update(rejected=True, reason="too_many_rows", detail=f"more than {max_rows} rows")
            return result
        result.update(ok=True, columns=columns, rows=[list(r) for r in rows])
        if len(rows) == 1 and len(columns) == 1:
            result.update(shape_ok=True, value=rows[0][0])
        else:
            result["detail"] = f"shape {len(rows)}x{len(columns)}, expected 1x1"
        return result
    except sqlite3.Error as error:
        reason = classify_error(str(error), guard)
        rejected = reason in {"not_authorized", "multiple_statements", "write_refused"} or reason.startswith("interrupted")
        result.update(rejected=rejected, reason=reason, detail=str(error)[:200])
        return result
    finally:
        if conn is not None:
            conn.close()
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


SELF_TESTS = [
    ("insert", "INSERT INTO product VALUES ('z', 1)", "not_select"),
    ("update", "UPDATE product SET price = 0", "not_select"),
    ("delete", "DELETE FROM orders", "not_select"),
    ("create", "CREATE TABLE t (x)", "not_select"),
    ("drop", "DROP TABLE orders", "not_select"),
    ("pragma", "PRAGMA writable_schema = 1", "not_select"),
    ("attach", "ATTACH DATABASE '/tmp/x.sqlite' AS x", "not_select"),
    ("write_inside_cte", "WITH t AS (SELECT 1) INSERT INTO product SELECT 'z', 1", "not_authorized"),
    ("select_then_write", "SELECT 1; DELETE FROM orders", "multiple_statements"),
    ("two_selects", "SELECT 1; SELECT 2", "multiple_statements"),
    ("schema_read", "SELECT sql FROM sqlite_master", "not_authorized"),
    ("schema_read_alias", "SELECT name FROM sqlite_schema", "not_authorized"),
    ("load_extension", "SELECT load_extension('/tmp/evil.so')", "not_authorized"),
    ("readfile", "SELECT readfile('/etc/passwd')", ("not_authorized", "runtime_error")),
    ("writefile", "SELECT writefile('/tmp/x', 'y')", ("not_authorized", "runtime_error")),
    ("random_function", "SELECT random()", "not_authorized"),
    ("recursive_cte", "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c", "not_authorized"),
    ("cartesian_explosion", "SELECT count(*) FROM orders a, orders b, orders c, orders d", "interrupted:work budget exceeded"),
    ("too_many_rows", "SELECT * FROM orders", "too_many_rows"),
    ("syntax_error", "SELECT FROM WHERE", "syntax_error"),
    ("unknown_column", "SELECT missing_column FROM orders", "runtime_error"),
    ("valid_scalar", "SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents FROM orders o JOIN product p ON p.product_id = o.product_id", "ok"),
    ("valid_with_cte", "WITH t AS (SELECT quantity_product * price AS amount FROM orders JOIN product USING (product_id)) SELECT COALESCE(SUM(amount), 0) FROM t", "ok"),
    ("valid_date_function", "SELECT count(*) FROM customers WHERE date(insert_date, '+1 day') >= '2025-06-01'", "ok"),
]


def self_tests(db_path):
    before = sha256_file(db_path)
    report = []
    for name, sql, expected in SELF_TESTS:
        r = execute_query(db_path, sql)
        observed = "ok" if r["ok"] else r["reason"]
        accepted = expected if isinstance(expected, tuple) else (expected,)
        report.append({"test": name, "sql": sql, "expected": " | ".join(accepted), "observed": observed,
                       "detail": r["detail"], "elapsed_ms": r["elapsed_ms"], "pass": observed in accepted})
    after = sha256_file(db_path)
    report.append({"test": "database_unchanged", "sql": "", "expected": before[:16], "observed": after[:16],
                   "detail": "sha256 of the SQLite file before and after the tests", "elapsed_ms": 0, "pass": before == after})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="JSON report of the self-tests")
    args = parser.parse_args()
    report = self_tests(args.db)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"db": str(args.db), "sqlite_version": sqlite3.sqlite_version,
                                        "tests": report}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [t["test"] for t in report if not t["pass"]]
    for t in report:
        print(("PASS " if t["pass"] else "FAIL ") + t["test"].ljust(24) + " " + t["observed"] + ("" if t["pass"] else "  expected " + t["expected"]))
    print(json.dumps({"tests": len(report), "failed": failed}))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
