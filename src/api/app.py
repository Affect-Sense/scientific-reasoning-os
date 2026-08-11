"""HTTP API for the Research Question lifecycle (Milestone 3).

The same four operations as the CLI, as a Cloud Run service:

  GET  /healthz
  POST /questions                      (submit)
  POST /questions/{question_id}/revisions   (revise)
  POST /questions/{question_id}/validate    (validate — researcher only)
  GET  /questions/{question_id}             (show)

Auth: shared API key in the X-API-Key header, value from the API_KEY
environment variable. Fail closed: if API_KEY is unset, every request is
rejected. Per-user tokens arrive with Milestone 4 onboarding.
"""
from __future__ import annotations

import logging
import os
import secrets
import sys
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

app = FastAPI(title="Scientific Reasoning OS — Beta API", version="0.3.0")


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service not configured (API_KEY unset).")
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


class SubmitRequest(BaseModel):
    text: str = Field(min_length=10)
    language: Literal["es", "en"]
    project_id: str = "proj_lak2027"
    researcher_id: str = "genaro"
    change_note: Optional[str] = None


class ReviseRequest(BaseModel):
    text: str = Field(min_length=10)
    researcher_id: str = "genaro"
    change_note: str = Field(min_length=5, description="Scientific provenance: what changed and why.")


class ValidateRequest(BaseModel):
    researcher_id: str = "genaro"
    decision_note: str = Field(min_length=5)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "sros-api", "version": "0.3.0"}


@app.post("/questions", dependencies=[Depends(require_api_key)])
def submit_question(req: SubmitRequest) -> dict:
    from src.application import rq_lifecycle as lifecycle
    from src.services.firestore_repository import FirestoreRepository
    from src.settings import settings

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    repo.ensure_project(
        req.project_id,
        owner_id=req.researcher_id,
        title="LAK 2027 — Behavioural representation of learner state",
        language=req.language,
    )
    return lifecycle.submit(
        text=req.text,
        language=req.language,
        researcher_id=req.researcher_id,
        project_id=req.project_id,
        change_note=req.change_note,
    )


