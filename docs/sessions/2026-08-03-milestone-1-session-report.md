# Scientific Reasoning OS — Session Report: Milestone 1

**Date:** 3 August 2026
**Session:** Implementation session 1 (first vertical slice)
**Milestone:** M1 — First running slice: input → Gemini → ResearchQuestion object → Firestore events
**Status:** ACHIEVED and verified repeatable
**Git:** commit d85ee3f, tag `milestone-1`, 21 files, 860 insertions

---

## What was built

The first end-to-end vertical slice of Scientific Reasoning OS, an agentic
system that supports researchers in producing defensible research questions
and evidence maps. The slice implements agent **A-02 Scientific Question
Agent** exactly as specified in Agent Catalogue v0.1:

1. A researcher submits a rough research question via a command-line entry point.
2. The system persists the question as a versioned `ResearchQuestion` object
   in Cloud Firestore (Object Model v0.1) and emits the catalogue event
   `research_question_submitted`.
3. Event `question_critique_started` is emitted and A-02 runs on
   **gemini-2.5-flash via Vertex AI** with a versioned, repository-stored
   prompt (`a02_critique_v1`).
4. The model's response is a schema-enforced structured output (Pydantic):
   inquiry-type classification, exactly four criterion findings (clarity,
   relevance, feasibility, falsifiability), exposed assumptions, missing
   information, revision prompts, uncertainty statement, and a recommended
   next workflow event. Invalid output triggers one repair retry; nothing
   malformed is ever persisted.
5. A complete audit record is written to `agent_runs`: agent id, model,
   prompt version, input/output references, token usage, latency, and
   estimated cost in USD.
6. The question object is updated (`status: critiqued`, `critique_refs`
   linked to the run) and `question_critique_created` is emitted with the
   catalogue payload. All three events share a correlation id and chain
   causation ids.

## What AI did vs. what the human did

**AI (A-02 / Gemini):** analysed the researcher's real LAK 2027 research
question; classified it as a specific inquiry type; assessed it against four
scientific criteria; exposed four implicit assumptions; identified missing
operationalisations (e.g. "cognitive friction events" undefined); produced
concrete revision prompts; declared its own uncertainty; and recommended
`question_revision_requested` — correctly refusing to declare novelty or
invent context, per its behavioural rules.

**Human (founder):** provisioned Google Cloud infrastructure, authored the
question, ran the pipeline, reviewed outputs, and retains the sole authority
to validate or revise the question. Agents recommend; researchers decide.

## Evidence captured

- Firestore collections: `research_projects`, `research_questions` (with
  `versions` subcollection), `events` (append-only, correlation/causation
  chained), `agent_runs` (token usage + cost per run).
- Two independent successful runs: `run_1a534e6695c7` (15:02 local) and
  `run_e0a817c1e514` (15:11 local) — repeatability condition met.
- Per-run economics: ~19–20 s model latency, **estimated cost USD 0.002983
  per critique** at gemini-2.5-flash list pricing.
- Timestamped execution logs in `logs/`; git history; console screenshots.

## Infrastructure decisions (full detail in docs/decisions/0001)

- GCP project `affectsense-openface-research`; Firestore `(default)`,
  native mode, `us-central1` (mexico-central1 not offered by Firestore;
  residency deviation recorded as beta-acceptable).
- Vertex AI enabled; ADC credentials; google-genai SDK.
- Event and object names follow the Event Catalogue and Firestore Object
  Model verbatim; the catalogues are the source of truth over ad-hoc naming.

## Technical debt (recorded, not hidden)

- `research_projects` bootstrap is a deterministic CLI step; belongs to
  A-04 Onboarding Agent at Milestone 4 (payment-linked onboarding).
- Gemini pricing constants hardcoded; move to configuration.
- No automated integration test yet; acceptance was manual dual-run.
- `question_components_proposed` event deliberately deferred to the
  revision-loop slice.

## Next slice (Milestone 2)

The revision loop: `question_revision_submitted` → new version with
`parent_version_id` → re-critique → living version history, making the
Research Question the versioned scientific object the PRD specifies.
