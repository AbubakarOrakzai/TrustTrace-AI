from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

ToolName = Literal["send_email", "query_db", "update_crm", "read_file", "http_request"]
Decision = Literal["ALLOW", "REVIEW", "BLOCK"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContextSource(StrictModel):
    source_id: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=80)
    content_hash: str = Field(min_length=1, max_length=128)
    excerpt: str = Field(default="", max_length=4000)


class ToolCall(StrictModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str = Field(default="demo-agent", min_length=1, max_length=200)
    session_id: str = Field(default="demo-session", min_length=1, max_length=200)
    tool_name: ToolName
    arguments: dict[str, Any]
    context_sources: list[ContextSource] = Field(default_factory=list)
    user_instruction: str = Field(default="", max_length=4000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Finding(StrictModel):
    rule_id: str
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message: str
    evidence: str = ""
    source_id: str | None = None


class LayerResult(StrictModel):
    layer: str
    decision: Decision
    risk_score: float = Field(ge=0, le=1)
    findings: list[Finding] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)
    status: Literal["ok", "degraded", "error"] = "ok"


class Verdict(StrictModel):
    decision: Decision
    final_risk_score: float = Field(ge=0, le=1)
    layers: list[LayerResult]
    reason_summary: str
    matched_controls: list[str] = Field(default_factory=list)


class AuditEvent(StrictModel):
    seq: int
    event_id: str
    timestamp: datetime
    tool_call: ToolCall
    verdict: Verdict
    prev_hash: str
    hash: str
    signature: str
    public_key_fingerprint: str
    model_id: str = "deterministic-only"
    policy_version: str


class ExecuteResponse(StrictModel):
    verdict: Verdict
    result: dict[str, Any] | None = None
