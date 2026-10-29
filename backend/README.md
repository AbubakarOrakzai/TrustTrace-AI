# TrustTrace Backend

FastAPI service that validates tool-call payloads, applies local deterministic
policies, records verdicts in a signed SQLite hash chain, and permits ALLOW
verdicts to reach sandbox-only mock tools.

Run from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```

Tests: `pytest -q`. Ruff: `ruff check .`. Type check:
`mypy`. API docs: <http://localhost:8000/docs>.

`POST /v1/evaluate/dataset` accepts up to 500 labeled public text samples. It
uses only the deterministic policy engine and returns aggregate metrics; it
does not call an LLM judge or add samples to the audit ledger. The public Vercel
API has no authentication. Do not send private, personal, or confidential
content to it.

From the repository root, Docker Compose starts the full demo with
`docker compose up --build`; it persists the audit database and signing key in
the `trusttrace-data` named volume.

All tools are synthetic mocks. In particular, mock `http_request` never sends
network traffic and mock `send_email` writes only to an in-process list. The
current policy and source-context checks are heuristic. The optional model
judge is disabled by default; NeMo Guardrails is not active. Select
`TRUSTTRACE_JUDGE_PROVIDER=nebius` (NVIDIA Nemotron-3-Nano-30B-A3B) and provide the matching API key
in the repository-root `.env` file to enable judging for `/v1/intercept` and
`/v1/execute`. These requests send tool arguments and context excerpts to the
selected provider; deterministic scenario replay remains offline. See the root
README for setup details. Audit signing keys and SQLite files are local
artifacts and are git-ignored.

Cybersecurity contributor: [Diltaj](https://github.com/Diltaj).
