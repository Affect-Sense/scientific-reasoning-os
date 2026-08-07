# Milestone 4 — Payment-Linked Onboarding
**Date:** 2026-08-06 (completed live same evening)
**Git:** tag `milestone-4`; pilot-ready follow-up commit same night

---

# Objective

Implement fully autonomous customer onboarding: a Stripe Checkout completes
and the system — with no human action — confirms payment as a first-class
event, creates the customer, provisions their research workspace, and
delivers them into it.

---

# Design

- **Webhook**: `POST /webhooks/stripe`, signature-verified, fail-closed
  (503 if the signing secret is unset, 400 on bad signature), and
  **idempotent** — Stripe retries deliveries, so a replayed session never
  double-onboards a customer.
- **Onboarding chain** (all correlation-linked, append-only):
  `payment_confirmed` → `customers/{id}` record → per-customer research
  project → per-user access token → `customer_onboarded`.
- **Per-actor identity**: the UI now resolves tokens to identities. Every
  pilot's questions, versions, and validations are attributed to *them* in
  the audit trail; the founder's admin key maps to the founder.
- **Commercial terms**: "Scientific Reasoning OS — Beta", MX$490 one-time,
  promo code SROSBETA (100%) for the invited pilot cohort. Comped checkouts
  fire the identical event chain, so onboarding evidence is uniform across
  paying and invited users (decision 12).
- **`/welcome` redirect**: Stripe's after-payment redirect lands on
  `/welcome?session_id=...`, which looks up the freshly minted token and
  forwards the customer into their personal workspace; if the webhook lags
  checkout by a second, the page politely auto-refreshes.
- **Deterministic recommendation rule** (same evening, decision 13): the
  agent's recommended next event is now derived in code from the critique
  severities (any major/blocking → revision requested; otherwise ready for
  validation). The model's own recommendation field is advisory only,
  logged when it disagrees. Rationale: never use an LLM where deterministic
  validation is safer.

---

# Defects encountered and resolved

Three production defects surfaced during live integration; all three were
diagnosed and fixed by the founder:

1. **Missing `STRIPE_WEBHOOK_SECRET` in Cloud Run** → endpoint correctly
   failed closed with 503. Fix: deploy the live signing secret as an
   environment variable.
2. **Stripe SDK version mismatch** → `to_dict_recursive()` unavailable in
   the deployed library version.
3. **StripeObject vs dict** → the Checkout Session is a `StripeObject`, not
   a plain dictionary; attribute access via `.get()` raised
   `AttributeError` (HTTP 500). Fix: normalize once at the boundary —
   `session = session.to_dict()` — then treat it as data.

After the fixes: full unit suite green (15 passed), redeployed, live event
replayed successfully.

---

# Final verification (live mode, real Stripe)

Cloud Run logs, 7 Aug 2026 01:37 UTC:

```
01:37:31  GET  /welcome?session_id=cs_live_… 200   (waiting page, auto-refresh)
01:37:41  POST /webhooks/stripe 200
01:37:42  created customers/cus_3fdb07b3eeb3
01:37:42  event payment_confirmed
01:37:42  created research_projects/proj_cus_3fdb07b3eeb3
01:37:42  event customer_onboarded
01:37:44  GET  /welcome … 303 See Other
01:37:44  GET  /ui?k=…  200
```

**Thirteen seconds from completed payment to a working research
environment, zero humans involved.** The onboarded customer then submitted
a question, received a Spanish-language critique, and validated it — as
themselves (`Validada por: cus_3fdb07b3eeb3`).

---

# Evidence

- 01-Stripe-checkout.png
- 02-Provisioning-screen.png
- 03-Onboarded-user.png
- 04-Pilot-invitation-Rosy.jpeg (phone number redacted)
- 05-Pilot-invitation-Memo.jpeg (phone number redacted)
- Cloud Run log excerpt above (tokens cropped)
- Stripe live-mode records

---

# Milestone achieved

Scientific Reasoning OS now has a fully autonomous commercial pipeline:
checkout → payment confirmation → provisioning → delivery into the product,
completing the payment-to-workflow chain required by the delivery brief.
(The first vertical slice was Milestone 1; this milestone completes the
commercial pipeline around it.) Six pilot invitations issued the following
morning: Rosy, Sofía, Memo, Erika, Gustavo, Ángel.
