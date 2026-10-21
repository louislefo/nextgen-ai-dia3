#!/usr/bin/env python3
"""Check the distributed data without a network call or reference answers.

Run before and after an experiment and keep both JSON outputs:
    python3 verify-data.py > data-check-before.json
    python3 verify-data.py > data-check-after.json
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def main():
    kit = Path(__file__).resolve().parent
    data = kit / "data"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    expected = {"boutique.sqlite": manifest["sqlite_file_sha256"], **manifest["csv_sha256"]}
    results = []
    for name, wanted in expected.items():
        if Path(name).name != name:
            raise ValueError("Expected a filename inside data")
        actual = hashlib.sha256((data / name).read_bytes()).hexdigest()
        results.append({"file": "data/" + name, "sha256": actual, "ok": actual == wanted})
    schema_hash = hashlib.sha256((kit / "schema.sql").read_bytes()).hexdigest()
    results.append({"file": "schema.sql", "sha256": schema_hash, "ok": schema_hash == manifest["schema_sha256"]})
    with sqlite3.connect((data / "boutique.sqlite").as_uri() + "?mode=ro", uri=True) as con:
        integrity = con.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = con.execute("PRAGMA foreign_key_check").fetchall()
    ok = all(row["ok"] for row in results) and integrity == [("ok",)] and not foreign_keys
    print(json.dumps({"python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
                      "files": results, "sqlite_integrity_ok": integrity == [("ok",)],
                      "foreign_keys_ok": not foreign_keys, "ok": ok}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
