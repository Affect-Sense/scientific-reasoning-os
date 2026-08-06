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


def require_ui_key(k: str = "") -> str:
    expected = os.environ.get("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service not configured (API_KEY unset).")
    if not secrets.compare_digest(k, expected):
        raise HTTPException(status_code=401, detail="Enlace inválido. Solicita un enlace de acceso.")
    return k


@app.get("/ui", response_class=HTMLResponse)
def ui_index(request: Request, k: str = ""):
    require_ui_key(k)
    return templates.TemplateResponse(request, "index.html", {"k": k})


@app.post("/ui/questions")
def ui_submit(k: str = "", text: str = Form(...), language: str = Form(...)):
    require_ui_key(k)
    from src.application import rq_lifecycle as lifecycle
    from src.services.firestore_repository import FirestoreRepository
    from src.settings import settings

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    repo.ensure_project(
        "proj_lak2027", owner_id="genaro",
        title="LAK 2027 — Behavioural representation of learner state", language=language,
    )
    result = lifecycle.submit(
        text=text.strip(), language=language, researcher_id="pilot",
        project_id="proj_lak2027", change_note=None,
    )
    return RedirectResponse(url=f"/ui/questions/{result['question_id']}?k={k}", status_code=303)


@app.get("/ui/questions/{question_id}", response_class=HTMLResponse)
def ui_question(request: Request, question_id: str, k: str = ""):
    require_ui_key(k)
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
    require_ui_key(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.revise(
            question_id=question_id, text=text.strip(),
            researcher_id="pilot", change_note=change_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}", status_code=303)


@app.post("/ui/questions/{question_id}/validate")
def ui_validate(question_id: str, k: str = "", decision_note: str = Form(...)):
    require_ui_key(k)
    from src.application import rq_lifecycle as lifecycle

    try:
        lifecycle.validate(
            question_id=question_id, researcher_id="pilot", decision_note=decision_note.strip(),
        )
    except SystemExit as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return RedirectResponse(url=f"/ui/questions/{question_id}?k={k}", status_code=303)
