# TrustTrace AI — Pitch Deck Outline

One idea per slide. Every number comes from `POST /v1/simulate/run-all` or
`python backend/benchmark.py` on the bundled scenarios.

1. **Title** — "Agent tool calls in. Verified decisions out." TrustTrace AI,
   the AI agent firewall and auditor. Team names.
2. **The problem** — Agents now send email, run SQL and edit CRMs. One poisoned
   invoice can tell them to leak payroll. Nobody checks the call before it runs.
3. **Why prompt filtering fails** — The attack lives in retrieved context, not
   in the tool arguments. Show the invoice text next to the harmless-looking email call.
4. **The solution** — Inspect every proposed tool call *and* its untrusted
   sources at the execution boundary. Only a policy ALLOW reaches a (sandbox) tool.
5. **How it works** — Diagram: schema → policy engine → optional Gemini judge
   → ALLOW / REVIEW / BLOCK → signed ledger. The judge can only tighten a verdict; failure blocks.
6. **Live demo** — Invoice Exfiltration blocked, source attributed to
   `invoice_4471.pdf`; Safe Internal Email allowed.
7. **Results** — 8 scenarios, 5/5 attacks stopped, 0/3 benign blocked,
   p50 policy latency about 1 ms.
8. **Benchmark** — Keyword filter catches 1/5 attacks; TrustTrace 5/5, plus a
   REVIEW tier for bulk changes. State the caveat: team-authored scenarios.
9. **Audit evidence** — SHA-256 chain + Ed25519 signatures, Verify chain, JSON
   export aligned to SOC 2 / AIUC-1 concepts. Never claims "compliant".
10. **Honest limits** — Heuristics can be evaded; mocks only; NeMo Guardrails
    not built. Fail-closed by design.
11. **Roadmap** — Real agent integration (MCP proxy), approval queue, NeMo,
    PDF reports, per-tenant policy.
12. **Ask / close** — Run it in one command: `docker compose up --build`. Repo,
    site and team.
