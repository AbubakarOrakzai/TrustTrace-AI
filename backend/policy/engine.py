from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import sqlglot
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlglot import exp

from models.schemas import Decision, Finding, LayerResult, ToolCall

RULES_PATH = Path(__file__).with_name("rules.yaml")


class StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailArguments(StrictArguments):
    recipient: str = Field(min_length=3, max_length=320)
    subject: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=10000)


class QueryArguments(StrictArguments):
    sql: str = Field(min_length=1, max_length=10000)


class CRMUpdate(StrictArguments):
    record_id: str = Field(min_length=1, max_length=200)
    owner: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class CRMArguments(StrictArguments):
    updates: list[CRMUpdate] = Field(min_length=1, max_length=100)


class FileArguments(StrictArguments):
    path: str = Field(min_length=1, max_length=1000)


class HTTPArguments(StrictArguments):
    url: str = Field(min_length=8, max_length=4000)
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE)$")
    body: str = Field(default="", max_length=10000)


ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "send_email": EmailArguments,
    "query_db": QueryArguments,
    "update_crm": CRMArguments,
    "read_file": FileArguments,
    "http_request": HTTPArguments,
}


def load_rules() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as file:
        rules = yaml.safe_load(file)
    if not isinstance(rules, dict):
        raise ValueError("Policy rules must be a YAML mapping")
    return rules


def _decision(score: float) -> Decision:
    if score >= 0.7:
        return "BLOCK"
    if score >= 0.4:
        return "REVIEW"
    return "ALLOW"


