#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-model orchestration skeleton - TD "Trustworthy generative AI" (ESILV).

Protocol of the practical work, the same for every sub-group: one SQLite base
(`data/boutique.sqlite`), the same twenty questions (`questions-td1.json`), and
one reference value per question that YOU compute without any model
(`reference-td1.csv`). For each question and each model, the program:

    1. sends the schema, the units, the conventions and the question, and asks
       for exactly one SQLite SELECT. The prompt is identical for every model:
       this is what makes the comparison between models fair;
    2. extracts the SQL from the answer and runs it in the read-only sandbox
       (`sandbox_sqlite.py`) on the base, one statement at a time;
    3. compares the value with your reference value for that question;
    4. writes one trace line: provider, model requested, model returned,
       question, prompt hash, SQL, value, reference, verdict, HTTP status,
       error, latency, tokens, native cost, attempts, date.

What this file provides, already working:
    - one client interface (`ClientLLM`) for every model, whatever the provider:
      a simulated client (`ClientSimule`, no key, no network) and an HTTP client
      (`ClientHTTP`) for Groq and OpenRouter, configured from
      `modeles-autorises.json`;
    - the rules of the batch: one request in flight at a time, a pause of three
      seconds between two requests, temperature 0, capped output, 45 seconds per
      request, one retry at most for a temporary error;
    - the sandboxed execution and the verdict by value comparison;
    - the trace table, saved after every answer (`traces-td1.jsonl`) and
      exported to CSV (`traces-td1.csv`); a cell (model, question) already
      verified is never replayed;
    - the rate per model, always given with its number of cases;
    - an offline replay of stored traces (`--replay`), for a session without
      network.

What YOU complete:
    - TD 1: nothing in this file. Your work is `reference-td1.csv`: the twenty
      reference queries and their values, computed without any model.
    - TD 2: `Orchestrateur.vote_k_sur_n(...)`, the consensus logic between
      several models; optionally the cascade and early stopping.

Standard library only. Python 3.10 or later.

    python3 skeleton-multi-llm-en.py --demo                      # three simulated models, no key, no network
    python3 skeleton-multi-llm-en.py --run                       # the required models on the twenty questions
    python3 skeleton-multi-llm-en.py --run --cases C01,C02       # a subset of questions
    python3 skeleton-multi-llm-en.py --run --models groq:openai/gpt-oss-120b openrouter:cohere/north-mini-code:free
    python3 skeleton-multi-llm-en.py --replay traces-reelles.jsonl   # offline: re-run the stored SQL of each trace
    python3 skeleton-multi-llm-en.py --rates                     # rates per model from traces-td1.jsonl
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent

# Layout of the student kit: every resource is next to this file. When the file
# runs from the repository instead of the kit, the same resources are looked up
# in the teacher folders (second candidate of each entry).
PROTOTYPE = HERE / "prototype-orchestrateur"
RESOURCES = {
    "access": (HERE / "check_access.py", HERE / "acces-modeles" / "check_access.py"),
    "sandbox": (HERE / "sandbox_sqlite.py", PROTOTYPE / "sandbox_sqlite.py"),
    "schema": (HERE / "schema.sql", PROTOTYPE / "schema.sql"),
    "db": (HERE / "data" / "boutique.sqlite", PROTOTYPE / "data" / "seed-20260925" / "boutique.sqlite"),
    "questions": (HERE / "questions-td1.json", HERE / "kit-td1" / "questions-td1.json"),
    "models": (HERE / "modeles-autorises.json", HERE / "acces-modeles" / "modeles-autorises.json"),
    "reference": (HERE / "reference-td1.csv", HERE / "kit-td1" / "reference-td1.csv"),
}


def resource(name: str) -> Path:
    for candidate in RESOURCES[name]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"{name}: none of {[str(c) for c in RESOURCES[name]]} exists")


sys.path.insert(0, str(resource("sandbox").parent))
import sandbox_sqlite  # noqa: E402  (read-only sandbox, next to this file in the kit)


# ==========================================================================
# 1. The prompt: identical for every model, conventions binding
# ==========================================================================

SYSTEM_PROMPT = ("You write SQLite queries for a small e-commerce database. Reply with exactly one "
                 "SQLite SELECT statement and nothing else: no explanation, no comments, no markdown "
                 "other than an optional ```sql fence.")