@app.post("/questions/{question_id}/revisions", dependencies=[Depends(require_api_key)])
def revise_question(question_id: str, req: ReviseRequest) -> dict:
    from src.application import rq_lifecycle as lifecycle

    try:
        return lifecycle.revise(
            question_id=question_id,
            text=req.text,
            researcher_id=req.researcher_id,
            change_note=req.change_note,
        )
    except SystemExit as exc:  # lifecycle uses SystemExit for domain refusals
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/questions/{question_id}/validate", dependencies=[Depends(require_api_key)])
def validate_question(question_id: str, req: ValidateRequest) -> dict:
    from src.application import rq_lifecycle as lifecycle

    try:
        return lifecycle.validate(
            question_id=question_id,
            researcher_id=req.researcher_id,
            decision_note=req.decision_note,
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/questions/{question_id}", dependencies=[Depends(require_api_key)])
def show_question(question_id: str) -> dict:
    from src.application import rq_lifecycle as lifecycle

    try:
        return lifecycle.show(question_id=question_id)
    except SystemExit as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# UI half-slice (Milestone 5 front half) — server-rendered, Spanish-first.
# Access: ?k=<API_KEY> query token for pilot links. Per-user tokens: M4.
# ---------------------------------------------------------------------------
from pathlib import Path

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

UI_STR = {
    "es": {
        "status": {"draft": "borrador", "awaiting_revision": "esperando revisión",
                   "ready_for_validation": "lista para validar", "validated": "validada"},
        "crit": {"clarity": "Claridad", "relevance": "Relevancia",
                 "feasibility": "Factibilidad", "falsifiability": "Falsabilidad"},
        "strapline": "No inventa literatura. No decide por ti.",
        "intro_line": "Convierte una idea en bruto en una pregunta de investigación defendible. El agente critica. Tú decides.",
        "workspace": "Tu espacio de trabajo",
        "your_questions": "Tus preguntas",
        "new_q": "Nueva pregunta", "first_q": "Envía tu primera pregunta",
        "q_label": "Pregunta de investigación",
        "q_help": "Escríbela como la tengas hoy. No necesita estar perfecta — para eso es la crítica.",
        "q_placeholder": "Escribe aquí tu pregunta de investigación (borrador está bien)",
        "critique_lang": "Idioma de la crítica",
        "submit_btn": "Enviar para crítica",
        "state": "Estado", "inquiry": "Tipo de indagación", "validated_by": "Validada por",
        "history": "Historial de versiones",
        "history_help": "Cada versión de tu pregunta queda guardada con su nota de cambio — tu bitácora de cómo evolucionó el razonamiento.",
        "current": "(actual)", "author": "Autor",
        "critique_h": "Última crítica de A-02",
        "critique_help": "Cuatro criterios con severidad (ok / minor / major). Supuestos: lo que tu pregunta da por sentado. Información faltante: lo que el agente necesitaría y tú no has dicho — se agrega escribiéndolo en tu siguiente revisión. Sugerencias de revisión: acciones concretas para la próxima versión. Notas para diseño: decisiones de método que vendrán después — no bloquean. Incertidumbre: lo que el agente honestamente no puede juzgar.",
        "assumptions": "Supuestos implícitos", "missing": "Información faltante (etapa de formulación)",
        "prompts_h": "Sugerencias de revisión", "opnotes": "Notas para la etapa de diseño (no bloquean la validación)",
        "uncertainty": "Incertidumbre declarada",
        "locked_notice": "Esta pregunta está <strong>validada y bloqueada</strong>. Desbloquearla será un acto deliberado en una versión futura del sistema.",
        "next_h": "¿Y ahora qué?",
        "next_body": "Con una pregunta defendible, el siguiente paso es el mapa de evidencia: qué se sabe, qué no, y dónde está tu hueco. Ese es exactamente el punto de partida del <strong>Taller Avanzado</strong> de AffectSense (septiembre). Escríbenos por WhatsApp para reservar tu lugar.",
        "revise_h": "Enviar una revisión",
        "revise_help": "Reescribe tu pregunta incorporando lo que decidas de la crítica. La nota de cambio (qué cambiaste y por qué) es tu procedencia científica.",
        "new_version_ph": "Nueva versión de tu pregunta",
        "change_note_ph": "Nota de cambio: qué cambiaste y por qué (procedencia científica)",
        "revise_btn": "Enviar revisión para crítica",
        "validate_h": "Validar y bloquear",
        "validate_help": "¿Cuándo está lista? Cuando el estado diga <strong>“lista para validar”</strong> (sin hallazgos major), o antes si tú lo decides — la autoridad es tuya y tu nota de decisión queda registrada.",
        "validate_warn": "A-02 recomendó revisar. Puedes validar de todas formas: la decisión es tuya y quedará registrada.",
        "decision_ph": "Nota de decisión (por qué la validas)",
        "validate_btn": "Validar como persona investigadora",
        "back": "← Nueva pregunta",
        "busy_title": "El agente está analizando tu pregunta…",
        "busy_body": "Esto toma entre 10 y 30 segundos. Tu petición ya fue recibida — no cierres la página.",
        "footer": "Powered by Gemini 2.5 Flash (Vertex AI) · Temperatura 0.2 · Cada corrida queda auditada (versión del prompt, tokens, costo)",
        "process": "El proceso: <strong>1)</strong> escribes tu pregunta (un borrador está perfecto), <strong>2)</strong> el agente la evalúa en cuatro criterios y te señala supuestos, información faltante y sugerencias, <strong>3)</strong> la revisas cuantas veces quieras (cada versión queda guardada), y <strong>4)</strong> cuando tú decidas, la validas.",
        "version_s": "versión(es)",
    },
    "en": {
        "status": {"draft": "draft", "awaiting_revision": "awaiting revision",
                   "ready_for_validation": "ready for validation", "validated": "validated"},
        "crit": {"clarity": "Clarity", "relevance": "Relevance",
                 "feasibility": "Feasibility", "falsifiability": "Falsifiability"},
        "strapline": "It doesn't invent literature. It doesn't decide for you.",
        "intro_line": "Turn a rough idea into a defensible research question. The agent critiques. You decide.",
        "workspace": "Your workspace",
        "your_questions": "Your questions",
        "new_q": "New question", "first_q": "Submit your first question",
        "q_label": "Research question",
        "q_help": "Write it as you have it today. It doesn't need to be perfect — that's what the critique is for.",
        "q_placeholder": "Write your research question here (a draft is fine)",
        "critique_lang": "Critique language",
        "submit_btn": "Submit for critique",
        "state": "Status", "inquiry": "Inquiry type", "validated_by": "Validated by",
        "history": "Version history",
        "history_help": "Every version of your question is preserved with its change note — the log of how your reasoning evolved.",
        "current": "(current)", "author": "Author",
        "critique_h": "Latest critique from A-02",
        "critique_help": "Four criteria with severity (ok / minor / major). Implicit assumptions: what your question takes for granted. Missing information: what the agent would need and you haven't stated — add it by writing it into your next revision. Revision suggestions: concrete actions for the next version. Design-stage notes: method decisions that come later — they never block. Declared uncertainty: what the agent honestly cannot judge.",
        "assumptions": "Implicit assumptions", "missing": "Missing information (formulation stage)",
        "prompts_h": "Revision suggestions", "opnotes": "Design-stage notes (non-blocking)",
        "uncertainty": "Declared uncertainty",
        "locked_notice": "This question is <strong>validated and locked</strong>. Unlocking will be a deliberate act in a future version of the system.",
        "next_h": "What's next?",
        "next_body": "With a defensible question, the next step is the evidence map: what is known, what isn't, and where your gap lies. That is exactly where AffectSense's <strong>Advanced Workshop</strong> (September) begins.",
        "revise_h": "Submit a revision",
        "revise_help": "Rewrite your question incorporating what you take from the critique. The change note (what changed and why) is your scientific provenance.",
        "new_version_ph": "New version of your question",
        "change_note_ph": "Change note: what you changed and why (scientific provenance)",
        "revise_btn": "Submit revision for critique",
        "validate_h": "Validate and lock",
        "validate_help": "When is it ready? When the status reads <strong>“ready for validation”</strong> (no major findings) — or earlier if you so decide. The authority is yours, and your decision note is recorded.",
        "validate_warn": "A-02 recommended revising. You may validate anyway: the decision is yours and will be recorded.",
        "decision_ph": "Decision note (why you are validating)",
        "validate_btn": "Validate as the researcher",
        "back": "← New question",
        "busy_title": "The agent is analysing your question…",
        "busy_body": "This takes 10–30 seconds. Your request has been received — don't close the page.",
        "footer": "Powered by Gemini 2.5 Flash (Vertex AI) · Temperature 0.2 · Every run is audited (prompt version, tokens, cost)",
        "process": "The process: <strong>1)</strong> write your question (a draft is perfect), <strong>2)</strong> the agent evaluates it on four criteria and flags assumptions, missing information and suggestions, <strong>3)</strong> revise as many times as you like (every version is preserved), and <strong>4)</strong> when you decide, validate it.",
        "version_s": "version(s)",
    },
}


def pick_lang(lang: str = "") -> str:
    return "en" if lang == "en" else "es"


def resolve_actor(k: str = "") -> tuple[str, str]:
    """Returns (researcher_id, project_id) for a UI access token.

    Admin: the shared API_KEY → founder identity, LAK project.
    Pilot/customer: per-user token minted at payment_confirmed → own project.
    Fail closed when unconfigured; 401 otherwise.
    """
    expected = os.environ.get("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service not configured (API_KEY unset).")
    if k and secrets.compare_digest(k, expected):
        return "genaro", "proj_lak2027"
    if k:
        try:
            from src.services.firestore_repository import FirestoreRepository
            from src.settings import settings

            repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
            found = repo.get_customer_by_token(k)
        except Exception:
            log.exception("customer token lookup failed; failing closed")
            found = None
        if found:
            customer_id, _rec = found
            return customer_id, f"proj_{customer_id}"
    raise HTTPException(status_code=401, detail="Enlace inválido. Solicita un enlace de acceso.")


@app.get("/ui", response_class=HTMLResponse)
def ui_index(request: Request, k: str = "", lang: str = ""):
    _researcher_id, project_id = resolve_actor(k)
    L = pick_lang(lang)
    questions = []
    try:
        from src.services.firestore_repository import FirestoreRepository
        from src.settings import settings

        repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
        docs = (
            repo.db.collection("research_questions")
            .where("project_id", "==", project_id)
            .stream()
        )
        for d in docs:
            q = d.to_dict()
            versions = list(
                repo.db.collection("research_questions").document(d.id)
                .collection("versions").stream()
            )
            current = next(
                (v.to_dict() for v in versions if v.id == q.get("current_version_id")), None
            )
            text = (current or {}).get("text", "")
            questions.append(
                {
                    "id": d.id,
                    "text_preview": text[:110] + ("…" if len(text) > 110 else ""),
                    "status_es": UI_STR[L]["status"].get(q.get("status"), q.get("status")),
                    "n_versions": len(versions),
                    "updated_at": str(q.get("updated_at", "")),
                }
            )
        questions.sort(key=lambda x: x["updated_at"], reverse=True)
    except Exception:
        log.exception("question list failed; rendering without it")
    return templates.TemplateResponse(request, "index.html", {"k": k, "questions": questions, "t": UI_STR[L], "lang": L})


@app.post("/ui/questions")
def ui_submit(k: str = "", lang: str = "", text: str = Form(...), language: str = Form(...)):
    researcher_id, project_id = resolve_actor(k)
    from src.application import rq_lifecycle as lifecycle
    from src.services.firestore_repository import FirestoreRepository
    from src.settings import settings

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    repo.ensure_project(
        project_id, owner_id=researcher_id,
        title=f"Proyecto de investigación — {researcher_id}", language=language,
    )
    result = lifecycle.submit(
        text=text.strip(), language=language, researcher_id=researcher_id,
        project_id=project_id, change_note=None,
    )
    L = pick_lang(lang)
    return RedirectResponse(url=f"/ui/questions/{result['question_id']}?k={k}&lang={L}", status_code=303)


@app.get("/ui/questions/{question_id}", response_class=HTMLResponse)
def ui_question(request: Request, question_id: str, k: str = "", lang: str = ""):
    resolve_actor(k)
    L = pick_lang(lang)
    from src.application import rq_lifecycle as lifecycle

    try:
        q = lifecycle.show(question_id=question_id)
    except SystemExit as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    current_text = ""
    for v in q["versions"]:
        if v["version_id"] == q["current_version_id"]:
            current_text = v["text"]
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "k": k, "q": q, "c": q.get("latest_critique"),
            "current_text": current_text,
            "status_es": UI_STR[L]["status"].get(q["status"], q["status"]),
            "crit_es": UI_STR[L]["crit"],
            "t": UI_STR[L], "lang": L,
        },
    )


