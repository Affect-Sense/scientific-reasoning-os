# Scientific Reasoning OS — Session Report: Milestone 2

**Date:** 4 August 2026
**Session:** Implementation session 2 (revision loop and lifecycle)
**Milestone:** M2 — Repeatable agent workflow: multiple inputs, valid traceable
outcomes, living version history
**Status:** ACHIEVED and verified on a real research question
**Git:** commit 84f414a, tag `milestone-2`, pushed to origin

---

## What was built

The complete Research Question lifecycle on top of the Milestone 1 slice:

1. **Subcommand CLI** — `submit`, `revise`, `validate`, `show` replace the
   single-purpose entry point.
2. **Reusable critique cycle** — one function drives both first submission
   and every revision: `question_critique_started` → A-02 (Gemini, schema
   validated) → `agent_runs` audit → `question_critique_created` → the
   agent's recommendation emitted as a **first-class catalogue event**
   (`question_revision_requested` with reasons and prompts, or
   `question_ready_for_validation` with a human-notice flag).
3. **Living version history** — `revise` creates a new version carrying
   `parent_version_id`, updates `current_version_id`, and re-runs the
   critique cycle; `show` renders the full lineage with per-version
   critique references.
4. **Researcher-only validation** — `validate` is a human approval point:
   it emits `question_validated` (producer: researcher), sets
   status/validated_at/locked_by, refuses re-validation of locked
   questions, and warns (but does not block) when the researcher overrides
   the agent's recommendation. Agents recommend; researchers decide.
5. **Configuration hygiene** — Gemini pricing moved from code to
   environment configuration (recorded technical-debt item cleared).

## Prompt engineering as audited product work

Three prompt versions were exercised during this session, all preserved in
the repository and all traceable per run via `prompt_version` in
`agent_runs`:

- **v1 → v2:** a Spanish-language submission produced English free-text
  (regression). v2 introduced an absolute language rule. Verified: full
  Spanish critique on re-test.
- **v2 → v3 (stage-aware severity):** v2 conflated research-question
  *formulation* with *operationalisation*, demanding instruments,
  thresholds and statistical criteria before allowing a question to reach
  validation — turning the RQ into a methods section. v3 introduces a
  STAGE RULE: major/blocking severities are reserved for genuine
  formulation defects; every operationalisation demand is routed into a
  new structured field, `operationalisation_notes`, which (a) can never be
  a revision reason and (b) can never be dropped — it rides in the
  `question_ready_for_validation` event payload as direct input to the
  future research-design stage. The calibration change was verified as a
  controlled A/B: the **identical question text** was re-critiqued under
  v2 (blocked) and v3 (ready for validation, with a healthy
  operationalisation backlog), both runs preserved in `agent_runs`.

## The workflow evidence

A real research question (`rq_0e58bd5b8ac7`, LAK 2027 study) travelled the
entire lifecycle: five researcher-authored versions with full parent
lineage and change notes; multiple critique rounds in which the agent
identified vague constructs, exposed assumptions, and — notably — caught a
revision that had silently *broadened* the question while claiming to
narrow it; and a final researcher validation lock
(`question_validated`, evt_7711ddd5658f). A second question in Spanish
(`rq_071a5d053935`) verified the language rule end to end.

## What AI did vs. what the human did

**AI (A-02):** critiqued every version against four scientific criteria at
formulation-stage calibration; classified inquiry types; exposed implicit
assumptions; separated formulation defects from operationalisation
demands; refused throughout to declare novelty, invent literature, or
validate the question itself.

**Human (founder/researcher):** authored every version of the question,
judged the agent's critiques, redesigned the agent's severity calibration
when it over-reached, and exercised the sole authority to validate and
lock. The prompt-calibration decision itself (stage-aware severity) was a
human product judgement, recorded as decision 8.

## Decisions recorded this session (docs/decisions/0001)

7. Language strategy: language-parametric per submission; internals in
   English; beta defaults Spanish (Mexico), XPRIZE materials in English.
8. Prompt v3 stage-aware severity with A/B verification.
9. HITL escalation backlog (Milestone 5): repeated revision loops emit
   `human_review_requested` and surface the existing paid human-mentoring
   product.

## Per-run economics

~15–20 s latency and ~USD 0.003 per critique (gemini-2.5-flash), recorded
per run with token counts in `agent_runs`.

## Technical debt

- Prompt v1/v2 remain in-repo (correct: versioned history), but automated
  regression tests for prompt behaviour (language, stage calibration) do
  not yet exist — currently manual.
- `question_unlocked` (returning a validated question to refinement) not
  implemented; deliberate scope cut.
- `question_components_proposed` event still deferred.
- Multi-question listing (`list` command) not implemented.

## Next milestone (M3)

Deployed API: the lifecycle becomes an HTTP service on Cloud Run so a
customer flow can reach it — prerequisite for payment-linked onboarding
(M4) and real pilot users (M6). Beta freeze: 15 August 2026.