USER_PROMPT_TEMPLATE = """Schema (SQLite):
{schema}

Conventions (binding):
- product.price is the unit price in euro cents, excluding VAT (an integer). Revenue excluding VAT is SUM(quantity_product * price), an integer number of cents.
- orders holds order lines: one row per (order_id, product_id). All lines of an order share the same customer_id and the same date.
- orders.date and customers.insert_date are UTC timestamps stored as text 'YYYY-MM-DD HH:MM:SS'. customers.birth_date is a date stored as text 'YYYY-MM-DD'. Compare them as text or with SQLite date functions.
- A period "from S to E" is closed on the left and open on the right: date >= S AND date < E.
- A customer's age on a day D is the number of completed years: someone born on B is N years old on D when the N-th anniversary of B is on or before D and the (N+1)-th anniversary is after D. "Exactly 25 years old" means completed age 25 on that day, computed from month and day, never from the year difference alone.
- Unless the question says "at the time of the order", ages are computed on the reference date given in the question.
- The query must return exactly one row and one column named revenue_cents. When no order line matches, return 0 (use COALESCE), not NULL.
- Use only the tables above. One SELECT statement, nothing else.

Question: {question}"""


def build_prompt(schema: str, question: str) -> tuple[str, str, str]:
    """Return (system, user, sha256 of both). The hash goes into every trace line."""
    user = USER_PROMPT_TEMPLATE.format(schema=schema.strip(), question=question)
    digest = hashlib.sha256((SYSTEM_PROMPT + "\n" + user).encode("utf-8")).hexdigest()
    return SYSTEM_PROMPT, user, digest


# ==========================================================================
# 2. Rules of the batch (the same for every sub-group)
# ==========================================================================

