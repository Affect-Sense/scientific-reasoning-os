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
