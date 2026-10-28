# TrustTrace AI — Demo Video Script

**Target length:** 3 minutes
**Format:** Screen recording with voice-over
**Demo URL:** `http://localhost:3000`

## Before recording

- Start the app from the repository root with `docker compose up --build`.
- Open the dashboard and wait for both services to be healthy.
- Use a fresh audit ledger if you want the counters to start at zero.
- Close unrelated windows and keep the dashboard/browser zoom readable.
- Optional: run `pytest` and `python backend/benchmark.py` in a second window for the baseline comparison.
- The demo uses deterministic scenario replays and sandboxed mock tools. It does
  not use a live LLM, send email, or make external HTTP requests.

## Script

### 0:00–0:20 — The problem

**On screen:** Show the TrustTrace dashboard overview.

**Narration:**
“AI agents can do more than answer questions. They can call tools that send
messages, read files, or update business systems. But an instruction hidden in
a document can try to steer an agent into taking an action the user never
requested. TrustTrace focuses on that execution boundary: inspect the proposed
tool call before it reaches a tool.”

### 0:20–0:45 — What TrustTrace checks

**On screen:** Point to the local policy status and scenario cards.

**Narration:**
“This prototype runs locally. It validates each tool-call payload, checks
deterministic policies, and records the result in a signed audit ledger. For
this demo, all tools are sandboxed mocks and all data is synthetic. There is no
live model or external service involved.”

### 0:45–1:35 — Invoice exfiltration

**On screen:** Click **Run scenario** on **Invoice Exfiltration**. Show the
BLOCK verdict, unapproved-destination and sensitive-data findings, and source
attribution to `invoice_4471.pdf`.

**Narration:**
“Here the user asked for a summary of a vendor invoice. The synthetic invoice
contains a hidden instruction to forward payroll data to an external address.
The replay proposes an email tool call. TrustTrace sees both the sensitive-data
indicator and the unapproved destination, and blocks the call before any mock
tool runs. The finding also points back to the invoice that contained the
instruction.”

### 1:35–2:05 — Benign controls, full suite and baseline

**On screen:** Run **Safe Internal Email**, then select **Run full suite**. Show
the scorecard results.

**Narration:**
“A firewall also needs benign controls. This email goes to an approved internal
domain, so the policy allows it in the sandbox. The full suite replays attack
and benign examples and compares each result with its expected decision. These
numbers describe only the included deterministic scenarios; they are not a
general security guarantee. For comparison, a naive keyword filter catches one
of the five attacks on these same scenarios; TrustTrace catches all five and
adds a REVIEW tier for bulk changes.”

### Optional insert (+15 s) — Tested against evasion

**On screen:** Show `pytest` output: 22 passed, 1 xfailed.

**Narration:**
“We also attacked our own rules. Obfuscated SQL, look-alike domains and path
traversal are all blocked, and testing found a real gap, which we fixed.
One known miss remains: leetspeak injection. We keep it as a tracked failing
test, and the optional model judge targets that class.”

### 2:05–2:40 — Audit evidence

**On screen:** Click **Verify chain**, then **Export JSON**.

**Narration:**
“Each decision is stored in a local SQLite ledger. Events are linked with
SHA-256 hashes and signed with a local Ed25519 key. We can verify the chain and
export a JSON report. The report is evidence aligned with SOC 2 and AIUC-1
control concepts; it is not a certification or compliance claim.”

### 2:40–3:00 — Close

**On screen:** Return to the overview, with the TrustTrace name visible.

**Narration:**
“TrustTrace is an early, offline-first prototype of an AI-agent firewall:
inspect tool calls, apply policy before execution, and keep a verifiable record
of decisions. An optional Gemini judge can only make a verdict stricter, and NeMo Guardrails
is on the roadmap. For now, the demo is deterministic, local, and safe to
explore. One command starts it: docker compose up.”

## Recording notes

- Keep the dashboard visible while describing each result; avoid implying a
  live AI agent generated the scenario tool calls.
- If the ledger is not empty, describe the displayed counts as accumulated
  local events rather than session-only totals.
- Do not show API keys, private signing keys, or real personal/enterprise data.