PAUSE_BETWEEN_REQUESTS_S = 3.0      # one request in flight at a time, three seconds apart
REQUEST_TIMEOUT_S = 45.0            # per request
MAX_OUTPUT_TOKENS = 1024            # reasoning included when the provider counts it
RETRY_AFTER_MAX_S = 60.0            # a 429 is retried once when Retry-After fits in this delay
TEMPORARY_RETRY_DELAY_S = 5.0       # timeout or 5xx: one retry after this pause
TEMPORARY_STATUSES = {500, 502, 503, 504}
ACCESS_STATUSES = {400, 401, 402, 403, 404, 422}   # recorded, never retried
VERIFIED_VERDICTS = {"correct", "incorrect", "sql_invalid", "sql_rejected", "access_error"}
KEY_ENV = {"groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
USER_AGENT = "esilv-td-skeleton/2 (python-urllib)"


# ==========================================================================
# 3. Data structures
# ==========================================================================

@dataclass
class ReponseLLM:
    """What a model returns, normalised across providers. A missing counter stays None."""
    model_requested: str
    model_returned: Optional[str] = None
    text: str = ""
    http_status: Optional[int] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_reasoning: Optional[int] = None
    cost_native: Optional[float] = None
    attempts: int = 1
    retry_after_s: Optional[float] = None
    nature: str = "real"                 # real | simulation | replay


@dataclass
class Trace:
    """One line per call. The columns are those of the assignment (section 1, step 4)."""
    cell_id: str            # provider:model:question, stable: a verified cell is never replayed
    provider: str
    model_requested: str
    model_returned: str
    case_id: str
    question: str
    prompt_sha256: str
    sql: str
    value: str              # value returned by the SQL, empty when nothing ran
    reference: str          # your reference value, empty when you have not computed it yet
    verdict: str            # correct | incorrect | sql_invalid | sql_rejected | access_error | not_executed | "" (no reference)
    verdict_detail: str
    http_status: str
    error: str
    latency_ms: float
    tokens_prompt: str
    tokens_completion: str
    tokens_reasoning: str
    cost_native: str
    attempts: int
    date_utc: str
    nature: str             # real | simulation | replay: never mix them in a rate


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def blank(value) -> str:
    return "" if value is None else str(value)


# ==========================================================================
# 4. Abstraction layer: the interface common to all models
# ==========================================================================

class ClientLLM(ABC):
    """Single interface. A model = an object that answers a prompt.

    The orchestrator knows ONLY this interface: it does not know, and does not
    need to know, which provider answers behind it. That is what lets you add,
    remove or replace a model without touching the orchestrator.
    """
    paced = True    # HTTP clients wait between two requests; simulated ones do not

    def __init__(self, provider: str, model_id: str, optional: bool = False):
        self.provider, self.model_id, self.optional = provider, model_id, optional

    @property
    def name(self) -> str:
        return f"{self.provider}:{self.model_id}"

    @abstractmethod
    def _appeler(self, system: str, user: str, case_id: str) -> ReponseLLM:
        """One real call to the model. Implemented by each concrete client."""

    def interroger(self, system: str, user: str, case_id: str, *, on_answer=None,
                   previous_attempts: int = 0) -> ReponseLLM:
        """Save each attempt before waiting; at most two attempts across resumes."""
        first = self._appeler(system, user, case_id)
        first.attempts = previous_attempts + 1
        if on_answer:
            on_answer(first)
        delay = retry_delay(first)
        if delay is None or first.attempts >= 2:
            return first
        time.sleep(max(PAUSE_BETWEEN_REQUESTS_S, delay))
        second = self._appeler(system, user, case_id)
        second.attempts = 2
        if on_answer:
            on_answer(second)
        return second


def retry_delay(answer: ReponseLLM) -> Optional[float]:
    """Delay before the single retry allowed by the batch rules, None when no retry applies."""
    if answer.http_status == 200 or answer.error is None:
        return None
    if answer.http_status == 429:
        wait = answer.retry_after_s
        return wait if wait is not None and 0 <= wait <= RETRY_AFTER_MAX_S else None
    if answer.http_status in ACCESS_STATUSES:
        return None                                   # access error: recorded, not retried
    if answer.http_status in TEMPORARY_STATUSES or answer.http_status is None:
        return TEMPORARY_RETRY_DELAY_S                # 5xx, timeout, network
    return None


class ClientSimule(ClientLLM):
    """Simulated model: answers with no network and no key, deterministically.

    `answers` maps a question identifier (C01, C02, ...) to the text the model
    would return; unknown questions receive `default_answer`. It runs the whole
    chain (prompt, extraction, sandbox, verdict, trace) from the first minute.
    Its rows carry nature = simulation: they never enter a real rate.
    """
    paced = False

    def __init__(self, model_id: str, answers: Optional[dict] = None, default_answer: str = ""):
        super().__init__("simulated", model_id)
        self.answers = answers or {}
        self.default_answer = default_answer

    def _appeler(self, system: str, user: str, case_id: str) -> ReponseLLM:
        text = self.answers.get(case_id, self.default_answer)
        return ReponseLLM(model_requested=self.model_id, model_returned=self.model_id, text=text,
                          http_status=200, latency_ms=0.0, nature="simulation")


class ClientHTTP(ClientLLM):
    """Groq or OpenRouter over the chat/completions format, standard library only.

    `gate_config` and `parametres` come from modeles-autorises.json: base URL,
    name of the output-cap field, exact parameters measured in the pilot. The
    key is read from the environment (GROQ_API_KEY, OPENROUTER_API_KEY), never
    from a file of the kit.
    """

    def __init__(self, provider: str, model_id: str, gate_config: dict, parametres: Optional[dict] = None,
                 optional: bool = False, timeout: float = REQUEST_TIMEOUT_S):
        super().__init__(provider, model_id, optional)
        self.base_url = gate_config["base_url"].rstrip("/")
        self.output_field = gate_config["output_field"]
        self.parametres = dict(parametres or {})
        self.timeout = timeout
        self.key = os.environ.get(KEY_ENV[provider], "")

    def body(self, system: str, user: str) -> dict:
        body = {"model": self.model_id, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        params = dict(self.parametres)
        cap = int(params.pop(self.output_field, MAX_OUTPUT_TOKENS))
        body[self.output_field] = min(cap, MAX_OUTPUT_TOKENS)
        body.update(params)
        if self.provider == "openrouter":
            body["usage"] = {"include": True}                                   # native cost in usage.cost
            body["provider"] = {"max_price": {"prompt": 0, "completion": 0}}   # refuse any paid route
        return body

    def _appeler(self, system: str, user: str, case_id: str) -> ReponseLLM:
        answer = ReponseLLM(model_requested=self.model_id)
        if not self.key or self.key.isspace():
            answer.error = f"missing {KEY_ENV[self.provider]}"
            return answer
        request = urllib.request.Request(
            self.base_url + "/chat/completions", method="POST",
            data=json.dumps(self.body(system, user)).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json",
                     "Accept": "application/json", "User-Agent": USER_AGENT, "X-Title": "ESILV TD"})
        started = time.perf_counter()
        raw, headers = b"", {}
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                answer.http_status = response.status
        except urllib.error.HTTPError as error:
            raw = error.read() if error.fp else b""
            answer.http_status = error.code
            answer.error = f"HTTP {error.code}"
            headers = {k.lower(): v for k, v in error.headers.items()}
        except (TimeoutError, socket.timeout):
            answer.error = f"timeout after {self.timeout}s"
        except urllib.error.URLError as error:
            reason = str(getattr(error, "reason", error))
            answer.error = ("timeout: " if "timed out" in reason else "network: ") + reason[:160]
        except OSError as error:
            answer.error = f"network: {error}"[:200]
        answer.latency_ms = round((time.perf_counter() - started) * 1000, 1)
        answer.retry_after_s = parse_retry_after(headers)
        parse_completion(raw, answer)
        return answer


def parse_retry_after(headers: dict) -> Optional[float]:
    try:
        return float(headers.get("retry-after")) if headers.get("retry-after") else None
    except ValueError:
        return None


def _text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def parse_completion(raw: bytes, answer: ReponseLLM) -> None:
    """Fill the answer from a chat/completions body. Missing counters stay None."""
    try:
        body = json.loads(raw.decode("utf-8", "replace")) if raw else None
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return
    if isinstance(body.get("error"), dict):
        answer.error = (answer.error or "error") + ": " + str(body["error"].get("message"))[:200]
    answer.model_returned = body.get("model")
    choices = body.get("choices") or []
    if choices and isinstance(choices[0], dict):
        answer.text = _text((choices[0].get("message") or {}).get("content"))
    usage = body.get("usage") or {}
    if isinstance(usage, dict):
        answer.tokens_prompt = usage.get("prompt_tokens")
        answer.tokens_completion = usage.get("completion_tokens")
        details = usage.get("completion_tokens_details") or {}
        if isinstance(details, dict):
            answer.tokens_reasoning = details.get("reasoning_tokens")
        answer.cost_native = usage.get("cost")


def clients_from_config(config: dict, selection: Optional[list] = None, with_optional: bool = False) -> list:
    """Build the HTTP clients of modeles-autorises.json.

    `selection` restricts to explicit "provider:model" names; otherwise the
    required models, plus the optional one when `with_optional` is true.
    """
    gates = {"groq": config["groq"], "openrouter": config["openrouter"]}
    clients = []
    for model in config["modeles"]:
        name = f"{model['gate']}:{model['identifiant_exact']}"
        if selection is not None and name not in selection:
            continue
        if selection is None and model.get("optionnel") and not with_optional:
            continue
        clients.append(ClientHTTP(model["gate"], model["identifiant_exact"], gates[model["gate"]],
                                  model.get("parametres"), optional=bool(model.get("optionnel"))))
    return clients


# ==========================================================================
# 5. From the answer to the verdict: SQL extraction, sandbox, comparison
# ==========================================================================

def extract_sql(text: str) -> Optional[str]:
    """Keep the entire statement, including any forbidden second statement."""
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.S | re.I)
    fenced = re.fullmatch(r"\s*```(?:sql|sqlite)?\s*(.*?)```\s*", text, flags=re.S | re.I)
    if fenced:
        candidate = fenced.group(1)
    else:
        candidate = text
    candidate = candidate.strip()
    return candidate or None


