from __future__ import annotations

import json

import httpx
import pytest

from judge.providers import (
    NEBIUS_MODEL,
    GeminiJudge,
    JudgeUnavailableError,
    NebiusJudge,
    configured_judge,
)
from models.schemas import ToolCall


def _completion(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
        request=httpx.Request("POST", "https://example.test"),
    )


def test_gemini_judge_retries_invalid_json_and_parses_verdict(monkeypatch) -> None:
    responses = [
        _completion("not json"),
        _completion(
            json.dumps(
                {
                    "aligned_with_user_intent": True,
                    "injection_suspected": False,
                    "injection_source_id": None,
                    "risk_score": 0.1,
                    "rationale": (
                        "The internal note request matches the user instruction."
                    ),
                }
            )
        ),
    ]
    requests = []

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr("judge.providers.httpx.post", fake_post)
    call = ToolCall(
        tool_name="read_file",
        arguments={"path": "demo/notes.txt"},
        user_instruction="Read the project notes.",
    )
    evaluation = GeminiJudge("test-key").evaluate(call)
    result = evaluation.result
    latency = evaluation.latency_ms

    assert result.aligned_with_user_intent is True
    assert result.risk_score == 0.1
    assert latency >= 0
    assert len(requests) == 2
    assert requests[0][0] == (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    )
    assert requests[0][1]["headers"]["Authorization"] == "Bearer test-key"
    assert requests[0][1]["timeout"] == 8.0


def test_gemini_judge_fails_closed_after_two_invalid_responses(monkeypatch) -> None:
    monkeypatch.setattr(
        "judge.providers.httpx.post",
        lambda *args, **kwargs: _completion("{}"),
    )
    judge = GeminiJudge("test-key")
    call = ToolCall(tool_name="read_file", arguments={"path": "demo/notes.txt"})

    with pytest.raises(JudgeUnavailableError):
        judge.evaluate(call)


def test_gemini_judge_requires_api_key() -> None:
    judge = GeminiJudge(None)
    call = ToolCall(tool_name="read_file", arguments={"path": "demo/notes.txt"})

    with pytest.raises(JudgeUnavailableError):
        judge.evaluate(call)


def test_nebius_judge_uses_token_factory_model_and_endpoint(monkeypatch) -> None:
    request = {}

    def fake_post(url, **kwargs):
        request["url"] = url
        request.update(kwargs)
        return _completion(
            json.dumps(
                {
                    "aligned_with_user_intent": True,
                    "injection_suspected": False,
                    "injection_source_id": None,
                    "risk_score": 0.1,
                    "rationale": (
                        "The requested read is consistent with the instruction."
                    ),
                }
            )
        )

    monkeypatch.setattr("judge.providers.httpx.post", fake_post)
    call = ToolCall(tool_name="read_file", arguments={"path": "demo/notes.txt"})

    evaluation = NebiusJudge("test-key").evaluate(call)

    assert evaluation.result.aligned_with_user_intent
    assert evaluation.provider == "Nebius Token Factory"
    assert evaluation.model == NEBIUS_MODEL
    assert request["url"] == (
        "https://api.tokenfactory.nebius.com/v1/chat/completions"
    )
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == NEBIUS_MODEL
    assert "response_format" not in request["json"]


def test_configured_judge_selects_nebius_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTTRACE_JUDGE_PROVIDER", "nebius")
    monkeypatch.setenv("NEBIUS_API_KEY", "local-test-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    judge = configured_judge()

    assert isinstance(judge, NebiusJudge)
    assert judge.provider == "Nebius Token Factory"
    assert judge.configured


def test_nebius_judge_falls_back_to_gemini_after_provider_failure(monkeypatch) -> None:
    requests = []

    def fake_post(url, **kwargs):
        requests.append(url)
        if "tokenfactory.nebius.com" in url:
            return httpx.Response(
                503,
                request=httpx.Request("POST", url),
            )
        return _completion(
            json.dumps(
                {
                    "aligned_with_user_intent": True,
                    "injection_suspected": False,
                    "injection_source_id": None,
                    "risk_score": 0.1,
                    "rationale": (
                        "The requested read is consistent with the instruction."
                    ),
                }
            )
        )

    monkeypatch.setattr("judge.providers.httpx.post", fake_post)
    judge = NebiusJudge(
        "nebius-test-key",
        fallback=GeminiJudge("gemini-test-key"),
    )
    call = ToolCall(tool_name="read_file", arguments={"path": "demo/notes.txt"})

    evaluation = judge.evaluate(call)

    assert evaluation.provider == "Gemini"
    assert evaluation.model == GeminiJudge("key").model
    assert evaluation.fallback_used
    assert len(requests) == 2
    assert "tokenfactory.nebius.com" in requests[0]
    assert "generativelanguage.googleapis.com" in requests[1]


def test_configured_nebius_enables_gemini_fallback_when_key_present(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRUSTTRACE_JUDGE_PROVIDER", "nebius")
    monkeypatch.setenv("NEBIUS_API_KEY", "local-nebius-key")
    monkeypatch.setenv("GEMINI_API_KEY", "local-gemini-key")

    judge = configured_judge()

    assert isinstance(judge, NebiusJudge)
    assert judge.provider == "Nebius Token Factory with Gemini fallback"
    assert judge.configured
