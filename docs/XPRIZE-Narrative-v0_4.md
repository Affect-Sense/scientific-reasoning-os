# Scientific Reasoning OS
## Gemini XPRIZE Submission Narrative (v0.4 — 12 Aug 2026)
*Finding updated with the selective-validation resolution. ~930 words.*

---

## The problem

Scientific research begins with asking the right question, yet developing a
defensible research question remains slow, manual, and unevenly available.
Researchers depend on scarce supervision and informal feedback through many
undocumented revisions. Early-career researchers — especially outside elite
institutions — often have no structured critique at the exact moment it
matters most.

## Our solution

Scientific Reasoning OS (SROS) is an agentic research environment built on
Gemini that strengthens scientific reasoning without replacing it. Its
Scientific Question Agent (A-02) critiques a researcher's question on four
formulation-stage criteria — clarity, relevance, feasibility, falsifiability
— classifies the inquiry type, exposes implicit assumptions, and proposes
concrete revisions. Every version is preserved with full lineage and
provenance notes. Methodological demands (instruments, thresholds,
measurement) are deliberately routed into non-blocking "operationalisation
notes" that feed the later design stage, because a research question is not a
methods section. The agent never declares novelty, never invents literature,
and never validates: the researcher decides, and that decision is recorded.
The product's masthead states the rule: *el agente critica; la persona
investigadora decide.*

## How AI runs the business

The commercial pipeline is autonomous end to end. A customer completes a
Stripe checkout; a signature-verified, idempotent webhook emits a
payment_confirmed event, creates the customer record, provisions a personal
research project, mints an access token, and redirects the customer into
their workspace — measured at **13 seconds, zero human involvement** (Cloud
Run logs, 7 Aug 2026), and observed as low as ~60 seconds from payment link
to first agent critique for invited researchers. Inside the product, Gemini
performs the substantive work: each critique costs **~US$0.003 and returns in
10–20 seconds**, recorded per run in an auditable ledger (model, prompt
version, tokens, latency, cost). Every state change is an append-only event
with correlation and causation chains: it is possible to show exactly what
the AI did, when, and at what cost. Total AI operating cost across the entire
beta to date: **US$0.15** for 50 agent runs. Cloud infrastructure runs
**under one US dollar per month** (GCP billing, Aug 2026).

## What humans do

The founder designs the ontology and behavioural rules, calibrates the agent,
and makes commercial decisions. Researchers author every version of their
question and hold sole validation authority. Two documented episodes show the
division working: the agent flagged that a revision had silently *broadened*
the founder's own research question while claiming to narrow it; and when the
agent conflated question formulation with study design, the fix (a
stage-aware prompt revision) was verified as a controlled A/B on identical
question text, both runs preserved in the ledger.

## What the pilots taught us — the honest headline

We invited a cohort of PhD-level researchers; four engaged substantively.
Their feedback drove same-day production changes (a full UX pass shipped
hours after one pilot's audit) and validated the product's positioning: an
expert who called the elicitation "exhausting" nonetheless took her question
through three versions to ready-for-validation in eleven minutes — the
behaviour contradicted the complaint.

The most important finding arrived in two acts, and we report both. For the
first five days, **of seven research questions submitted by external
researchers, zero were validated** — every researcher engaged deeply
(multiple revision cycles, real domain questions) and then stopped at the
gate the agent opened for them. We treated this as data: we shipped an
in-product explanation of what validation means and when it is warranted,
and told one pilot directly that the button was his. Within hours, the most
engaged pilot validated his strongest question — **and deliberately left his
three weaker ones unvalidated**, then doubled his usage. Our reading: the
gate was under-explained (a copy fix resolved that), and validation is a
genuine scientific commitment researchers do not make lightly — the agent
surfaced enough real weakness that they withheld the lock until a question
earned it. A research-support agent whose users validate *selectively* is a
more credible artifact than one they rush through; the same pilot
independently proposed gating the button on critique quality, corroborating
the design question we carry into the next iteration.

## Business viability

SROS launched commercially in beta on 6 August 2026 (product at MX$490
one-time via Stripe, live mode; a 100% founders code for invited pilots).
It connects to an existing, revenue-generating education business: the
founder's AI-for-literature-review workshops — **10 paying customers,
MX$15,300 banked in July 2026** (Stripe → Klar, statements exported), rated
10/10 — which double as the acquisition channel (academic WhatsApp networks)
and the upsell ladder: SROS is the prerequisite that produces the defensible
question the September advanced workshop assumes. Nine customers have been
provisioned through the autonomous funnel; founders-price offers are in
market.

## Category impact

Research-question formulation is a universal bottleneck with no scaled
tooling. SROS demonstrates a materially better process: structured,
criterion-based critique in the researcher's own language (Spanish-first for
Latin America, English-ready), with version-controlled provenance that makes
the reasoning inspectable — a property peer review increasingly demands of
AI-assisted work. The category's importance was underscored in August 2026
when four of Google's most senior AI leaders left to found Discovery Loop,
automating experimental *execution*; SROS addresses the complementary,
human-sovereign *formulation* stage such systems presuppose.

## Evidence of progress

Seven engineering milestones in eight days, each tagged in a private GitHub
repository with session reports and 18 recorded architecture decisions:
first slice → revision lifecycle → deployed API → autonomous onboarding →
multi-step outcomes → real pilot cohort → traceable commercial evidence.
Supporting artifacts: git history and tags; append-only event ledger;
per-run cost accounting; Cloud Run logs; screenshots of real researcher
sessions; Stripe and GCP billing exports; documented pilot feedback.

## Vision

SROS aims to become the operating system for scientific reasoning — from
question formulation through evidence mapping, design, and argument — while
keeping the scientist sovereign at every decision that is theirs. The goal is
not artificial scientists; it is better science, by more scientists, in more
places.
