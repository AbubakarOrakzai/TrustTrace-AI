# Session Handoff

Keep this file current at the end of each work session for the next contributor
or LLM.

## Current state

The local-first MVP is implemented and validated. It includes a deterministic
FastAPI interceptor, sandboxed mock tools, scenario simulator/scorecard, signed
SQLite audit ledger, Next.js dashboard, and a working Docker Compose stack.
An optional Gemini judge is available; it remains disabled unless configured
with a local API key.

## Work completed before implementation

- Initialized this directory as a Git repository.
- Added project context for Haseeb Khan and Abu Baker.
- Read the user-provided power prompt; its safety requirements are documented in
  `CONTEXT.md`.
- Replaced the placeholder README with project setup, architecture, demo, and
  limitations.

## Implementation status

- [x] Backend schemas, API, policy engine, mock tools, and audit ledger.
- [x] Backend unit and API flow tests.
- [x] Frontend simulator, full-suite scorecard, trace, and audit verification UI.
- [x] Docker Compose build and live health/simulator smoke test.
- [x] Optional Gemini judge with deterministic BLOCK short-circuit and fail-closed errors.
- [x] Root, backend, and frontend setup/handoff documentation.
- [x] Backend lint/type checks and frontend production build.

## Ten-point build plan

1. Define strict tool-call, finding, verdict, and audit-event schemas.
2. Reject invalid payloads and tool arguments before evaluation.
3. Enforce deterministic destination, sensitive-data, SQL, CRM, and context rules.
4. Route ALLOW verdicts only to local sandbox mocks.
5. Sign each audit event and verify the SQLite hash chain.
6. Expose intercept, execute, traces, scenarios, report, and health APIs.
7. Ship deterministic attack/benign scenarios and a full-suite scorecard.
8. Provide a dashboard for scenario runs, findings, traces, and audit verification.
9. Package the backend and dashboard in a health-checked Docker Compose stack.
10. Add optional hosted Nemotron judging and NeMo Guardrails only after
    documentation verification and with a locally supplied key.

## Decisions and assumptions

- Start offline and deterministic so the demo runs without API credentials.
- Use synthetic data and mocked tools only; do not trigger external side effects.
- Do not guess provider endpoints/model IDs or NeMo APIs; verify before integration.
- Initial context-injection detection is heuristic and is not represented as a
  complete prompt-injection defense.
- SQL execution is restricted to one data statement in the in-memory sandbox;
  destructive/unbounded operations and database attachment are blocked.
- Google's OpenAI-compatible Gemini endpoint has been verified against
  https://ai.google.dev/gemini-api/docs/openai. Gemini remains optional and
  sends tool-call data to Google only when enabled.
- Nebius Token Factory URL/model IDs and NeMo Guardrails configuration APIs have
  not been independently verified; those integrations remain disabled.

## Validation results

- Backend: 12 tests pass. TestClient emits a non-fatal Starlette deprecation
  warning about its current `httpx` integration.
- Gemini judge and fail-closed integration are covered with mocked API responses;
  no real API key is needed for tests.
- `ruff check .` and strict `mypy` pass.
- `npm run build` passes with Next.js 15.5.28.
- `docker compose up -d --build --wait` passes after Gemini support; both
  containers report healthy, dashboard returns HTTP 200, and invoice scenario
  returns the expected BLOCK with Gemini disabled.
- Manual API coverage verifies scenario replay, sandbox ALLOW, scorecard, report,
  and audit-chain verification.

## Next steps

Next, Haseeb can add a newly rotated Gemini key to an ignored local `.env` to
try live judging. Any Gemini key previously pasted into chat should be revoked
and replaced before use.
Nebius/Nemotron, NeMo Guardrails, SSE, PDF export, repository publication, and
demo/video links remain future work.
