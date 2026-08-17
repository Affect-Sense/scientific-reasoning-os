# Scientific Reasoning OS — Gemini XPRIZE Submission

**AffectSense · August 2026**
*An agentic research environment that critiques research questions. Built on
Gemini 2.5 Flash (Vertex AI). The agent critiques; the researcher decides.*

---

## What this is

Scientific Reasoning OS (SROS) helps researchers turn a rough idea into a
defensible research question. The Scientific Question Agent (A-02) evaluates a
submitted question on four formulation-stage criteria — clarity, relevance,
feasibility, falsifiability — classifies the inquiry type, exposes implicit
assumptions, flags missing information, proposes concrete revisions, and
routes methodological concerns into non-blocking design-stage notes. Every
version is preserved with full provenance. The agent never validates a
question; only the researcher does.

## Live system

- **Public service:** https://sros-api-209857552354.us-central1.run.app
- **Liveness:** the live-demo URL above; the `/health` route recorded in decision 10 was never applied to code (`/healthz` remains, and is intercepted by the Google Frontend on Cloud Run) — corrected post-freeze
- **Architecture:** FastAPI on Google Cloud Run (us-central1) · Gemini 2.5
  Flash via Vertex AI · Firestore (append-only events + agent-run ledger) ·
  Stripe Checkout (autonomous onboarding).

## How to test it (judges)

A time-limited access link and a founders promo code are provided in the
submission form. With the link:

1. Open the access URL. You land in a workspace (Spanish default; use the
   header 🌐 toggle for English, or select English on the form).
2. Submit any rough research question. Wait 10–30s for the agent.
3. Read the structured critique: four criteria with severity, assumptions,
   missing information, revision suggestions, design-stage notes, declared
   uncertainty.
4. Submit a revision with a change note. Observe the version lineage.
5. Validate and lock when you judge it ready — the decision is yours.

To see the full commercial pipeline: complete a Stripe checkout with the
provided promo code (MX$0). You are provisioned a workspace and redirected
into it automatically, in ~13 seconds, with no human involvement.

## Repository

- Source: this repository (private; judges added as collaborators).
- Milestone tags `milestone-1` … `milestone-7` mark each working increment.
- `docs/decisions/` — 18 recorded architecture decisions.
- `docs/sessions/` — per-milestone session reports.
- `config/prompts/` — versioned A-02 prompts (v1 → v3).
- `tests/` — 20 automated tests: `python -m pytest tests/unit -q`.

## Evidence index (submission package)

- Demo video (3 min).
- Narrative (this package, `XPRIZE-Narrative-v0_3.md`).
- Commercial evidence: workshop revenue (MX$15,300, 10 customers, Stripe→Klar),
  SROS live checkout sessions, GCP operating costs (<US$1/month).
- Pilot evidence: documented feedback from 4 PhD-level researchers; the
  0/7-validated finding and our analysis.
- Product evidence: Cloud Run logs, agent-run ledger, session screenshots.

## What AI does vs. what humans do

Gemini performs every critique (~US$0.003, 10–20s each, fully audited).
The autonomous webhook onboards paying customers with zero human steps.
Humans author questions and hold sole validation authority; the founder
designs the ontology, calibrates the agent, and runs the business.