@app.post("/ui/questions/{question_id}/revise")
def ui_revise(question_id: str, k: str = "", lang: str = "", text: str = Form(...), change_note: str = Form(...)):
    researcher_id, _ = resolve_actor(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.revise(
            question_id=question_id, text=text.strip(),
            researcher_id=researcher_id, change_note=change_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}&lang={pick_lang(lang)}", status_code=303)


@app.post("/ui/questions/{question_id}/validate")
def ui_validate(question_id: str, k: str = "", lang: str = "", decision_note: str = Form(...)):
    researcher_id, _ = resolve_actor(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.validate(
            question_id=question_id, researcher_id=researcher_id, decision_note=decision_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}&lang={pick_lang(lang)}", status_code=303)


# ---------------------------------------------------------------------------
# Stripe webhook (Milestone 4): payment_confirmed → customer → token → project
# ---------------------------------------------------------------------------
import stripe as stripe_lib


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET unset.")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe_lib.Webhook.construct_event(payload, signature, secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.")

    if event["type"] != "checkout.session.completed":
        return {"received": True, "ignored": event["type"]}

    session = event["data"]["object"]
    if hasattr(session, "to_dict"):
        session = session.to_dict()
    from src.domain import events as ev
    from src.domain.events import new_id
    from src.services.firestore_repository import FirestoreRepository
    from src.settings import settings
    from datetime import datetime, timezone

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)

    # Idempotency: Stripe retries webhooks; never double-onboard.
    existing = repo.get_customer_by_session(session["id"])
    if existing:
        log.info("webhook replay for session %s -> customers/%s (noop)", session["id"], existing)
        return {"received": True, "customer_id": existing, "replay": True}

    customer_id = new_id("cus")
    access_token = secrets.token_urlsafe(24)
    project_id = f"proj_{customer_id}"
    correlation_id = new_id("cor")
    email = (session.get("customer_details") or {}).get("email") or session.get("customer_email") or ""
    name = (session.get("customer_details") or {}).get("name") or ""

    repo.create_customer(
        customer_id,
        {
            "email": email,
            "name": name,
            "stripe_session_id": session["id"],
            "stripe_customer_id": session.get("customer"),
            "amount_total": session.get("amount_total"),
            "currency": session.get("currency"),
            "payment_status": session.get("payment_status"),
            "access_token": access_token,
            "project_id": project_id,
            "status": "active",
            "schema_version": "0.1",
            "created_at": datetime.now(timezone.utc),
        },
    )
    e_pay = ev.payment_confirmed(
        project_id=project_id,
        customer_id=customer_id,
        stripe_session_id=session["id"],
        amount_total=session.get("amount_total") or 0,
        currency=session.get("currency") or "mxn",
        payment_status=session.get("payment_status") or "unknown",
        customer_email=email,
        correlation_id=correlation_id,
    )
    repo.write_event(e_pay)
    repo.ensure_project(
        project_id, owner_id=customer_id,
        title=f"Proyecto de investigación — {name or email or customer_id}", language="es",
    )
    e_onb = ev.customer_onboarded(
        project_id=project_id, customer_id=customer_id,
        correlation_id=correlation_id, causation_id=e_pay.event_id,
    )
    repo.write_event(e_onb)
    log.info("onboarded customers/%s (project %s) from session %s", customer_id, project_id, session["id"])
    return {"received": True, "customer_id": customer_id}


# ---------------------------------------------------------------------------
# Post-checkout welcome: Stripe redirects here; we forward to the pilot's
# personal tokenized UI link. Webhook may lag checkout by a second or two,
# so unknown sessions get a brief auto-refresh instead of an error.
# ---------------------------------------------------------------------------
@app.get("/welcome", response_class=HTMLResponse)
def welcome(session_id: str = ""):
    if session_id:
        try:
            from src.services.firestore_repository import FirestoreRepository
            from src.settings import settings

            repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
            docs = list(
                repo.db.collection("customers")
                .where("stripe_session_id", "==", session_id)
                .limit(1)
                .stream()
            )
            if docs:
                token = docs[0].to_dict().get("access_token", "")
                if token:
                    return RedirectResponse(url=f"/ui?k={token}", status_code=303)
        except Exception:
            log.exception("welcome lookup failed")
    return HTMLResponse(
        """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
        <meta http-equiv="refresh" content="3">
        <title>Preparando tu acceso…</title></head>
        <body style="font-family:sans-serif;max-width:640px;margin:4rem auto;">
        <h1>Preparando tu acceso…</h1>
        <p>Estamos creando tu espacio de trabajo. Esta página se actualizará
        automáticamente en unos segundos.</p></body></html>"""
    )
