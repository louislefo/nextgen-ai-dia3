#!/usr/bin/env python3
"""Check the environment of the ESILV TD: Python, the database fingerprint and
the access to the authorised models.

The script reads modeles-autorises.json next to itself, checks the SHA-256
fingerprint of the database against the manifest.json stored beside it, sends
one minimal request per authorised model (Groq or OpenRouter, exact identifier
and parameters of the selection) and prints an OK or KO verdict per line. A
screenshot of an all-OK run is the proof that the environment prerequisite is
met.

Usage:
    pip install requests
    export GROQ_API_KEY="gsk_..."
    export OPENROUTER_API_KEY="sk-or-v1-..."
    python3 check_access.py                 # database of the kit: data/boutique.sqlite
    python3 check_access.py --db PATH       # another copy of boutique.sqlite (manifest.json beside it)
    python3 check_access.py --no-network    # Python and database checks only

Only dependency: requests (plus the standard library). Python 3.10+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "modeles-autorises.json"
DATABASE_NAME = "boutique.sqlite"
DATABASE_CANDIDATES = (
    HERE / "data" / DATABASE_NAME,                                             # student kit
    HERE.parent / "prototype-orchestrateur" / "data" / "seed-20260925" / DATABASE_NAME,  # repository layout
)
CSV_NAMES = ("product.csv", "customers.csv", "orders.csv")
MIN_PYTHON = (3, 10)
PROBE_QUESTION = "Reply with the single word OK, nothing else."
PAUSE_BETWEEN_CALLS_S = 3
REQUEST_TIMEOUT_S = 45
DEFAULT_OUTPUT_CAP = 64

KEY_ENV = {"groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
USER_AGENT = "esilv-td-check-access/2"


def load_config() -> dict:
    if not CONFIG.exists():
        sys.exit(f"Missing {CONFIG.name} next to this script.")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short(fingerprint: str) -> str:
    return fingerprint[:8] + "..." + fingerprint[-8:]


# ---------------------------------------------------------------------------
# Local checks: Python, database fingerprint, CSV fingerprints
# ---------------------------------------------------------------------------
def check_python() -> tuple[bool, str]:
    version = sys.version_info[:3]
    text = ".".join(str(v) for v in version)
    wanted = ".".join(str(v) for v in MIN_PYTHON)
    if version[:2] >= MIN_PYTHON:
        return True, f"python {text} ({wanted} or later required)"
    return False, f"python {text} -> {wanted} or later required"


def locate_database(explicit: Path | None) -> Path | None:
    candidates = (explicit,) if explicit else DATABASE_CANDIDATES
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()
    return None


def check_database(db_path: Path | None) -> list[tuple[bool, str]]:
    """Return one (ok, message) per local check. The first line is the database fingerprint."""
    if db_path is None:
        wanted = ", ".join(str(c) for c in DATABASE_CANDIDATES)
        return [(False, f"database -> file missing (looked for {wanted}); get the kit again")]
    manifest_path = db_path.parent / "manifest.json"
    if not manifest_path.exists():
        return [(False, f"database {db_path.name} -> manifest.json missing beside it; get the kit again")]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        return [(False, f"database {db_path.name} -> manifest.json unreadable ({error})")]
    expected = str(manifest.get("sqlite_file_sha256", ""))
    seed = manifest.get("seed", "?")
    counts = manifest.get("counts", {})
    observed = sha256_file(db_path)
    results = []
    if not expected:
        results.append((False, f"database {db_path.name} -> manifest.json carries no sqlite_file_sha256"))
    elif observed == expected:
        results.append((True, f"database {db_path.name} -> sha256 {short(observed)}, identical to manifest.json (seed {seed})"))
    else:
        results.append((False, f"database {db_path.name} -> sha256 {short(observed)} differs from manifest.json "
                               f"(expected {short(expected)}); get the kit again, never modify the base"))

    # Row counts through sqlite3, read-only: proves the module works on this machine.
    try:
        conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            found = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("product", "customers", "orders")}
        finally:
            conn.close()
        wanted = {t: counts.get(t) for t in found}
        if all(wanted[t] is None or wanted[t] == found[t] for t in found):
            results.append((True, f"sqlite3 {sqlite3.sqlite_version} -> {found['product']} products, "
                                  f"{found['customers']} customers, {found['orders']} order lines, as in manifest.json"))
        else:
            results.append((False, f"sqlite3 -> row counts {found} differ from manifest.json {wanted}"))
    except sqlite3.Error as error:
        results.append((False, f"sqlite3 -> cannot read {db_path.name}: {error}"))

    # CSV files, when they travel with the base.
    csv_expected = manifest.get("csv_sha256", {})
    present = [name for name in CSV_NAMES if (db_path.parent / name).exists()]
    if present and csv_expected:
        wrong = [name for name in present if sha256_file(db_path.parent / name) != csv_expected.get(name)]
        if wrong:
            results.append((False, f"csv {', '.join(wrong)} -> fingerprint differs from manifest.json; get the kit again"))
        else:
            results.append((True, f"csv {', '.join(present)} -> fingerprints identical to manifest.json"))
    return results


# ---------------------------------------------------------------------------
# Network checks: one minimal request per authorised model
# ---------------------------------------------------------------------------
def build_request(gate_config: dict, gate: str, model: dict) -> tuple[str, dict, dict]:
    url = gate_config["base_url"].rstrip("/") + "/chat/completions"
    key = os.environ.get(KEY_ENV[gate], "")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    body = {
        "model": model["identifiant_exact"],
        "temperature": 0,
        "messages": [{"role": "user", "content": PROBE_QUESTION}],
    }
    # Reuse the exact parameters from the current model selection: the
    # output cap field name differs by gate (max_completion_tokens vs
    # max_tokens), the rest (reasoning switches) is gate- and model-specific.
    output_field = gate_config["output_field"]
    parametres = dict(model.get("parametres", {}))
    body[output_field] = parametres.pop(output_field, DEFAULT_OUTPUT_CAP)
    body.update(parametres)
    if gate == "openrouter":
        headers["X-Title"] = "esilv-td-check-access"
        body["usage"] = {"include": True}
        body["provider"] = {"max_price": {"prompt": 0, "completion": 0}}  # refuse any paid route
    return url, headers, body


def check_model(gate_config: dict, gate: str, model: dict) -> tuple[bool, str]:
    key = os.environ.get(KEY_ENV[gate], "")
    if not key or key.isspace():
        return False, f"missing {KEY_ENV[gate]}"

    import requests  # imported here so that the local checks run without it

    url, headers, body = build_request(gate_config, gate, model)
    try:
        response = requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT_S)
    except requests.exceptions.Timeout:
        return False, f"timeout after {REQUEST_TIMEOUT_S}s"
    except requests.exceptions.RequestException as error:
        return False, f"network error: {error}"

    if response.status_code != 200:
        return False, f"HTTP {response.status_code}: {response.text[:160]!r}"

    try:
        message = response.json()["choices"][0]["message"]
        text = (message.get("content") or "").strip()
        reasoning = (message.get("reasoning") or message.get("reasoning_content") or "").strip()
    except (ValueError, KeyError, IndexError, TypeError):
        return False, "response is not a usable chat/completions answer"

    if not text:
        hint = f" (reasoning only: {reasoning[:80]!r})" if reasoning else ""
        return False, f"empty response{hint} - output cap likely exhausted by reasoning"
    return True, text


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Python, the database fingerprint and the access to the authorised models.")
    parser.add_argument("--db", type=Path, default=None, help=f"path of {DATABASE_NAME} (manifest.json must be beside it)")
    parser.add_argument("--no-network", action="store_true", help="skip the model probes")
    args = parser.parse_args()

    config = load_config()
    gates = {"groq": config["groq"], "openrouter": config["openrouter"]}
    models = config["modeles"]

    local = [check_python()] + check_database(locate_database(args.db))
    for ok, detail in local:
        print(f"[{'OK' if ok else 'KO'}] {detail}")
    local_failed = [detail for ok, detail in local if not ok]

    results = []
    if args.no_network:
        print("[--] model probes skipped (--no-network)")
    else:
        try:
            import requests  # noqa: F401
        except ImportError:
            print("[KO] requests -> module missing: run `pip install requests` in your virtual environment")
            local_failed.append("requests missing")
            models = []
        for index, model in enumerate(models):
            gate = model["gate"]
            ok, detail = check_model(gates[gate], gate, model)
            results.append((model, ok))
            tag = "OK" if ok else "KO"
            optional = " (optional)" if model.get("optionnel") else ""
            print(f"[{tag}] {gate}/{model['identifiant_exact']}{optional} -> {detail}")
            if index < len(models) - 1:
                time.sleep(PAUSE_BETWEEN_CALLS_S)

    required_failed = [m for m, ok in results if not ok and not m.get("optionnel")]
    optional_failed = [m for m, ok in results if not ok and m.get("optionnel")]

    print()
    if results:
        print(f"{sum(ok for _, ok in results)}/{len(results)} models OK.")
    if optional_failed:
        names = ", ".join(m["identifiant_exact"] for m in optional_failed)
        print(f"Optional model(s) failed ({names}): prerequisite still met, but check before the session.")
    if local_failed:
        print("Local checks failed (Python or database): environment not ready.")
    if required_failed:
        names = ", ".join(m["identifiant_exact"] for m in required_failed)
        print(f"Required model(s) failed ({names}): environment not ready.")
    if local_failed or required_failed:
        return 1

    if args.no_network:
        print("Python and database OK. Run the script again without --no-network to check the models.")
        return 0
    print("Database and all required models OK: prerequisite met. Keep a screenshot of this output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