def verdict_for(value, reference) -> tuple[str, str]:
    """Compare the value of the SQL with your reference. Strict equality of the numbers."""
    if reference is None or reference == "":
        return "", "no reference value in reference-td1.csv"
    if value is None:
        return "incorrect", "NULL instead of 0" if int(reference) == 0 else "NULL instead of a number"
    try:
        return ("correct", "") if float(value) == float(reference) else ("incorrect", "value differs")
    except (TypeError, ValueError):
        return "incorrect", "non-numeric value"


def judge(db_path: Path, sql: Optional[str], reference) -> dict:
    """Run the SQL in the sandbox and compare. Returns the verdict fields of the trace."""
    out = {"sql": sql or "", "value": "", "verdict": "sql_invalid", "verdict_detail": "no SQL statement found"}
    if not sql:
        return out
    result = sandbox_sqlite.execute_query(db_path, sql)
    if result["rejected"]:
        out.update(verdict="sql_rejected", verdict_detail=result["reason"] + " " + result["detail"])
    elif not result["ok"]:
        out.update(verdict="sql_invalid", verdict_detail=result["reason"] + " " + result["detail"])
    elif not result["shape_ok"]:
        out.update(verdict="sql_invalid", verdict_detail="shape: " + result["detail"])
    elif result["columns"] != ["revenue_cents"]:
        out.update(verdict="sql_invalid", verdict_detail="expected column revenue_cents")
    else:
        verdict, detail = verdict_for(result["value"], reference)
        out.update(value=blank(result["value"]), verdict=verdict, verdict_detail=detail)
    return out


