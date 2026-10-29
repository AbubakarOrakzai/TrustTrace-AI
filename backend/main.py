from __future__ import annotations

import hashlib
import json
import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from audit.ledger import AuditLedger
from evaluation_api import router as evaluation_router
from judge.providers import (
    GeminiJudge,
    JudgeEvaluation,
    JudgeUnavailableError,
    NebiusJudge,
    configured_judge,
)
from mock_tools import MockTools
from models.schemas import (
    Decision,
    ExecuteResponse,
    Finding,
    LayerResult,
    ToolCall,
    Verdict,
)
from policy.engine import PolicyEngine, load_rules
from runtime_config import data_path
from scenarios import SCENARIOS, make_tool_call

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("trusttrace")
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

ledger = AuditLedger(
    data_path(
        "TRUSTTRACE_DB_PATH",
        "trusttrace.db",
        BASE_DIR,
    ),
    data_path(
        "TRUSTTRACE_KEY_PATH",
        ".trusttrace-signing-key.pem",
        BASE_DIR,
    ),
)
policy_engine = PolicyEngine()
mock_tools = MockTools()
judge: GeminiJudge | NebiusJudge | None = configured_judge()


def policy_version() -> str:
    content = (BASE_DIR / "policy" / "rules.yaml").read_bytes()
    return hashlib.sha256(content).hexdigest()


def inspect_call(call: ToolCall, *, use_judge: bool = True) -> tuple[Verdict, Any]:
    policy_layer = policy_engine.evaluate(call)
    layers = [policy_layer]
    final_risk = policy_layer.risk_score
    decision: Decision = policy_layer.decision
    evaluation: JudgeEvaluation | None = None

    if use_judge and judge is not None and policy_layer.decision != "BLOCK":
        try:
            evaluation = judge.evaluate(call)
            judge_result = evaluation.result
            provider = evaluation.provider
            findings = []
            if evaluation.fallback_used:
                findings.append(
                    Finding(
                        rule_id="primary_evaluator_unavailable",
                        severity="MEDIUM",
                        message=(
                            "Nebius Token Factory was unavailable; Gemini evaluated "
                            "this call instead."
                        ),
                    )
                )
            judge_risk = judge_result.risk_score
            if (
                not judge_result.aligned_with_user_intent
                or judge_result.injection_suspected
            ):
                judge_risk = max(judge_risk, 0.7)
            if not judge_result.aligned_with_user_intent:
                findings.append(
                    Finding(
                        rule_id="intent_mismatch",
                        severity="HIGH",
                        message=(
                            f"{provider} judged the tool call misaligned with "
                            "the user "
                            "instruction."
                        ),
                        evidence=judge_result.rationale,
                    )
                )
            if judge_result.injection_suspected:
                findings.append(
                    Finding(
                        rule_id="judge_injection_suspected",
                        severity="HIGH",
                        message=(
                            f"{provider} suspected an instruction in "
                            "untrusted context."
                        ),
                        evidence=judge_result.rationale,
                        source_id=judge_result.injection_source_id,
                    )
                )
            judge_decision: Decision = (
                "BLOCK"
                if judge_risk >= 0.7
                else "REVIEW"
                if judge_risk >= 0.4
                else "ALLOW"
            )
            layers.append(
                LayerResult(
                    layer=f"L3 {provider} intent judge",
                    decision=judge_decision,
                    risk_score=judge_risk,
                    findings=findings,
                    latency_ms=evaluation.latency_ms,
                )
            )
            final_risk = max(final_risk, judge_risk)
            if final_risk >= 0.7:
                decision = "BLOCK"
            elif final_risk >= 0.4:
                decision = "REVIEW"
        except JudgeUnavailableError as error:
            layers.append(
                LayerResult(
                    layer=f"L3 {judge.provider} intent judge",
                    decision="BLOCK",
                    risk_score=1.0,
                    findings=[
                        Finding(
                            rule_id="evaluator_unavailable",
                            severity="CRITICAL",
                            message=(
                                f"{judge.provider} evaluator is unavailable or "
                                "returned invalid "
                                "output; the call was blocked."
                            ),
                        )
                    ],
                    latency_ms=error.latency_ms,
                    status="error",
                )
            )
            final_risk = 1.0
            decision = "BLOCK"

    verdict = Verdict(
        decision=decision,
        final_risk_score=final_risk,
        layers=layers,
        reason_summary=(
            "; ".join(finding.message for layer in layers for finding in layer.findings)
            if any(layer.findings for layer in layers)
            else "No configured deterministic policy indicators were detected."
        ),
        matched_controls=[
            control
            for layer in layers
            for finding in layer.findings
            for control in (
                ["SOC2:CC6.1", "AIUC-1:B-security"]
                if finding.severity in {"HIGH", "CRITICAL"}
                else ["SOC2:CC7.2"]
            )
        ],
    )
    model_id = (
        evaluation.model
        if evaluation is not None
        else judge.model
        if use_judge and judge is not None
        else "deterministic-only"
    )
    event = ledger.append(call, verdict, policy_version(), model_id=model_id)
    logger.info(
        json.dumps(
            {
                "event": "tool_call_evaluated",
                "event_id": event.event_id,
                "decision": verdict.decision,
                "tool_name": call.tool_name,
            }
        )
    )
    return verdict, event


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        rules = load_rules()
        logger.info(
            json.dumps(
                {
                    "event": "startup",
                    "policy_version": rules.get("version", "unknown"),
                    "evaluator": judge.provider
                    if judge and judge.configured
                    else "deterministic-only",
                }
            )
        )
    except Exception:
        logger.exception("Policy rules could not be loaded")
        raise
    yield


