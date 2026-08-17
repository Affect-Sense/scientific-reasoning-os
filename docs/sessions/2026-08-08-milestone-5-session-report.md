# Milestone 5 — Multi-Step User Outcome
**Date closed:** 2026-08-08 (evidence banked 7 Aug)
**Git:** tag `milestone-5` (decision 15)

---

# Objective

Demonstrate that a user completes a meaningful multi-step sequence — not a
single agent response. The delivery brief's bar: "a chatbot demonstration is
not a beta."

---

# Evidence

Two independent real users completed multi-step workflows unaided:

1. **Live customer, full commercial-to-scientific loop (7 Aug):** completed
   a live Stripe checkout, was provisioned autonomously, submitted a research
   question, received a Spanish-language critique, and validated it as
   themselves (`question_validated`, actor = the customer). Payment → workspace
   measured at 13 seconds; the entire loop needed zero founder intervention.
2. **External pilot, iterative refinement loop (7 Aug):** a PhD researcher ran
   three critique cycles across revisions of one question in an unfamiliar
   domain (neuroimaging classification), each version preserved with
   parent lineage and change notes.

All steps are traceable in the append-only event ledger (correlation and
causation chains) and the agent-run ledger (tokens, latency, cost per run).

---

# Milestone achieved

The system supports — and real users completed — the full multi-step
workflow: enter through the funnel, submit, receive critique, revise with
provenance, and decide. Milestone closed on evidence already banked rather
than a dedicated build session; recorded as architecture decision 15.