# ==========================================================================
# 6. Trace collection: saved after every answer, exported to CSV
# ==========================================================================

class TableTraces:
    """Accumulates traces and saves each of them immediately in a JSONL state
    file. You trace BEFORE you optimise: with no trace, no decision is
    defensible. A cell whose verdict is verified is never replayed.
    """

    def __init__(self, state_path: Optional[Path] = None):
        self.lignes: list[Trace] = []
        self.state_path = state_path
        if state_path is not None and state_path.exists():
            names = {f.name for f in fields(Trace)}
            for line in state_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    self.lignes.append(Trace(**{k: v for k, v in record.items() if k in names}))

    def latest_by_cell(self) -> dict:
        return {(t.nature, t.cell_id): t for t in self.lignes}

    def latest(self, cell_id: str, nature: str = "real") -> Optional[Trace]:
        return self.latest_by_cell().get((nature, cell_id))

    def verified(self, cell_id: str, nature: str = "real") -> bool:
        trace = self.latest(cell_id, nature)
        return trace is not None and (trace.verdict in VERIFIED_VERDICTS or
                                      (trace.verdict == "" and trace.value != ""))

    def ajouter(self, trace: Trace) -> None:
        self.lignes.append(trace)
        if self.state_path is not None:
            with self.state_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(asdict(trace), ensure_ascii=False) + "\n")

    def exporter_csv(self, chemin: Path) -> None:
        colonnes = [f.name for f in fields(Trace)]
        with open(chemin, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=colonnes, lineterminator="\n")
            writer.writeheader()
            for trace in self.lignes:
                writer.writerow(asdict(trace))

    def taux_par_modele(self) -> dict:
        """Per model: number of cases, executed, correct, invalid, rejected, not executed.

        A rate is only meaningful with its number of cases: 18 correct out of 20
        cases, never "90 %" alone. Rows of different natures are kept apart.
        """
        table: dict = {}
        for trace in self.latest_by_cell().values():
            key = (trace.nature, f"{trace.provider}:{trace.model_requested}")
            row = table.setdefault(key, {"nature": trace.nature, "model": key[1], "cases": 0, "executed": 0,
                                         "correct": 0, "sql_invalid": 0, "sql_rejected": 0, "not_executed": 0,
                                         "unscored": 0})
            row["cases"] += 1
            if trace.verdict in ("correct", "incorrect"):
                row["executed"] += 1
                row["correct"] += trace.verdict == "correct"
            elif trace.verdict == "":
                row["executed"] += bool(trace.value != "")
                row["unscored"] += 1
            elif trace.verdict in ("sql_invalid", "sql_rejected"):
                row[trace.verdict] += 1
            else:
                row["not_executed"] += 1
        return dict(sorted(table.items()))


def print_rates(traces: TableTraces) -> None:
    rows = traces.taux_par_modele()
    if not rows:
        print("No trace yet.")
        return
    header = f"{'model':52} {'nature':10} {'cases':>5} {'run':>4} {'correct':>8} {'invalid':>7} {'rejected':>8} {'not run':>7}   accuracy"
    print(header)
    print("-" * len(header))
    for row in rows.values():
        accuracy = (f"{row['correct']}/{row['cases']} cases ({row['correct'] / row['cases']:.1%})"
                    if row["unscored"] == 0 else f"unscored ({row['unscored']} without reference)")
        print(f"{row['model']:52} {row['nature']:10} {row['cases']:>5} {row['executed']:>4} {row['correct']:>8} "
              f"{row['sql_invalid']:>7} {row['sql_rejected']:>8} {row['not_executed']:>7}   {accuracy}")


# ==========================================================================
# 7. Orchestrator: asks n models the same question and (over to you) makes them vote
# ==========================================================================

