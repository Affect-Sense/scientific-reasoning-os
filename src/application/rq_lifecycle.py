"""Research Question lifecycle (Milestone 2).

submit   → research_question_submitted → critique cycle
revise   → question_revision_submitted (new version, parent linked) → critique cycle
validate → question_validated (RESEARCHER ONLY — agents never lock)
show     → version history + latest critique

Critique cycle (reused by submit and revise):
  question_critique_started → A-02 (Gemini, validated) → agent_runs
  → question_critique_created → question_revision_requested
                              | question_ready_for_validation
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

PROMPT_FILE = "a02_critique_v3.md"
PROMPT_VERSION = "a02_critique_v3"
CRITERIA = ["clarity", "relevance", "feasibility", "falsifiability"]


def _clients() -> tuple[FirestoreRepository, GeminiClient]:
    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    gemini = GeminiClient(settings.gcp_project_id, settings.gcp_location, settings.gemini_model)
    return repo, gemini


def _load_prompt() -> str:
    return (settings.prompt_dir / PROMPT_FILE).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Reusable critique cycle
# ---------------------------------------------------------------------------

def run_critique_cycle(
    repo: FirestoreRepository,
    gemini: GeminiClient,
    *,
    project_id: str,
    question_id: str,
    version_id: str,
    text: str,
    language: str,
    correlation_id: str,
    causation_id: str,
) -> dict:
    e_started = ev.question_critique_started(
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        criteria=CRITERIA,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    repo.write_event(e_started)

    run_id = new_id("run")
    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()
    user_content = json.dumps(
        {"research_question_text": text, "language": language, "version_id": version_id},
        ensure_ascii=False,
    )

    try:
        critique, usage, _raw = gemini.generate_structured(
            system_instruction=_load_prompt(),
            user_content=user_content,
            schema=A02CritiqueOutput,
        )
    except GeminiStructuredError as exc:
        repo.write_agent_run(
            run_id,
            {
                "project_id": project_id,
                "agent_id": "A-02",
                "task_id": "question_critique",
                "trigger_event_id": e_started.event_id,
                "model": settings.gemini_model,
                "prompt_version": PROMPT_VERSION,
                "input_refs": [f"research_questions/{question_id}/versions/{version_id}"],
                "output_refs": [],
                "status": "failed",
                "error": str(exc),
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc),
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "schema_version": "0.1",
            },
        )
        raise

    latency_ms = int((time.monotonic() - t0) * 1000)
    estimated_cost = round(
        usage.prompt_tokens / 1e6 * settings.gemini_price_in_per_m
        + usage.output_tokens / 1e6 * settings.gemini_price_out_per_m,
        6,
    )
    repo.write_agent_run(
        run_id,
        {
            "project_id": project_id,
            "agent_id": "A-02",
            "task_id": "question_critique",
            "trigger_event_id": e_started.event_id,
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

    e_created = ev.question_critique_created(
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        findings=[f.model_dump() for f in critique.findings],
        evidence_refs=[f"agent_runs/{run_id}"],
        uncertainty=critique.uncertainty,
        recommended_next_event=critique.recommended_next_event,
        correlation_id=correlation_id,
        causation_id=e_started.event_id,
    )
    repo.write_event(e_created)

    # Deterministic recommendation (decision 13): derived in code from the
    # severities. The model's recommended_next_event is advisory only.
    has_blocker = any(f.severity in ("major", "blocking") for f in critique.findings)
    applied_recommendation = (
        "question_revision_requested" if has_blocker else "question_ready_for_validation"
    )
    if applied_recommendation != critique.recommended_next_event:
        log.warning(
            "A-02 advisory recommendation (%s) overridden by deterministic rule (%s) "
            "for %s/%s", critique.recommended_next_event, applied_recommendation,
            question_id, version_id,
        )

    # Recommendation becomes a first-class catalogue event (M2) ------------
    if applied_recommendation == "question_revision_requested":
        reasons = [
            f"{f.criterion}: {f.assessment}"
            for f in critique.findings
            if f.severity in ("major", "blocking")
        ] + [m.item for m in critique.missing_information]
        e_next = ev.question_revision_requested(
            project_id=project_id,
            question_id=question_id,
            version_id=version_id,
            reasons=reasons,
            prompts=critique.revision_prompts,
            correlation_id=correlation_id,
            causation_id=e_created.event_id,
        )
        new_status = "awaiting_revision"
    else:
        e_next = ev.question_ready_for_validation(
            project_id=project_id,
            question_id=question_id,
            version_id=version_id,
            assessments=[f.model_dump() for f in critique.findings],
            unresolved_items=[m.item for m in critique.missing_information]
            + critique.operationalisation_notes,
            correlation_id=correlation_id,
            causation_id=e_created.event_id,
        )
        new_status = "ready_for_validation"
    repo.write_event(e_next)

    repo.set_question_fields(question_id, status=new_status, inquiry_type=critique.inquiry_type)
    repo.db.collection("research_questions").document(question_id).collection(
        "versions"
    ).document(version_id).update({"critique_refs": [run_id]})

    return {
        "run_id": run_id,
        "events": [e_started.event_id, e_created.event_id, e_next.event_id],
        "status": new_status,
        "inquiry_type": critique.inquiry_type,
        "recommended_next_event": applied_recommendation,
        "model_advisory_recommendation": critique.recommended_next_event,
        "latency_ms": latency_ms,
        "token_usage": usage.total_tokens,
        "estimated_cost_usd": estimated_cost,
        "critique": critique.model_dump(),
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def submit(
    *, text: str, language: str, researcher_id: str, project_id: str, change_note: str | None
) -> dict:
    repo, gemini = _clients()
    question_id = new_id("rq")
    version_id = new_id("ver")
    correlation_id = new_id("cor")

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

    cycle = run_critique_cycle(
        repo,
        gemini,
        project_id=project_id,
        question_id=question_id,
        version_id=version_id,
        text=text,
        language=language,
        correlation_id=correlation_id,
        causation_id=e1.event_id,
    )
    return {
        "question_id": question_id,
        "version_id": version_id,
        "correlation_id": correlation_id,
        "events": [e1.event_id] + cycle["events"],
        **{k: v for k, v in cycle.items() if k != "events"},
    }


def revise(
    *, question_id: str, text: str, researcher_id: str, change_note: str | None
) -> dict:
    repo, gemini = _clients()
    q = repo.get_question(question_id)
    if q is None:
        raise SystemExit(f"research_questions/{question_id} not found")
    if q.get("status") == "validated":
        raise SystemExit(
            f"{question_id} is validated/locked. Unlocking (question_unlocked) is a "
            "separate deliberate act — not implemented in this slice."
        )
    parent_version_id = q["current_version_id"]
    parent = repo.get_version(question_id, parent_version_id) or {}
    language = parent.get("language", "en")
    project_id = q["project_id"]

    new_version_id = new_id("ver")
    correlation_id = new_id("cor")

    version = ResearchQuestionVersion(
        text=text,
        language=language,  # type: ignore[arg-type]
        parent_version_id=parent_version_id,
        author_type="researcher",
        author_id=researcher_id,
        change_note=change_note,
    )
    repo.add_version(question_id, new_version_id, version)

    e1 = ev.question_revision_submitted(
        project_id=project_id,
        question_id=question_id,
        parent_version_id=parent_version_id,
        new_version_id=new_version_id,
        text=text,
        change_note=change_note,
        researcher_id=researcher_id,
        correlation_id=correlation_id,
    )
    repo.write_event(e1)

    cycle = run_critique_cycle(
        repo,
        gemini,
        project_id=project_id,
        question_id=question_id,
        version_id=new_version_id,
        text=text,
        language=language,
        correlation_id=correlation_id,
        causation_id=e1.event_id,
    )
    return {
        "question_id": question_id,
        "version_id": new_version_id,
        "parent_version_id": parent_version_id,
        "correlation_id": correlation_id,
        "events": [e1.event_id] + cycle["events"],
        **{k: v for k, v in cycle.items() if k != "events"},
    }


def validate(*, question_id: str, researcher_id: str, decision_note: str) -> dict:
    """Human approval point. Only the researcher validates; agents never lock."""
    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    q = repo.get_question(question_id)
    if q is None:
        raise SystemExit(f"research_questions/{question_id} not found")
    if q.get("status") == "validated":
        raise SystemExit(f"{question_id} is already validated.")
    if q.get("status") != "ready_for_validation":
        log.warning(
            "Validating from status '%s' — A-02 last recommended revision. "
            "Researcher authority prevails; decision recorded.",
            q.get("status"),
        )

    version_id = q["current_version_id"]
    correlation_id = new_id("cor")
    e = ev.question_validated(
        project_id=q["project_id"],
        question_id=question_id,
        version_id=version_id,
        decision_note=decision_note,
        researcher_id=researcher_id,
        correlation_id=correlation_id,
    )
    repo.write_event(e)
    repo.set_question_fields(
        question_id,
        status="validated",
        validated_at=datetime.now(timezone.utc),
        locked_by=researcher_id,
    )
    return {
        "question_id": question_id,
        "version_id": version_id,
        "status": "validated",
        "event": e.event_id,
    }


def show(*, question_id: str) -> dict:
    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    q = repo.get_question(question_id)
    if q is None:
        raise SystemExit(f"research_questions/{question_id} not found")
    versions = repo.list_versions(question_id)
    lineage = []
    latest_critique = None
    for vid, v in versions:
        lineage.append(
            {
                "version_id": vid,
                "language": v.get("language", "es"),
                "parent_version_id": v.get("parent_version_id"),
                "author": f'{v.get("author_type")}:{v.get("author_id")}',
                "change_note": v.get("change_note"),
                "text": v.get("text"),
                "critique_refs": v.get("critique_refs", []),
            }
        )
        for run_id in v.get("critique_refs", []):
            run = repo.get_agent_run(run_id)
            if run:
                latest_critique = {"run_id": run_id, "version_id": vid, **run.get("output", {})}
    return {
        "question_id": question_id,
        "project_id": q.get("project_id"),
        "status": q.get("status"),
        "inquiry_type": q.get("inquiry_type"),
        "current_version_id": q.get("current_version_id"),
        "locked_by": q.get("locked_by"),
        "versions": lineage,
        "latest_critique": latest_critique,
    }