app = FastAPI(title="TrustTrace AI", version="0.1.0", lifespan=lifespan)
app.include_router(evaluation_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    judge_status = (
        "disabled"
        if judge is None
        else "ready"
        if judge.configured
        else "degraded_missing_api_key"
    )
    return {
        "status": "ok",
        "layers": {
            "schema_and_policy": "ready",
            "guardrails": "not_configured",
            "llm_judge": judge_status,
            "audit": "ready",
        },
        "judge_provider": judge.provider if judge else "none",
        "judge_primary_configured": bool(judge and judge.api_key),
        "judge_fallback_configured": bool(
            isinstance(judge, NebiusJudge)
            and judge.fallback
            and judge.fallback.configured
        ),
        "model_id": judge.model if judge and judge.configured else "deterministic-only",
    }


def validate_tool_call(payload: dict[str, Any]) -> ToolCall:
    try:
        return ToolCall.model_validate(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "decision": "BLOCK",
                "reason": "schema_violation",
                "errors": [
                    {
                        "location": [str(part) for part in item["loc"]],
                        "message": item["msg"],
                    }
                    for item in error.errors()
                ],
            },
        ) from error


@app.post("/v1/intercept")
def intercept(payload: dict[str, Any]) -> dict[str, Any]:
    call = validate_tool_call(payload)
    verdict, event = inspect_call(call)
    return {"tool_call_id": call.id, "verdict": verdict, "event_id": event.event_id}


@app.post("/v1/execute", response_model=ExecuteResponse)
def execute(payload: dict[str, Any]) -> ExecuteResponse:
    call = validate_tool_call(payload)
    verdict, _ = inspect_call(call)
    result = mock_tools.execute(call) if verdict.decision == "ALLOW" else None
    return ExecuteResponse(verdict=verdict, result=result)


@app.get("/v1/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return [
        {key: value for key, value in scenario.items() if key != "tool_call"}
        for scenario in SCENARIOS.values()
    ]


@app.post("/simulate/{scenario_id}")
@app.get("/simulate/{scenario_id}")
def simulate(scenario_id: str) -> dict[str, Any]:
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    call = make_tool_call(scenario_id)
    verdict, event = inspect_call(call, use_judge=False)
    return {
        "scenario": {
            key: value
            for key, value in SCENARIOS[scenario_id].items()
            if key != "tool_call"
        },
        "tool_call": call,
        "verdict": verdict,
        "event": event,
        "expected_matches": verdict.decision
        == SCENARIOS[scenario_id]["expected_decision"],
    }


@app.get("/v1/traces")
def traces() -> list[Any]:
    return ledger.list_events()


@app.get("/v1/traces/{event_id}")
def trace(event_id: str) -> Any:
    event = ledger.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return event


@app.get("/v1/audit/verify")
def verify_audit() -> dict[str, Any]:
    return ledger.verify()


@app.get("/v1/audit/report")
def audit_report(report_format: str = "json") -> dict[str, Any]:
    if report_format != "json":
        raise HTTPException(status_code=400, detail="Only JSON export is implemented")
    return ledger.report()


@app.post("/v1/simulate/run-all")
def run_all() -> dict[str, Any]:
    results = []
    for scenario_id, scenario in SCENARIOS.items():
        call = make_tool_call(scenario_id)
        verdict, _ = inspect_call(call, use_judge=False)
        results.append(
            {
                "scenario_id": scenario_id,
                "expected": scenario["expected_decision"],
                "actual": verdict.decision,
                "matched": verdict.decision == scenario["expected_decision"],
                "latency_ms": verdict.layers[0].latency_ms,
            }
        )
    matched = sum(result["matched"] for result in results)
    attacks = [result for result in results if result["expected"] != "ALLOW"]
    benign = [result for result in results if result["expected"] == "ALLOW"]
    detected = sum(result["actual"] != "ALLOW" for result in attacks)
    false_positives = sum(result["actual"] != "ALLOW" for result in benign)
    latencies = sorted(result["latency_ms"] for result in results)
    p95_index = max(0, math.ceil(0.95 * len(latencies)) - 1)
    return {
        "results": results,
        "scenario_accuracy": matched / len(results) if results else 1.0,
        "attack_block_rate": detected / len(attacks) if attacks else 1.0,
        "benign_false_positive_rate": (
            false_positives / len(benign) if benign else 0.0
        ),
        "p50_policy_latency_ms": (
            (latencies[(len(latencies) - 1) // 2] + latencies[len(latencies) // 2]) / 2
            if latencies
            else 0.0
        ),
        "p95_policy_latency_ms": latencies[p95_index] if latencies else 0.0,
    }
