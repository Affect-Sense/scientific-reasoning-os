# ADR 0001 — First slice and infrastructure decisions (3 Aug 2026)

1. First vertical slice implements A-02 Scientific Question Agent per Agent
   Catalogue v0.1 (the persona brief's "RQ Diagnostic Agent" does not exist in
   the catalogue; catalogue wins). Events emitted: research_question_submitted,
   question_critique_started, question_critique_created — exact catalogue names.
2. Firestore database: (default), us-central1, native mode, free tier.
   Deviation from mexico-central1 residency preference because Firestore does
   not serve that region. Beta-acceptable; revisit before institutional scale.
3. Critique content is stored in agent_runs output and referenced from
   versions.critique_refs by run_id. Object Model v0.1 defines critique_refs but
   no critiques collection; propose resolution in Object Model v0.2.
4. research_projects/proj_lak2027 is bootstrapped deterministically by the CLI.
   Technical debt: project creation belongs to A-04 at Milestone 4
   (payment-linked onboarding).
5. Gemini access: google-genai SDK, Vertex mode, ADC credentials,
   gemini-2.5-flash (env-configurable). Structured output validated by Pydantic;
   one repair retry; failed runs recorded in agent_runs, never persisted as
   domain objects.

6. Repository visibility set to Private (3 Aug 2026), consistent with the
   dual-layer IP posture (secreto industrial for core engine and prompts).
   XPRIZE judges to be granted collaborator access at submission time.

7. Language strategy: system is language-parametric per submission (language
   field per RQ version); internals and schemas remain English. Beta defaults
   to "es" for the Mexican market; XPRIZE materials in English. No code change
   required for future markets beyond changing a default.
8. Prompt v3 (stage-aware severity): A-02 judges formulation-stage quality
   only; operationalisation demands route to operationalisation_notes and the
   ready_for_validation payload for the future design stage. Verified by A/B
   on identical question text under prompt_version v2 vs v3 (agent_runs).
9. HITL escalation backlog (Milestone 5): after N consecutive
   question_revision_requested on one question, emit human_review_requested
   and offer paid human assessment (existing premium mentoring product).