class PolicyEngine:
    def __init__(self) -> None:
        self._email_times: dict[str, list[datetime]] = {}

    def evaluate(self, call: ToolCall) -> LayerResult:
        started = time.perf_counter()
        rules = load_rules()
        findings: list[Finding] = []
        risk = 0.0
        external = False

        try:
            validated = ARGUMENT_MODELS[call.tool_name].model_validate(call.arguments)
            arguments = validated.model_dump()
        except (ValidationError, KeyError) as error:
            finding = Finding(
                rule_id="schema_violation",
                severity="CRITICAL",
                message="Tool arguments do not match the strict tool schema.",
                evidence=type(error).__name__,
            )
            return LayerResult(
                layer="L0+L1 policy",
                decision="BLOCK",
                risk_score=1.0,
                findings=[finding],
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        serialized = json.dumps(arguments, ensure_ascii=True, sort_keys=True)
        sensitive = any(
            re.search(pattern, serialized) for pattern in rules["sensitive_patterns"]
        )
        if sensitive:
            risk = max(risk, 0.65)
            findings.append(
                Finding(
                    rule_id="sensitive_data",
                    severity="HIGH",
                    message="Arguments contain a sensitive-data indicator.",
                    evidence=(
                        "Matched a configured pattern; values are not copied "
                        "to the finding."
                    ),
                )
            )

        destination = ""
        if call.tool_name == "send_email":
            destination = (
                str(arguments["recipient"]).rsplit("@", maxsplit=1)[-1].lower()
            )
            now = datetime.now(timezone.utc)
            recent = [
                sent_at
                for sent_at in self._email_times.get(call.session_id, [])
                if sent_at > now - timedelta(minutes=1)
            ]
            recent.append(now)
            self._email_times[call.session_id] = recent
            if len(recent) > int(rules["max_outbound_emails_per_minute"]):
                risk = max(risk, 0.5)
                findings.append(
                    Finding(
                        rule_id="email_rate_limit",
                        severity="MEDIUM",
                        message="Outbound email rate limit exceeded for this session.",
                    )
                )
        elif call.tool_name == "http_request":
            parsed_url = urlparse(str(arguments["url"]))
            destination = (parsed_url.hostname or "").lower()
            if parsed_url.scheme != "https":
                risk = max(risk, 0.7)
                findings.append(
                    Finding(
                        rule_id="insecure_http",
                        severity="HIGH",
                        message="HTTP tool calls must use HTTPS.",
                    )
                )

        allowed_domains = {str(domain).lower() for domain in rules["allowed_domains"]}
        if destination and destination not in allowed_domains:
            external = True
            risk = max(risk, 0.7)
            findings.append(
                Finding(
                    rule_id="unapproved_destination",
                    severity="HIGH",
                    message="Destination domain is not in the configured allowlist.",
                    evidence=destination,
                )
            )

        if external and sensitive:
            risk = 1.0
            findings.append(
                Finding(
                    rule_id="exfiltration",
                    severity="CRITICAL",
                    message=(
                        "Sensitive-data indicator is paired with an unapproved "
                        "destination."
                    ),
                )
            )

        if call.tool_name == "query_db":
            sql = str(arguments["sql"])
            try:
                statements = sqlglot.parse(sql, read="sqlite")
                if len(statements) != 1:
                    risk = 1.0
                    findings.append(
                        Finding(
                            rule_id="multiple_sql_statements",
                            severity="CRITICAL",
                            message="Exactly one SQL statement is permitted.",
                        )
                    )
                elif statements[0] is None:
                    risk = 1.0
                    findings.append(
                        Finding(
                            rule_id="invalid_sql",
                            severity="CRITICAL",
                            message="An empty SQL statement is blocked.",
                        )
                    )
                else:
                    statement = statements[0]
                    kind = statement.key.upper()
                    if kind not in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
                        risk = 1.0
                        findings.append(
                            Finding(
                                rule_id="dangerous_sql",
                                severity="CRITICAL",
                                message=(
                                    "Only data queries against the in-memory "
                                    "sandbox are permitted."
                                ),
                            )
                        )
                    where_clause = statement.find(exp.Where)
                    if kind in {"DELETE", "UPDATE"} and where_clause is None:
                        risk = 1.0
                        findings.append(
                            Finding(
                                rule_id="dangerous_sql",
                                severity="CRITICAL",
                                message="Destructive or unbounded SQL is blocked.",
                            )
                        )
                    restricted = {
                        str(name).lower() for name in rules["restricted_tables"]
                    }
                    accessed = {
                        table.name.lower() for table in statement.find_all(exp.Table)
                    }
                    if kind == "SELECT" and accessed.intersection(restricted):
                        risk = max(risk, 0.5)
                        findings.append(
                            Finding(
                                rule_id="restricted_table",
                                severity="HIGH",
                                message=(
                                    "SELECT references a restricted table and "
                                    "requires review."
                                ),
                            )
                        )
            except sqlglot.errors.ParseError:
                risk = 1.0
                findings.append(
                    Finding(
                        rule_id="invalid_sql",
                        severity="CRITICAL",
                        message="SQL could not be parsed and is blocked.",
                    )
                )

        if call.tool_name == "update_crm":
            count = len(arguments["updates"])
            if count > int(rules["max_crm_updates"]):
                risk = max(risk, 0.5)
                findings.append(
                    Finding(
                        rule_id="bulk_crm_update",
                        severity="HIGH",
                        message="CRM update batch exceeds the review threshold.",
                        evidence=f"{count} records",
                    )
                )

        if call.tool_name == "read_file":
            path = str(arguments["path"]).replace("\\", "/")
            if path.startswith("/") or ".." in path.split("/"):
                risk = 1.0
                findings.append(
                    Finding(
                        rule_id="path_traversal",
                        severity="CRITICAL",
                        message="File path escapes the allowed demo directory.",
                        evidence=path,
                    )
                )

        injection_patterns = rules["injection_patterns"]
        for source in call.context_sources:
            if any(
                re.search(pattern, source.excerpt) for pattern in injection_patterns
            ):
                risk = 1.0
                findings.append(
                    Finding(
                        rule_id="untrusted_context_instruction",
                        severity="CRITICAL",
                        message="Potential instruction in untrusted source context.",
                        evidence=source.source_id,
                        source_id=source.source_id,
                    )
                )

        decision = _decision(risk)
        return LayerResult(
            layer="L0+L1 deterministic policy",
            decision=decision,
            risk_score=risk,
            findings=findings,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
