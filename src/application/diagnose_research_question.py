"""The vertical slice.

input → research_question_submitted
      → question_critique_started
      → A-02 (Gemini, structured, validated)
      → agent_runs record
      → research_questions/{id} + versions/{id} (+ critique_refs)
      → question_critique_created
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from src.domain import events as ev
from src.domain.events import new_id
from src.domain.research_question import (
    A02CritiqueOutput,
    ResearchQuestionDoc,
    ResearchQuestionVersion,
)
from src.services.firestore_repository import FirestoreRepository
from src.services.gemini_client import GeminiClient, GeminiStructuredError
from src.settings import settings

log = logging.getLogger(__name__)

PROMPT_FILE = "a02_critique_v1.md"
PROMPT_VERSION = "a02_critique_v1"
CRITERIA = ["clarity", "relevance", "feasibility", "falsifiability"]

# Vertex AI list price, gemini-2.5-flash, USD per 1M tokens (config, not code, later)
PRICE_IN_PER_M = 0.30
PRICE_OUT_PER_M = 2.50


def _load_prompt() -> str:
    return (settings.prompt_dir / PROMPT_FILE).read_text(encoding="utf-8")


def diagnose(
    *,
    text: str,
    language: str,
    researcher_id: str,
    project_id: str,
    change_note: str | None = None,
) -> dict:
    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    gemini = GeminiClient(settings.gcp_project_id, settings.gcp_location, settings.gemini_model)

    question_id = new_id("rq")
    version_id = new_id("ver")
    correlation_id = new_id("cor")
    run_id = new_id("run")

    # 1. Persist the submitted question (Draft) ------------------------------
    doc = ResearchQuestionDoc(
        project_id=project_id,
        current_version_id=version_id,
        status="draft",
        inquiry_type="unclassified",
    )
    version = ResearchQuestionVersion(
        text=text,
        language=language,  # type: ignore[arg-type]
        author_type="researcher",
        author_id=researcher_id,
        change_note=change_note,
    )
    repo.write_research_question(question_id, doc, version_id, version)

    e1 = ev.research_question_submitted(
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        text=text,
        language=language,
        researcher_id=researcher_id,
        correlation_id=correlation_id,
    )
    repo.write_event(e1)

    # 2. Critique started ----------------------------------------------------
    e2 = ev.question_critique_started(
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        criteria=CRITERIA,
        correlation_id=correlation_id,
        causation_id=e1.event_id,
    )
    repo.write_event(e2)

    # 3. Run A-02 ------------------------------------------------------------
    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()
    system_prompt = _load_prompt()
    user_content = json.dumps(
        {"research_question_text": text, "language": language, "version_id": version_id},
        ensure_ascii=False,
    )

    try:
        critique, usage, raw = gemini.generate_structured(
            system_instruction=system_prompt,
            user_content=user_content,
            schema=A02CritiqueOutput,
        )
    except GeminiStructuredError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        repo.write_agent_run(
            run_id,
            {
                "project_id": project_id,
                "agent_id": "A-02",
                "task_id": "question_critique",
                "trigger_event_id": e2.event_id,
                "model": settings.gemini_model,
                "prompt_version": PROMPT_VERSION,
                "input_refs": [f"research_questions/{question_id}/versions/{version_id}"],
                "output_refs": [],
                "status": "failed",
                "error": str(exc),
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc),
                "latency_ms": latency_ms,
                "schema_version": "0.1",
            },
        )
        log.error("A-02 run %s FAILED: %s", run_id, exc)
        raise

    latency_ms = int((time.monotonic() - t0) * 1000)
    estimated_cost = round(
        usage.prompt_tokens / 1e6 * PRICE_IN_PER_M + usage.output_tokens / 1e6 * PRICE_OUT_PER_M,
        6,
    )

    # 4. Evidence: agent_runs ------------------------------------------------
    repo.write_agent_run(
        run_id,
        {
            "project_id": project_id,
            "agent_id": "A-02",
            "task_id": "question_critique",
            "trigger_event_id": e2.event_id,
            "model": settings.gemini_model,
            "prompt_version": PROMPT_VERSION,
            "input_refs": [f"research_questions/{question_id}/versions/{version_id}"],
            "output_refs": [f"agent_runs/{run_id}"],
            "output": critique.model_dump(),
            "confidence": None,
            "status": "completed",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc),
            "latency_ms": latency_ms,
            "token_usage": {
                "prompt_tokens": usage.prompt_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            },
            "estimated_cost_usd": estimated_cost,
            "schema_version": "0.1",
        },
    )

    # 5. Update the question object -----------------------------------------
    repo.update_question_after_critique(
        question_id,
        status="critiqued",
        inquiry_type=critique.inquiry_type,
        critique_ref=run_id,
        version_id=version_id,
    )

    # 6. Critique created event ----------------------------------------------
    e3 = ev.question_critique_created(
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        findings=[f.model_dump() for f in critique.findings],
        evidence_refs=[f"agent_runs/{run_id}"],
        uncertainty=critique.uncertainty,
        recommended_next_event=critique.recommended_next_event,
        correlation_id=correlation_id,
        causation_id=e2.event_id,
    )
    repo.write_event(e3)

    return {
        "question_id": question_id,
        "version_id": version_id,
        "run_id": run_id,
        "correlation_id": correlation_id,
        "events": [e1.event_id, e2.event_id, e3.event_id],
        "inquiry_type": critique.inquiry_type,
        "recommended_next_event": critique.recommended_next_event,
        "latency_ms": latency_ms,
        "token_usage": usage.total_tokens,
        "estimated_cost_usd": estimated_cost,
        "critique": critique.model_dump(),
    }
