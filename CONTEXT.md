# TrustTrace AI — Project Context

Durable requirements and confirmed decisions for this repository. Update this
file when project scope or architecture changes; do not convert assumptions
into decisions without confirmation.

## Purpose and users

TrustTrace AI is a hackathon prototype for intercepting AI-agent tool calls
before execution, applying deterministic security policies, and generating
tamper-evident audit evidence. Intended users are teams building AI agents who
need visibility and control at the tool-execution boundary.

## Team

- Haseeb Khan — Machine learning engineer; project owner.
- Abu Baker — Frontend Developer.

## Confirmed product requirements

- Never perform real side effects in demo tools; use sandboxed mocks and fake
  data only.
- Deterministic policy checks run before any optional model evaluation.
- A model judge may escalate risk but must never override a deterministic block.
- If an enabled external evaluator is unavailable or invalid, fail closed.
- NeMo Guardrails should be optional and degrade without taking down the service.
- Compliance language must describe evidence as aligned with controls, never
  claim SOC 2 or AIUC-1 certification.
- Payload models forbid unknown fields, and secrets must not be committed.
- Product premise: prevent untrusted context from steering an agent into
  unauthorized tool calls; include attack scenarios and benign controls.

## Current implementation decisions

- Python/FastAPI backend, Pydantic v2, Next.js/TypeScript frontend.
- MVP is local-first and offline; no Nebius calls or NeMo Guardrails integration
  are currently enabled.
- Deterministic policies inspect synthetic tool calls before execution.
- Tools are sandboxed mock implementations; no outbound email/HTTP/OS actions.
- SQLite audit ledger uses a SHA-256 chain and locally generated Ed25519 key.
- Docker Compose runs both services locally and persists the audit data/key in a
  named volume.
- No hosted service, real user data, or production integrations are configured.

## Deferred and unverified

- Current Nebius Token Factory base URL and available Nemotron model IDs.
- Current NeMo Guardrails API/configuration for OpenAI-compatible inference.
- Live LLM judge, real-time SSE, PDF report, Docker Compose, deployed demo URL,
  and real integration SDK.
- Hackathon demo/video links and final repository URL.

## Safety and compliance boundaries

- Never attach real tools or sensitive enterprise data to the demo.
- Never interpret a policy ALLOW as authorization to perform an actual external
  action; it only permits a sandbox mock in this prototype.
- Reports are evidence aligned with control concepts, not certification or a
  compliance guarantee.
- Treat retrieved document context as untrusted input.

## Contributor / LLM guidance

- Read this file and `SESSION.md` before changing the project.
- Preserve the no-real-side-effects boundary.
- Keep claims honest and distinguish implemented behavior from roadmap items.
- Update README/setup docs and session handoff when implementation changes.
- Run focused tests and builds for touched components; report failures plainly.
