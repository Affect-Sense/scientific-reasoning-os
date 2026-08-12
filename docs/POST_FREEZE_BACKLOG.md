# SROS Post-Freeze Backlog
*Captured 11–12 Aug 2026. NOT for pre-submission work — September and beyond.*

## From Memo (Guillermo Calderón) — QA round 2, 11 Aug

**Shipped before freeze (12 Aug, rev 00019):**
- Language trap fixed: persistent header 🌐 toggle (was one-way to English).
- Severity badges localized (blocking → bloqueante in Spanish critiques).

**High value, post-freeze:**
1. Per-version critique history. Only the latest critique is shown; each
   version's critique exists (agent_runs, critique_refs) but is not surfaced.
   Researchers cannot compare versions or confirm they addressed a prior
   recommendation. UI join, no new data. Memo's strongest idea.
2. User dashboard as home page: activity overview, per-question status at a
   glance; rename the "Nueva pregunta" heading — the page is now a panel.
3. Traffic-light status colours on the panel (validated / awaiting revision /
   ready) so status reads without reading text.
4. Panel/detail consistency: "ready for validation" chip vs. non-OK criteria
   visible on the detail page — reconcile the summary signal.
5. Landing-page redirect on validation next-step (dates, contents, price,
   reserve, payment) replacing the generic WhatsApp line — ties SROS
   validation directly into the W2 workshop funnel.
6. Evidence-map explainer page.

## Validation-gate finding (deliberately unchanged before submission)
Memo independently proposed gating the validate button on critique quality.
This corroborates the pilot finding (0/7 validated for five days; first
selective validation 12 Aug after the explanation copy shipped). The gate was
left unchanged during observation; post-freeze, consider an intermediate
state between "critiqued" and "locked".

## Earlier backlog (still open)
- Advanced Researcher Mode (Celene): import literature first, accept partial
  questions, critique-first; skip elicitation scaffolding.
- A-02 persona/mascot (Memo round 1).
- Per-user rate limiting before opening to non-invited users.
- agent_runs explicit actor_id attribution (decision 14, Object Model v0.2).
- Custom domain sros.affect-sense.com (Cloud Run domain mapping).
- Cookie-based token after first visit (remove token from URL/logs).
