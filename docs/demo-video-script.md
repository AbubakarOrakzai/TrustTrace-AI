# TrustTrace AI — Hackathon Demo Video

- **Target length:** approximately 3 minutes 40 seconds
- **Format:** 1080p screen-led animation with captions and one consistent voice
- **Output:** `docs/PresentationVideo.mp4`

## Before recording

- For a local demo, run `docker compose up --build` from the repository root.
- For a public demo, open the dashboard and check that the API is online.
- Use the real dashboard screenshots supplied in `docs`; fit the entire image
  inside each frame rather than cropping its edges.
- For the Public Data Lab, use **Download public benchmark sample**. It has
  12 labeled rows from the pinned NeurAlchemy sample, not private or production
  data. Uploaded rows are sent to the hosted backend; use public,
  non-sensitive data only.
- Demonstrate the optional model judge separately with an eligible,
  harmless synthetic request. The successful local test used a benign
  synthetic file-read request and returned a valid structured result from
  Nebius Token Factory, model
  `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Do not show credentials or claim this one inference is a benchmark, uptime
  guarantee, or proof of general model accuracy.
- Scenario tools are sandbox mocks. No real email, SQL database, CRM, file
  system, or external HTTP service is called.
- Keep soft ambient music under the narration, and show the project GitHub
  URL in a persistent button at the lower-right corner.

## Script

### Start with the risk

**On screen:** Fit the real TrustTrace dashboard fully in frame. Progressively
reveal the path from an untrusted document to a proposed tool call and a
pre-execution decision.

**Narration:**
“An AI agent can read an invoice, then propose an email the user never
authorized. The risk is not only what the model says. It is what the agent is
about to do. TrustTrace checks the proposed tool call and its source context
before execution.”

### Stop the attack at the boundary

**On screen:** Run **Invoice Exfiltration**. Reveal the hidden instruction,
outside recipient, policy findings, and final BLOCK in that order. Keep the
complete dashboard visible.

**Narration:**
“Here, a synthetic invoice asks the agent to forward payroll-related data to
an outside address. TrustTrace validates the call, checks the destination and
the untrusted source, then blocks it. This deterministic block never reaches
the model judge. No email is sent.”

### Show the measured scope

**On screen:** Select **Run full suite**, then animate the scorecard in:
eight examples, five of five authored attacks flagged, zero of three benign
calls blocked, about one millisecond local-policy median.

**Narration:**
“The team-authored suite replays eight examples: five of five attacks are
flagged, and none of three benign calls are blocked. These numbers measure a
small regression suite. They do not show how the rules perform against every
real-world attack.”

### Be honest about the benchmark

**On screen:** Download and evaluate the pinned public sample. Reveal the
12-row count, then the current result: zero of six attacks flagged.

**Narration:**
“The Public Data Lab evaluates a small pinned sample with deterministic rules.
In these twelve rows, the current rules flag none of the six attacks. That is
an important limitation, not a success. This feature uses deterministic
evaluation, not an external model, and does not add samples to the audit
ledger. Uploaded rows go to the hosted backend, so use public, non-sensitive
data only.”

### Explain how it is built

**On screen:** Animate the architecture left to right: Next.js dashboard,
FastAPI endpoint, strict schema and deterministic policy, optional judge, then
SQLite hash chain with Ed25519 signatures. Reveal ALLOW, REVIEW, and BLOCK
outcomes last.

**Narration:**
“The Next.js dashboard presents decisions from a FastAPI backend. Calls pass
strict schema validation and deterministic policy checks first. An eligible
call can then use the optional model judge. Decisions are recorded in a
SQLite hash chain and signed with Ed25519. Even ALLOW reaches only a sandbox
mock.”

### Verify the real Nemotron path

**On screen:** Show the Nebius logo and a clearly labeled
“NVIDIA HACKATHON · PROJECT DEMO” corner label. Animate the synthetic request
through policy checks to Nebius and Nemotron. Show the exact model name and
successful structured response.

**Narration:**
“Separately, I verified the optional judge with one harmless synthetic
request. Nebius Token Factory returned a valid structured response from
NVIDIA Nemotron 3 Nano. Deterministic blocks still short-circuit before the
model, and provider errors fail closed. One successful request proves this
path worked once; it is not a benchmark or an availability guarantee.”

### Leave verifiable evidence

**On screen:** Select **Verify chain**, animate the event links, then select
**Export JSON**.

**Narration:**
“Each tool-call verdict can be checked in the audit ledger. Events are linked
with SHA-256 hashes and signed with Ed25519. We can verify the chain and
export a JSON report. Hosted Vercel filesystems are temporary, so hosted audit
history is not durable.”

### Make the boundary explicit

**On screen:** Reveal the five tool schemas one at a time beside the sandbox
notice. End on the full dashboard and project link.

**Narration:**
“The five downloaded schemas describe demo functions; they do not connect to
live services or start an agent. TrustTrace inspects tool calls before
execution and records each decision. The benchmark also highlights where the
current rules need improvement.”

## Presentation choices

- Lead with a concrete, recognizable risk, then show the interception
  step-by-step. Use one main idea per chapter and reveal evidence only when it
  is discussed.
- Keep motion purposeful: use staged highlights and transitions to show
  sequence or focus, not decoration. Preserve full dashboard screenshots and
  readable contrast.
- Use concise on-screen labels, synchronized captions, one consistent
  medium-paced narrator voice, and a subtle ambient music bed. Keep
  limitations beside the results they qualify; do not inflate benchmark
  claims or imply NVIDIA endorsement.
- These choices follow guidance on purposeful animation, scanning and
  cognitive load, and video usability:
  - [NN/g: Animation for Attention and Comprehension](https://www.nngroup.com/articles/animation-usability/)
  - [NN/g: How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/)
  - [NN/g: Minimize Cognitive Load](https://www.nngroup.com/articles/minimize-cognitive-load/)
  - [NN/g: Video Usability](https://www.nngroup.com/articles/video-usability/)