class Orchestrateur:
    """Coordinates several `ClientLLM` on the same questions, against your references."""

    def __init__(self, clients: list, db_path: Path, schema: str, references: dict, traces: TableTraces,
                 pause_s: float = PAUSE_BETWEEN_REQUESTS_S):
        self.clients, self.db_path, self.schema = clients, db_path, schema
        self.references, self.traces, self.pause_s = references, traces, pause_s

    def interroger_tous(self, case: dict) -> list:
        """Asks the SAME question to every model, runs each SQL, traces each call.

        Returns the trace of every model for this question. Already-working part.
        The judgement between models (the vote) is yours, in TD 2.
        """
        system, user, prompt_sha = build_prompt(self.schema, case["question"])
        reference = self.references.get(case["id"])
        out = []
        for client in self.clients:
            cell_id = f"{client.provider}:{client.model_id}:{case['id']}"
            nature = "simulation" if isinstance(client, ClientSimule) else "real"
            previous = self.traces.latest(cell_id, nature)
            if previous and (previous.prompt_sha256 != prompt_sha or previous.reference != blank(reference)):
                raise ValueError("Prompt or reference changed: use a new --state/--out for a new experiment, "
                                 "or --replay to score stored SQL offline.")
            if self.traces.verified(cell_id, nature) or (previous and previous.attempts >= 2):
                out.append(previous)
                continue

            def save_attempt(answer):
                trace = self.tracer(cell_id, client, case, prompt_sha, answer, reference)
                self.traces.ajouter(trace)
                print(f"  [{trace.verdict or 'unscored':12}] {client.name:52} value={trace.value or '-':>9} "
                      f"reference={trace.reference or '-':>9} {trace.latency_ms:7.0f} ms  {trace.error}", flush=True)

            client.interroger(system, user, case["id"], on_answer=save_attempt,
                               previous_attempts=previous.attempts if previous else 0)
            out.append(self.traces.latest(cell_id, nature))
            if client.paced:
                time.sleep(self.pause_s)
        return out

    def tracer(self, cell_id: str, client: ClientLLM, case: dict, prompt_sha: str, answer: ReponseLLM, reference) -> Trace:
        if answer.http_status == 200 and answer.error is None:
            fields_ = judge(self.db_path, extract_sql(answer.text), reference)
        elif answer.http_status in ACCESS_STATUSES:
            fields_ = {"sql": "", "value": "", "verdict": "access_error", "verdict_detail": answer.error or ""}
        else:
            fields_ = {"sql": "", "value": "", "verdict": "not_executed", "verdict_detail": answer.error or ""}
        return Trace(cell_id=cell_id, provider=client.provider, model_requested=answer.model_requested,
                     model_returned=blank(answer.model_returned), case_id=case["id"], question=case["question"],
                     prompt_sha256=prompt_sha, sql=fields_["sql"], value=fields_["value"], reference=blank(reference),
                     verdict=fields_["verdict"], verdict_detail=fields_["verdict_detail"],
                     http_status=blank(answer.http_status), error=blank(answer.error), latency_ms=answer.latency_ms,
                     tokens_prompt=blank(answer.tokens_prompt), tokens_completion=blank(answer.tokens_completion),
                     tokens_reasoning=blank(answer.tokens_reasoning), cost_native=blank(answer.cost_native),
                     attempts=answer.attempts, date_utc=utc_now(), nature=answer.nature)

    # ---------------------------------------------------------------------
    # TO COMPLETE (TD 2): k-of-n voting
    # ---------------------------------------------------------------------
    def vote_k_sur_n(self, traces_question: list, k: int):
        """TD 2 contract. `traces_question` holds the proposals of the panel for one
        question, as built by `atelier-vote.py`. Each proposal carries `provider`,
        `model_requested`, `value` (integer cents or None) and `verdict`
        (`executed` or `error`). No reference is passed in: the vote decides
        first, the comparison with your reference comes after.

          1. Only executed proposals that carry a value vote. An error or an
             unavailable member stays in n and casts no vote.
          2. k is a strict majority: n // 2 < k <= n, otherwise raise ValueError.
          3. Two proposals with the same (provider, model_requested) are refused
             with a ValueError: a duplicate is not a second vote.
          4. If a value reaches k votes, return
             {"consensus": True, "value": v, "votes": count, "models": [...]}
             where models lists "provider:model_requested" of the agreeing
             members.
          5. Otherwise return {"consensus": False, "value": None,
             "votes": largest count, "models": []}. Never invent a value.

        Seen in lecture 2: models trained on close data are wrong together, so a
        consensus is not a proof of correctness. Keep the panel to distinct model
        families, and look in your traces for a case where several models agree
        on a wrong value.
        """
        raise NotImplementedError("vote_k_sur_n: to implement in TD 2 (see the procedure in the docstring).")


