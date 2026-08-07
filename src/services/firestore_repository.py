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

    # -- reads and version lifecycle (Milestone 2) ---------------------------

    def get_question(self, question_id: str) -> dict[str, Any] | None:
        snap = self.db.collection("research_questions").document(question_id).get()
        return snap.to_dict() if snap.exists else None

    def get_version(self, question_id: str, version_id: str) -> dict[str, Any] | None:
        snap = (
            self.db.collection("research_questions")
            .document(question_id)
            .collection("versions")
            .document(version_id)
            .get()
        )
        return snap.to_dict() if snap.exists else None

    def list_versions(self, question_id: str) -> list[tuple[str, dict[str, Any]]]:
        col = (
            self.db.collection("research_questions")
            .document(question_id)
            .collection("versions")
            .order_by("created_at")
        )
        return [(d.id, d.to_dict()) for d in col.stream()]

    def add_version(
        self, question_id: str, version_id: str, version: ResearchQuestionVersion
    ) -> str:
        q_ref = self.db.collection("research_questions").document(question_id)
        q_ref.collection("versions").document(version_id).set(version.model_dump())
        q_ref.update(
            {
                "current_version_id": version_id,
                "status": "draft",
                "updated_at": datetime.now(timezone.utc),
            }
        )
        log.info("added version %s to research_questions/%s (now current)", version_id, question_id)
        return version_id

    def set_question_fields(self, question_id: str, **fields: Any) -> None:
        fields["updated_at"] = datetime.now(timezone.utc)
        self.db.collection("research_questions").document(question_id).update(fields)
        log.info("updated research_questions/%s: %s", question_id, list(fields.keys()))

    def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        snap = self.db.collection("agent_runs").document(run_id).get()
        return snap.to_dict() if snap.exists else None

    # -- customers (Milestone 4) --------------------------------------------

    def create_customer(self, customer_id: str, record: dict[str, Any]) -> str:
        self.db.collection("customers").document(customer_id).set(record)
        log.info("created customers/%s", customer_id)
        return customer_id

    def get_customer_by_token(self, token: str) -> tuple[str, dict[str, Any]] | None:
        docs = list(
            self.db.collection("customers")
            .where("access_token", "==", token)
            .where("status", "==", "active")
            .limit(1)
            .stream()
        )
        if not docs:
            return None
        return docs[0].id, docs[0].to_dict()

    def get_customer_by_session(self, stripe_session_id: str) -> str | None:
        docs = list(
            self.db.collection("customers")
            .where("stripe_session_id", "==", stripe_session_id)
            .limit(1)
            .stream()
        )
        return docs[0].id if docs else None
