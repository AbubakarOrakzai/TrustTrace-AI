# TrustTrace Dashboard

Responsive Next.js dashboard for the TrustTrace API. It runs deterministic
attack scenarios, displays verdicts and findings, verifies or exports the
audit ledger, and evaluates labeled public text samples in the Public Data Lab.

```bash
npm install
npm run dev
```

Open <http://localhost:3000>. The API defaults to `http://localhost:8000`; set
`NEXT_PUBLIC_API_URL` at build time to use another backend origin. Start the
backend separately. Deterministic scenarios and dataset evaluation do not call
a hosted model.

The Public Data Lab accepts JSON arrays/objects or JSONL rows with `text` and
binary `label` fields. On the public Vercel deployment, selected rows are sent
to the hosted backend; use public, non-sensitive data only. The endpoint returns
aggregate metrics and does not add sample rows to the app audit ledger.

At widths below 820px, the sidebar becomes a compact horizontal navigation bar,
and dashboard cards and upload controls reflow for phone screens.
The light/dark theme toggle defaults to the device color preference and saves
your selection in the browser.

The root `docker-compose.yml` runs the dashboard and API together. Its
`NEXT_PUBLIC_API_URL` build argument is compiled into the browser bundle.
