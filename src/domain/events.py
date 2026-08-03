"""Event objects.

Source of truth: Scientific Reasoning OS Event Catalogue v0.1.
Events are immutable, append-only records of something that has happened.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    event_type: str
    occurred_at: datetime = Field(default_factory=utcnow)
    producer: str
    actor_type: Literal["researcher", "agent", "system"]
    actor_id: str
    project_id: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    correlation_id: str
    causation_id: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    payload: dict[str, Any] = Field(default_factory=dict)
    processing_status: str = "recorded"


# ---------------------------------------------------------------------------
# Builders — exact catalogue names and minimum payloads (Event Catalogue v0.1)
# ---------------------------------------------------------------------------

def research_question_submitted(
    *,
    project_id: str,
    question_id: str,
    version_id: str,
    text: str,
    language: str,
    researcher_id: str,
    correlation_id: str,
) -> Event:
    return Event(
        event_type="research_question_submitted",
        producer="cli",
        actor_type="researcher",
        actor_id=researcher_id,
        project_id=project_id,
        object_type="research_question",
        object_id=question_id,
        correlation_id=correlation_id,
        payload={
            "question_id": question_id,
            "version_id": version_id,
            "text": text,
            "language": language,
        },
    )


def question_critique_started(
    *,
    project_id: str,
    question_id: str,
    version_id: str,
    criteria: list[str],
    correlation_id: str,
    causation_id: str,
) -> Event:
    return Event(
        event_type="question_critique_started",
        producer="A-02",
        actor_type="agent",
        actor_id="A-02",
        project_id=project_id,
        object_type="research_question",
        object_id=question_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload={
            "version_id": version_id,
            "criteria": criteria,
        },
    )


def question_critique_created(
    *,
    project_id: str,
    question_id: str,
    version_id: str,
    findings: list[dict[str, Any]],
    evidence_refs: list[str],
    uncertainty: str,
    recommended_next_event: str,
    correlation_id: str,
    causation_id: str,
) -> Event:
    return Event(
        event_type="question_critique_created",
        producer="A-02",
        actor_type="agent",
        actor_id="A-02",
        project_id=project_id,
        object_type="research_question",
        object_id=question_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload={
            "version_id": version_id,
            "findings": findings,
            "evidence_refs": evidence_refs,
            "uncertainty": uncertainty,
            "recommended_next_event": recommended_next_event,
        },
    )
