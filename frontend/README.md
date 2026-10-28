# TrustTrace Dashboard

Next.js dashboard for the local TrustTrace API. It runs deterministic attack
scenarios, displays the verdict and policy findings, and verifies or exports
the signed local audit ledger.

```bash
npm install
npm run dev
```

Open <http://localhost:3000>. The API defaults to `http://localhost:8000`; set
`NEXT_PUBLIC_API_URL` at build time to use another backend origin. Start the
backend separately. No hosted model is called from the dashboard.

The root `docker-compose.yml` runs the dashboard and API together. Its
`NEXT_PUBLIC_API_URL` build argument is compiled into the browser bundle.
