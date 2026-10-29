# LinkedIn post — TrustTrace AI

## Post copy

An AI agent can read an invoice, follow an instruction hidden inside it, and
propose a tool call the user never authorized.

I built **TrustTrace AI** to inspect agent tool calls before they reach a
tool. It checks the proposed action and its untrusted context, applies policy,
and records the decision in a signed audit trail.

The demo shows:

- A synthetic invoice-driven data-exfiltration attempt blocked before any
  email is sent.
- An eight-case, team-authored regression suite: five of five authored
  attacks flagged, with zero of three benign calls blocked. These results
  describe this small test suite, not general attack-detection performance.
- A Public Data Lab evaluation where the current deterministic rules flagged
  zero of six attacks in a 12-row sample. That limitation is part of the
  story—and a clear direction for improving the project.
- A separately verified, optional inference using NVIDIA Nemotron 3 Nano
  through Nebius Token Factory. The Public Data Lab itself uses deterministic
  rules and does not call an external model.

The project is a prototype: its tools are sandbox mocks, and the benchmark
results are not a security guarantee. I’m sharing the work to get feedback
and keep improving how agent actions are checked before execution.

This is an independent project; it is not sponsored or endorsed by NVIDIA or
Nebius.

🎥 Watch the attached project demo.

Project: https://github.com/Haseebi-khan/TrustTrace-AI

#AI #GenerativeAI #NVIDIA #Nemotron #Nebius #AI安全 #Cybersecurity #Hackathon

## Posting notes

- Attach `docs/PresentationVideo.mp4` to the post.
- Keep the limitation about the 12-row sample visible; do not present it as a
  broad benchmark result.
- The project is independently built; do not imply NVIDIA or Nebius
  sponsorship, endorsement, or partnership.
