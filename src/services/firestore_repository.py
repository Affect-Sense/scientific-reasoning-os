"""Firestore repository.

Discipline (persona brief + Object Model v0.1):
- validate before write (all inputs are Pydantic objects);
- preserve schema_version, timestamps, provenance;
- stable identifiers; log every write; return created IDs;
- events and agent_runs are append-only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

from src.domain.events import Event
from src.domain.research_question import ResearchQuestionDoc, ResearchQuestionVersion

log = logging.getLogger(__name__)


class FirestoreRepository:
    def __init__(self, project: str, database: str = "(default)"):
        self.db = firestore.Client(project=project, database=database)

    # -- research_projects ---------------------------------------------------

    def ensure_project(self, project_id: str, *, owner_id: str, title: str, language: str) -> str:
        ref = self.db.collection("research_projects").document(project_id)
        if not ref.get().exists:
            ref.set(
                {
                    "owner_id": owner_id,
                    "title": title,
                    "language": language,
                    "status": "active",
                    "schema_version": "0.1",
                    "created_at": datetime.now(timezone.utc),
                }
            )
            log.info("created research_projects/%s", project_id)
        return project_id

    # -- research_questions --------------------------------------------------

    def write_research_question(
        self,
        question_id: str,
        doc: ResearchQuestionDoc,
        version_id: str,
        version: ResearchQuestionVersion,
    ) -> str:
        q_ref = self.db.collection("research_questions").document(question_id)
        q_ref.set(doc.model_dump())
        q_ref.collection("versions").document(version_id).set(version.model_dump())
        log.info("wrote research_questions/%s (version %s)", question_id, version_id)
        return question_id

    def update_question_after_critique(
        self, question_id: str, *, status: str, inquiry_type: str, critique_ref: str, version_id: str
    ) -> None:
        q_ref = self.db.collection("research_questions").document(question_id)
        q_ref.update(
            {
                "status": status,
                "inquiry_type": inquiry_type,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        q_ref.collection("versions").document(version_id).update(
            {"critique_refs": firestore.ArrayUnion([critique_ref])}
        )
        log.info("updated research_questions/%s after critique (%s)", question_id, critique_ref)

    # -- events (append-only) ------------------------------------------------

    def write_event(self, event: Event) -> str:
        self.db.collection("events").document(event.event_id).set(event.model_dump())
        log.info("event %s (%s)", event.event_type, event.event_id)
        return event.event_id

    # -- agent_runs (append-only, XPRIZE evidence) --------------------------

    def write_agent_run(self, run_id: str, record: dict[str, Any]) -> str:
        self.db.collection("agent_runs").document(run_id).set(record)
        log.info("agent_run %s status=%s", run_id, record.get("status"))
        return run_id
