# Milestone 3 — Deployed API
**Date:** 2026-08-06
**Git:** commit 59d11eb, tag `milestone-3`

---

# Objective

Deploy the Scientific Reasoning OS lifecycle as a production service on
Google Cloud Run, reachable through a stable public endpoint, with the same
guarantees as the local slice: schema-validated agent output, append-only
events, per-run audit.

---

# Outcome

Successfully deployed.

Cloud Run service: `sros-api`
Public endpoint: `https://sros-api-209857552354.us-central1.run.app`

First cloud execution: question `rq_df3d800b13dc` — full lifecycle
(submitted → critiqued → events written) in **9.3 seconds** at an estimated
cost of **US$0.0023**, roughly half the local latency because compute now
sits in the same region as Vertex AI and Firestore.

---

# What was built

- FastAPI service exposing the lifecycle: `POST /questions`,
  `POST /questions/{id}/revisions`, `POST /questions/{id}/validate`,
  `GET /questions/{id}`, `GET /health`.
- Shared API-key authentication (`X-API-Key`), **fail-closed**: if the key
  is unconfigured the service rejects all requests rather than opening up.
- Domain refusals (e.g. revising a validated/locked question) surface as
  HTTP 409, preserving the behavioural rules over HTTP.
- Dockerfile + Cloud Build source deployment; 512Mi / 1 CPU /
  max 2 instances to cap cost exposure.

---

# Diagnosis worth recording: /healthz vs /health

The application initially exposed `GET /healthz`, which returned a Google
Frontend 404 **before the request ever reached the application**, even
though the route was registered and visible in the OpenAPI specification.
Isolation (performed by the founder): `/questions` worked end to end;
`/healthz/` (trailing slash) reached FastAPI as a 307 redirect; `/healthz`
never appeared in application logs — proving the interception happened at
Google's frontend layer, which reserves `/healthz` on Cloud Run. Renaming
the endpoint to `/health` eliminated the conflict.

**Canonical health endpoint: `GET /health`.** Monitoring tools, load
balancers, and future clients must use it (recorded as architecture
decision 10).

---

# Evidence

- 01-SROS-running.png
- 02-Question-versioning.png
- 03-Agent-critique.png
- Cloud Run logs of the first cloud execution (latency and cost above)
- Git tag `milestone-3`

The screenshots demonstrate the deployed system serving version-controlled
research questions with structured A-02 critiques to an authenticated user.

---

# Technical debt recorded

- Shared API key is service-wide; per-user tokens arrive with Milestone 4.
- No uptime monitoring configured against `/health` yet.

---

# Milestone achieved

Scientific Reasoning OS runs in Google Cloud through a stable endpoint. The
compute left the founder's laptop without losing a single audit guarantee.
