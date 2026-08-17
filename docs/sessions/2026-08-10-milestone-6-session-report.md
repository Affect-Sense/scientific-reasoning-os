# Milestone 6 — Real Pilot Cohort
**Date closed:** 2026-08-10
**Git:** tag `milestone-6` (decision 17)

---

# Objective

A small real-user cohort uses the deployed system and gives feedback.

---

# The cohort

Four external PhD-level researchers engaged via the live funnel. Three
provided substantive feedback; the fourth used the system but submitted no
feedback and is not referenced individually. Naming follows written consent
(see CONSENT_STATEMENT): two testers are named with permission; the third
declined attribution and appears unnamed.

- **Dr Gustavo Padrón Rivera (Universidad de Hidalgo)** — consented, incl.
  audio: stress-tested with a deliberately vague neuroimaging question;
  three critique cycles. Probed model configuration (model, temperature,
  context handling) — answered with full transparency. A compliance audit of
  his runs against A-02's behavioural rules PASSED: the agent never invented
  an unstated population; exemplars appeared only inside revision prompts.
  Use-case in his words: refining the idea alone, before presenting to a
  team.
- **Dr Guillermo Calderón** — consented (written feedback): two rounds of
  detailed QA. Round 1 (12 points) shipped to production the same afternoon:
  loading indicator, guided intro, section explanations, question history
  list, next-step block. Round 2 surfaced a language-lock defect (fixed:
  persistent header toggle) and unlocalized severity badges (fixed), plus a
  product roadmap now in docs/POST_FREEZE_BACKLOG.md.
- **An established environmental researcher** (unnamed by choice) —
  critiqued fit rather than execution: experts want evaluation, not
  elicitation. Behaviour contradicted the complaint: three versions to
  ready-for-validation in eleven minutes. Defined the Advanced Researcher
  Mode roadmap item. No quotation is attributed.
- **Fourth researcher** — onboarded 11 Aug; payment link to first critique
  in ~60 seconds; no feedback submitted.

---

# Headline finding

For the first five days, **0 of 7 externally submitted questions were
validated** — researchers engaged deeply, then stopped at the validation
gate. An in-product explanation of validation was shipped and one pilot was
told directly the button was his. Within hours he validated his strongest
question and deliberately left three weaker ones open, then doubled usage.
Reading: the gate was under-explained (copy fixed), and validation is a
genuine scientific commitment — selective validation is the designed
behaviour. The same pilot independently proposed gating the button on
critique quality; carried as a design question, deliberately unchanged
before submission.

---

# Milestone achieved

Real researchers, real questions, documented feedback, and a
feedback-to-production loop measured in hours.
