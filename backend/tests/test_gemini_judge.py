from __future__ import annotations

import json

import httpx
import pytest

from judge.gemini import GeminiJudge, JudgeUnavailableError
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

    monkeypatch.setattr("judge.gemini.httpx.post", fake_post)
    call = ToolCall(
        tool_name="read_file",
        arguments={"path": "demo/notes.txt"},
        user_instruction="Read the project notes.",
    )
    result, latency = GeminiJudge("test-key").evaluate(call)

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
        "judge.gemini.httpx.post",
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
