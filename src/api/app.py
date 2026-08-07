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

STATUS_ES = {
    "draft": "borrador",
    "awaiting_revision": "esperando revisión",
    "ready_for_validation": "lista para validar",
    "validated": "validada",
}
CRIT_ES = {
    "clarity": "Claridad",
    "relevance": "Relevancia",
    "feasibility": "Factibilidad",
    "falsifiability": "Falsabilidad",
}


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
def ui_index(request: Request, k: str = ""):
    resolve_actor(k)
    return templates.TemplateResponse(request, "index.html", {"k": k})


@app.post("/ui/questions")
def ui_submit(k: str = "", text: str = Form(...), language: str = Form(...)):
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
    return RedirectResponse(url=f"/ui/questions/{result['question_id']}?k={k}", status_code=303)


@app.get("/ui/questions/{question_id}", response_class=HTMLResponse)
def ui_question(request: Request, question_id: str, k: str = ""):
    resolve_actor(k)
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
            "status_es": STATUS_ES.get(q["status"], q["status"]),
            "crit_es": CRIT_ES,
        },
    )


@app.post("/ui/questions/{question_id}/revise")
def ui_revise(question_id: str, k: str = "", text: str = Form(...), change_note: str = Form(...)):
    researcher_id, _ = resolve_actor(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.revise(
            question_id=question_id, text=text.strip(),
            researcher_id=researcher_id, change_note=change_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}", status_code=303)


@app.post("/ui/questions/{question_id}/validate")
def ui_validate(question_id: str, k: str = "", decision_note: str = Form(...)):
    researcher_id, _ = resolve_actor(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.validate(
            question_id=question_id, researcher_id=researcher_id, decision_note=decision_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}", status_code=303)


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
    from src.domain import events as ev
    from src.domain.events import new_id
    from src.services.firestore_repository import FirestoreRepository
    from src.settings import settings
    from datetime import datetime, timezone

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)

    # Stripe returns a StripeObject; normalize it before dictionary access.
    session = session.to_dict()

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
