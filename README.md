# TrustTrace AI

**The AI Agent Firewall and Auditor** — a local demo that checks agent tool
calls against security policies before allowing them to reach sandboxed mock
tools, then records the decision in a signed audit ledger.

> **Prototype notice:** This project is for local demonstration, not production
> security or certified compliance. Reports provide evidence aligned with SOC 2
> / AIUC-1 concepts; they do not prove certification or compliance.

## Run it

### Easiest: Docker Compose

Install Docker Engine and Docker Compose, then run these commands from the
repository directory:

```bash
docker compose up --build
```

Wait until both services are healthy, then open:

- Dashboard: <http://localhost:3000>
- API and interactive docs: <http://localhost:8000/docs>
- Health status: <http://localhost:8000/health>

No API key or cloud account is needed. Stop the app with `Ctrl+C`, or run
`docker compose down` in another terminal. Audit data and its signing key are
stored in the local Docker volume named `trusttrace-data` and survive a normal
stop/restart.

To erase that local audit history and key as well as stop the services:

```bash
docker compose down --volumes
```

### Run without Docker

Requires Python 3.10+ and Node.js 18+.

Start the backend in one terminal:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Start the dashboard in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. The dashboard uses `http://localhost:8000` by
default. To use a different backend, set `NEXT_PUBLIC_API_URL` before building
the frontend; see [`frontend/.env.example`](frontend/.env.example).

## Use the dashboard

1. Select **Run scenario** on a card to send its synthetic tool call to the
   policy engine. The trace shows the final decision, risk score, findings, and
   any source-document attribution.
2. Select **Run full suite** to replay all eight included attack and benign
   scenarios. Review expected-decision accuracy, attack detection, benign false
   positives, and policy latency.
3. In **Latest trace**, inspect the proposed tool arguments and matched policy
   findings. A `BLOCK` or `REVIEW` decision never reaches a mock tool.
4. In **Audit ledger**, select **Verify chain** to validate event hashes and
   signatures, or **Export JSON** to download an evidence report.

Included scenarios:

| Scenario | Expected result | What it demonstrates |
|---|---|---|
| Invoice Exfiltration | BLOCK | Untrusted invoice context proposes sending payroll-related data externally |
| SQL Destruction via Support Ticket | BLOCK | A destructive SQL statement is intercepted |
| CRM Mass Tampering | REVIEW | A bulk CRM change exceeds the review threshold |
| URL Exfiltration | BLOCK | An unapproved destination and sensitive-data indicator |
| Injection in Retrieved Context | BLOCK | An instruction in untrusted source context is flagged |
| Safe Internal Email | ALLOW | Email to an approved internal domain |
| Safe SQL Read | ALLOW | A read from the mock customer table |
| Single CRM Note Update | ALLOW | A single-record mock update |

These are deterministic replays, not live LLM-agent runs. Repeated runs append
more records to the audit ledger.

## Use the API

Interactive request/response examples are available at
<http://localhost:8000/docs>. Common endpoints:

| Method and path | Purpose |
|---|---|
| `GET /health` | Check API and layer status |
| `GET /v1/scenarios` | List the demo scenarios |
| `POST /simulate/{scenario_id}` | Replay one scenario and record its verdict |
| `POST /v1/simulate/run-all` | Replay all scenarios and return a scorecard |
| `POST /v1/intercept` | Validate and inspect a tool call without executing it |
| `POST /v1/execute` | Inspect a tool call; execute a sandbox mock only on ALLOW |
| `GET /v1/traces` | List recent audit events |
| `GET /v1/traces/{event_id}` | Get one event by ID |
| `GET /v1/audit/verify` | Verify event hashes and signatures |
| `GET /v1/audit/report` | Downloadable JSON evidence report |

Run the invoice attack with curl:

```bash
curl -X POST http://localhost:8000/simulate/invoice-exfiltration
```

Check audit integrity:

```bash
curl http://localhost:8000/v1/audit/verify
```

Inspect the scorecard:

```bash
curl -X POST http://localhost:8000/v1/simulate/run-all
```

Example intercept request:

```bash
curl -X POST http://localhost:8000/v1/intercept \
  -H 'Content-Type: application/json' \
  -d '{
    "tool_name": "send_email",
    "arguments": {
      "recipient": "team@internal.example.com",
      "subject": "Meeting notes",
      "body": "The project review is on Thursday."
    },
    "user_instruction": "Send the notes to the internal team."
  }'
```

The tool name and its arguments must match the strict schema. The available
tools are `send_email`, `query_db`, `update_crm`, `read_file`, and
`http_request`. Extra argument fields are rejected.

## Policies and local data

Edit [`backend/policy/rules.yaml`](backend/policy/rules.yaml) to change the
allowed email/HTTP domains, sensitive-data patterns, restricted SQL tables, CRM
bulk threshold, or email rate limit. Restart the backend after editing.

The API stores audit events in SQLite and creates an Ed25519 signing key on
first start. Without Docker these files are
`backend/trusttrace.db` and `backend/.trusttrace-signing-key.pem`; Docker stores
them in its named data volume. Keep the key private: the ledger's signatures
cannot be independently verified if the private key is lost.

## What this demo does—and does not do

- Tools use synthetic data and sandbox mocks only. The email tool writes to an
  in-process fake outbox; the HTTP tool does not make a network request; SQL
  operates only on an in-memory SQLite database.
- A policy `ALLOW` permits only that local mock. It does not authorize or perform
  a real external action.
- Policy and prompt-injection checks are deterministic heuristics; they can miss
  attacks or flag benign activity. Do not connect real tools or sensitive data.
-   The Gemini judge and NVIDIA NeMo Guardrails are disabled by default. Scenario
  replays remain deterministic and do not call a hosted model. You can optionally
  enable Gemini judging for `/v1/intercept` and `/v1/execute` requests; when
  enabled, those tool-call arguments and context excerpts are sent to Google's
  Gemini API. Do not send sensitive or confidential data.
- SSE streaming, PDF reports, and production-grade isolation are not
  implemented.

## Optional Gemini judge

Google's [Gemini API supports the OpenAI-compatible chat completions
endpoint](https://ai.google.dev/gemini-api/docs/openai). The live judge is
disabled by default; no key is needed for the scenarios or dashboard demo.

1. Copy the example environment file at the repository root:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` locally and set `TRUSTTRACE_JUDGE_PROVIDER=gemini` and
   `GEMINI_API_KEY` to a key from Google AI Studio. Keep `.env` private; it is
   excluded from Git.
3. If using Docker Compose, recreate the backend so it receives the setting:

   ```bash
   docker compose up -d --build backend
   ```

   For manual backend setup, restart Uvicorn after saving `.env`.
4. Check `GET /health`; `layers.llm_judge` should report `ready`.
5. Send a tool call to `POST /v1/intercept` or `/v1/execute`. The verdict and
   audit event will include the Gemini judge result/model. Deterministic
   scenario replay (`/simulate/...` and **Run full suite**) intentionally stays
   offline and repeatable.

Deterministic BLOCK decisions short-circuit the model call and cannot be
overridden. When the judge is enabled, an unavailable service or invalid result
fails closed as `BLOCK` with `evaluator_unavailable`. Gemini evaluation sends
the user instruction, tool arguments, and source excerpts to Google and may
incur API charges. The model's opinion is not a security guarantee.

## Project and contributor notes

- [Backend setup and development](backend/README.md)
- [Dashboard setup](frontend/README.md)
- [Durable project context](CONTEXT.md)
- [Session handoff for future contributors/LLMs](SESSION.md)

Team: Haseeb Khan (ML Engineer), Abu Baker (Frontend Developer), and Luqman Khan
(ML Engineer).
