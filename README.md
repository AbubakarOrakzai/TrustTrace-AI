# TrustTrace AI

**The AI Agent Firewall and Auditor** — a local-first demo that inspects agent
tool calls before they reach sandboxed mock tools, applies deterministic policy,
and records tamper-evident audit evidence.

> This is a hackathon prototype, not a certified compliance product. Its reports
> provide evidence aligned with SOC 2 / AIUC-1 concepts; they do not establish
> certification or compliance.

## What works in this starter

- FastAPI interception API with strict request and per-tool argument validation.
- Deterministic policies for external destinations, sensitive-data exfiltration,
  risky SQL, prompt-injection indicators in source context, and bulk CRM changes.
- Offline scenario simulator, including invoice exfiltration and benign controls.
- Sandbox-only mock tools. No email, network request, OS command, or real database
  mutation is performed by a tool.
- SQLite audit ledger with a SHA-256 hash chain and Ed25519 signatures.
- Next.js dashboard for running scenarios and inspecting recent verdicts.
- Local setup and focused backend tests.

The LLM judge, NeMo Guardrails, SSE, PDF exports, Docker Compose, and richer
scorecard are not wired up yet. The MVP does not send data to a hosted model.
This keeps the initial demo deterministic, offline, and safe.

## Architecture

```text
Dashboard ──HTTP──> FastAPI interceptor
                         ├─ strict Pydantic validation (L0)
                         ├─ deterministic policy engine (L1)
                         ├─ source-context injection indicators (initial L2)
                         ├─ decision aggregation (no LLM judge in MVP)
                         ├─ signed SQLite audit ledger
                         └─ ALLOW only ──> sandboxed mock tool
```

## Quick start

Requirements: Python 3.10+ and Node.js 18+.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000
```

Backend API docs: <http://localhost:8000/docs>. The local audit DB is created at
`backend/trusttrace.db`; the signing key is generated locally at
`backend/.trusttrace-signing-key.pem`. Keep both local and do not commit them.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard: <http://localhost:3000>. Set `NEXT_PUBLIC_API_URL` if the backend is
not at `http://localhost:8000`.
Copy `frontend/.env.example` to `frontend/.env.local` to configure the API URL.

## API

- `GET /health` — backend status and enabled layers.
- `GET /v1/scenarios` — deterministic demo scenarios.
- `POST /simulate/{scenario_id}` — replay a fixed tool call through the policy.
- `POST /v1/intercept` — validate and inspect a `ToolCall`.
- `POST /v1/execute` — inspect, then execute only an ALLOW verdict using a mock.
- `GET /v1/traces` and `GET /v1/traces/{id}` — recent audit records.
- `GET /v1/audit/verify` — verify the hash chain and Ed25519 signatures.
- `GET /v1/audit/report` — JSON evidence export with an alignment disclaimer.

Example:

```bash
curl -s http://localhost:8000/simulate/invoice-exfiltration
```

## Demo walkthrough

1. Start backend and frontend using the commands above.
2. Open the dashboard and run **Invoice Exfiltration**. It should be BLOCKED:
   the scenario proposes sending payroll-related data to an unapproved domain.
3. Run **Safe Internal Email** or **Safe SQL Read**; these are benign controls.
4. Open **Audit** and verify the signed event chain.
5. Inspect the event details and JSON evidence export.

## Initial 3-minute hackathon presentation

- **Problem (20s):** Agents can turn untrusted document content into harmful
  tool calls; text-only moderation does not gate the execution boundary.
- **Hero attack (60s):** Run Invoice Exfiltration and show deterministic block
  findings before the mock tool can execute.
- **Controls (40s):** Run safe scenarios to show allowed calls and explain the
  policy boundary.
- **Audit (40s):** Verify the local hash/signature chain and export JSON evidence.
- **Architecture/roadmap (20s):** Explain that this starter is offline and
  deterministic; live Nebius judging and NeMo rails remain planned work.

## Roadmap and known limitations

1. Add configurable Nebius judging with strict structured output, bounded
   timeouts, and fail-closed behavior after verifying current provider/model docs.
2. Add NeMo Guardrails as an optional layer that degrades cleanly if unavailable.
3. Add SSE traces, richer attack scorecard, PDF export, Docker Compose, and CI.
4. Expand policies and test coverage; review false-positive/negative behavior.
5. Add a thin framework integration/SDK only after the API stabilizes.

The included injection checks are heuristic indicators, not a complete detector.
This MVP does not claim to detect every prompt injection, guarantee a 95%
detection rate, or provide production-grade isolation. Do not connect real tools
or sensitive data to it.

## Team

- Haseeb Khan — Software, ML/DL/CV Engineer & Cloud Engineer.
- Abu Baker — Frontend Developer.
- Luqman Khan — ML Engineer

## Handoff for other LLMs

Read [CONTEXT.md](CONTEXT.md) for durable project decisions and
[SESSION.md](SESSION.md) for current status and next steps before continuing.