# ==========================================================================
# 8. Inputs of the kit: questions, references, models
# ==========================================================================

def load_questions(path: Path, selection: Optional[str] = None) -> list:
    questions = json.loads(path.read_text(encoding="utf-8"))["questions"]
    if selection:
        wanted = [s.strip() for s in selection.split(",") if s.strip()]
        by_id = {q["id"]: q for q in questions}
        missing = [w for w in wanted if w not in by_id]
        if missing:
            raise SystemExit(f"unknown question identifiers: {missing}")
        questions = [by_id[w] for w in wanted]
    return questions


def load_references(path: Optional[Path]) -> dict:
    """reference-td1.csv: case_id, sql, revenue_cents. Empty values stay absent (not scored)."""
    references = {}
    if path is None or not path.exists():
        return references
    with open(path, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            value = (row.get("revenue_cents") or "").strip()
            if value != "":
                references[row["case_id"].strip()] = int(value)
    return references


def load_replay(path: Path) -> list:
    """Stored traces to re-execute offline: JSONL (one record per line) or CSV."""
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay(records: list, allowed: set, questions: list, db_path: Path, schema: str, references: dict, traces: TableTraces) -> None:
    """Re-run the SQL of stored traces on the local base, without network or key.

    Provider, model, latency, tokens, cost and date come from the stored trace
    (real measurements of the pilot); value and verdict are recomputed here,
    against YOUR references. Rows carry nature = replay.
    """
    by_id = {q["id"]: q for q in questions}
    # The pilot contains several lots. Keep the most recent record per model/case.
    latest = {}
    for record in sorted(records, key=lambda r: (r.get("date_utc") or "", int(r.get("lot") or 0))):
        key = (record.get("provider"), record.get("model_requested") or record.get("model"), record.get("case_id"))
        latest[key] = record
    for record in latest.values():
        provider, model = record.get("provider", ""), record.get("model_requested") or record.get("model", "")
        case_id = record.get("case_id", "")
        if f"{provider}:{model}" not in allowed or case_id not in by_id:
            continue
        cell_id = f"{provider}:{model}:{case_id}"
        if traces.verified(cell_id, "replay"):
            continue
        _, _, prompt_sha = build_prompt(schema, by_id[case_id]["question"])
        reference = references.get(case_id)
        sql = record.get("sql") or ""
        if sql:
            fields_ = judge(db_path, sql, reference)
        else:
            fields_ = {"sql": "", "value": "", "verdict": "not_executed", "verdict_detail": blank(record.get("status") or record.get("error"))}
        traces.ajouter(Trace(cell_id=cell_id, provider=provider, model_requested=model,
                             model_returned=blank(record.get("model_returned")), case_id=case_id,
                             question=by_id[case_id]["question"], prompt_sha256=prompt_sha, sql=fields_["sql"],
                             value=fields_["value"], reference=blank(reference), verdict=fields_["verdict"],
                             verdict_detail=fields_["verdict_detail"], http_status=blank(record.get("http_status")),
                             error=blank(record.get("error")), latency_ms=float(record.get("latency_ms") or 0),
                             tokens_prompt=blank(record.get("tokens_prompt")), tokens_completion=blank(record.get("tokens_completion")),
                             tokens_reasoning=blank(record.get("tokens_reasoning")), cost_native=blank(record.get("cost_native")),
                             attempts=int(record.get("attempts") or 1), date_utc=blank(record.get("date_utc")), nature="replay"))


# ==========================================================================
# 9. Demo: runs right now, with no API key
# ==========================================================================

TOTAL_REVENUE_SQL = ("SELECT COALESCE(SUM(o.quantity_product * p.price), 0) AS revenue_cents "
                     "FROM orders o JOIN product p ON p.product_id = o.product_id")
PRICE_ONLY_SQL = "SELECT SUM(p.price) AS revenue_cents FROM orders o JOIN product p ON p.product_id = o.product_id"


def demo_clients() -> list:
    """Three simulated models whose mistakes are visible: one ignores the filters
    of the question, one forgets the quantity, one does not answer with SQL and
    once tries to write. None of them contains a reference query."""
    return [
        ClientSimule("sim-no-filter", default_answer="```sql\n" + TOTAL_REVENUE_SQL + ";\n```"),
        ClientSimule("sim-price-only", default_answer=PRICE_ONLY_SQL),
        ClientSimule("sim-chatty", {"C02": "DELETE FROM orders; SELECT 1"},
                     default_answer="I think the revenue is about 12 euros for that period."),
    ]


# ==========================================================================
# 10. Command line
# ==========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Ask models for SQL, run it in the sandbox, compare, trace.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="three simulated models, no key, no network")
    mode.add_argument("--run", action="store_true", help="the authorised models of modeles-autorises.json")
    mode.add_argument("--replay", type=Path, metavar="FILE", help="re-run the SQL of stored traces (JSONL or CSV), offline")
    mode.add_argument("--rates", action="store_true", help="print the rates per model from the state file")
    parser.add_argument("--cases", default=None, help="comma-separated question identifiers, default: all twenty")
    parser.add_argument("--models", nargs="*", default=None, help="explicit provider:model names, default: the required models")
    parser.add_argument("--optional", action="store_true", help="include the optional model of the selection")
    parser.add_argument("--db", type=Path, default=None, help="SQLite base, default: data/boutique.sqlite")
    parser.add_argument("--questions", type=Path, default=None, help="default: questions-td1.json")
    parser.add_argument("--reference", type=Path, default=None, help="your references, default: reference-td1.csv")
    parser.add_argument("--models-config", type=Path, default=None, help="default: modeles-autorises.json")
    parser.add_argument("--state", type=Path, default=None, help="JSONL state file, default: traces-td1.jsonl (traces-demo.jsonl for --demo)")
    parser.add_argument("--out", type=Path, default=None, help="CSV export, default: traces-td1.csv (traces-demo.csv for --demo)")
    parser.add_argument("--pause", type=float, default=PAUSE_BETWEEN_REQUESTS_S, help="seconds between two requests")
    args = parser.parse_args()

    db_path = args.db or resource("db")
    schema = resource("schema").read_text(encoding="utf-8")
    questions = load_questions(args.questions or resource("questions"), args.cases)
    references = load_references(args.reference or (RESOURCES["reference"][0] if RESOURCES["reference"][0].exists() else None))
    config = json.loads((args.models_config or resource("models")).read_text(encoding="utf-8"))
    suffix = "demo" if args.demo else "replay" if args.replay else "td1"
    state_path = args.state or Path(f"traces-{suffix}.jsonl")
    out_path = args.out or Path(f"traces-{suffix}.csv")
    traces = TableTraces(state_path)

    if args.rates:
        print_rates(traces)
        return 0

    if args.run:
        sys.path.insert(0, str(resource("access").parent))
        from check_access import check_database
        failed = [detail for ok, detail in check_database(db_path) if not ok]
        if failed:
            raise SystemExit("\n".join(failed))
        missing_references = [q["id"] for q in questions if q["id"] not in references]
        if missing_references:
            raise SystemExit(f"Complete your reference values before calling models: {missing_references}")
        if args.pause < PAUSE_BETWEEN_REQUESTS_S:
            raise SystemExit("At least 3 seconds between requests are required.")

    if not references:
        print("No reference value found (reference-td1.csv): the traces will be unscored until you fill it in.\n")

    if args.replay:
        clients = clients_from_config(config, args.models, with_optional=True)
        allowed = {c.name for c in clients}
        replay(load_replay(args.replay), allowed, questions, db_path, schema, references, traces)
    else:
        clients = demo_clients() if args.demo else clients_from_config(config, args.models, args.optional)
        if not clients:
            raise SystemExit("no model selected")
        missing = sorted({KEY_ENV[c.provider] for c in clients if isinstance(c, ClientHTTP) and not c.key})
        if missing:
            raise SystemExit("missing environment variable(s): " + ", ".join(missing))
        orchestrateur = Orchestrateur(clients, db_path, schema, references, traces, pause_s=args.pause)
        for case in questions:                     # question-major order: a model's calls are spread over time
            print(f"{case['id']}  {case['question']}")
            orchestrateur.interroger_tous(case)

    traces.exporter_csv(out_path)
    print(f"\nTraces: {len(traces.lignes)} line(s) in {state_path}, all attempts exported to {out_path}\n")
    print_rates(traces)
    if args.demo:
        print("\nStep to complete in TD 2: k-of-n voting (Orchestrateur.vote_k_sur_n).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
