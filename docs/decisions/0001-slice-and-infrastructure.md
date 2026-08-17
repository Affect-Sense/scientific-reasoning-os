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

10. Canonical health endpoint is GET /health. /healthz is intercepted by the
    Google Frontend on Cloud Run and returns 404 before reaching the
    application (verified: route present in OpenAPI, /healthz/ reached the app
    as 307, /healthz never appeared in app logs). Monitoring, load balancers
    and clients must use /health.

11. payment_confirmed and customer_onboarded are catalogue extensions mandated
    by the delivery brief; proposed for Event Catalogue v0.2. Stripe webhook
    is signature-verified, fail-closed, and idempotent (session replay never
    double-onboards).
12. Beta commercial terms: "Scientific Reasoning OS — Beta", MX$490 one-time,
    promo code SROSBETA (100%) for invited pilots. Comped checkouts fire the
    identical event chain, so onboarding evidence is uniform.
13. Watch item: A-02 recommended_next_event observed inconsistent with its own
    severities (all ok/minor but revision recommended). Fix: derive the
    recommendation deterministically from severities in code; model field
    becomes advisory. Scheduled next session.

14. Object Model v0.2 proposal (pilot-driven, 7 Aug): agent_runs should carry
    an explicit actor/customer attribution field; today ownership resolves
    only via project_id -> customers, two hops. Surfaced during the first
    pilot compliance audit (Gustavo, 3 runs, PASS).

15. Milestone 5 closed 8 Aug on evidence already banked: live customer
    completed checkout -> submit -> critique -> validate unaided
    (cus_3fdb07b3eeb3, 7 Aug); pilot completed three critique cycles across
    revisions in an unfamiliar domain (neuroimaging). Multi-step user
    outcome demonstrated by two independent real users.

16. Process defect, second occurrence (10 Aug): overlay deliveries built
    outside the repo overwrote a committed hotfix (Stripe session
    normalization), regressing the live webhook. Rule going forward: after
    any overlay unzip, run `git diff` and review before deploying; any
    hotfix made directly on this machine must be reported back to the
    engineering agent so its working copy is updated. The normalization now
    lives in the repo with a guard (hasattr check) so re-application is safe.

17. Milestone 6 closed 10 Aug: three external researchers (PhD-level) used
    the deployed system via the live funnel and delivered substantive
    documented feedback — UX audit (shipped same day), agent-rules
    compliance probe (audited: PASS), and expert-segmentation critique
    (validated the ladder positioning; Advanced Researcher Mode filed as
    post-freeze backlog). All external questions currently stop at the
    validation gate (0/5 externally validated) — open product question
    under live observation. Revenue note: all onboarding to date via promo
    code (MX$0); first real-revenue test in progress (Wave 1 emails, 10 Aug).

18. Milestone 7 closed 11 Aug on its own definition (traceability): workshop
    revenue MX$15,300 (10 customers, July 2026, Stripe -> Klar, statements
    exported); SROS beta launched 6 Aug — live-payable rail verified twice,
    9 customers onboarded via the autonomous funnel (promo-comped pilots;
    founders-price offers in market, W1 cohort deliberately held for the
    September W2 launch); AI operating cost US$0.11 for 36 audited runs;
    infra <US$20/month. Every figure exports from Stripe, Klar, GCP Billing,
    or the agent_runs ledger.

19. DEFECT identified 12 Aug: the Stripe webhook provisions an SROS workspace
    for ANY completed live checkout in the account — it does not filter by
    product. First occurrence: a W1 workshop registration (MX$900) silently
    created an SROS customer record and workspace. The buyer experienced only
    the normal workshop flow (the workshop payment link redirects to its own
    confirmation page), so the orphaned workspace is server-side only and was
    never surfaced to him; SROS will be introduced to workshop participants
    live on 22 Aug, not retroactively by message. Response: (a) the record
    (cus_bb6d73a680ed, MX$900) is classified as W1 workshop revenue and
    EXCLUDED from all SROS traction figures in the XPRIZE submission;
    (b) every new provision is verified against its Stripe line item before
    entering any count until the fix ships; (c) webhook product filter is the
    first post-freeze code change. An earlier idea to adopt the behaviour as
    "bundling policy" was rejected: a bundle requires checkout disclosure and
    a pricing decision, neither of which existed.

20. Repository made public 17 Aug 2026 for XPRIZE judging (Devpost "Try it
    out" link). The IP moat (ontology, agent/event catalogues) is not in this
    repository. Revisit visibility after judging concludes.
