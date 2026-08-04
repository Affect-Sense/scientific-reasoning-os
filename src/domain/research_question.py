"""Domain objects for the Research Question slice.

Source of truth: Scientific Reasoning OS Firestore Object Model v0.1 and
PRD Core Domain Object 03 (Research Question).

Schema version: 0.1
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Firestore documents (Object Model v0.1)
# ---------------------------------------------------------------------------

class ResearchQuestionDoc(BaseModel):
    """Document at research_questions/{question_id}."""

    project_id: str
    current_version_id: str
    status: Literal[
        "draft",
        "critiqued",
        "awaiting_revision",
        "ready_for_validation",
        "validated",
    ]
    inquiry_type: str
    validated_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ResearchQuestionVersion(BaseModel):
    """Document at research_questions/{question_id}/versions/{version_id}."""

    text: str
    language: Literal["es", "en"]
    parent_version_id: Optional[str] = None
    author_type: Literal["researcher", "agent"]
    author_id: str
    change_note: Optional[str] = None
    critique_refs: list[str] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# A-02 Scientific Question Agent — structured output contract
# ---------------------------------------------------------------------------

class CritiqueFinding(BaseModel):
    criterion: Literal["clarity", "relevance", "feasibility", "falsifiability"]
    assessment: str = Field(description="Evidence-based assessment of this criterion for the submitted question text. Ground every statement in the text itself; do not invent context.")
    severity: Literal["ok", "minor", "major", "blocking"]


class MissingInformation(BaseModel):
    item: str = Field(description="A specific piece of information absent from the question that is required to assess or execute it.")
    why_needed: str


class A02CritiqueOutput(BaseModel):
    """Everything A-02 is allowed to produce for one critique pass.

    Behavioural rules (Agent Catalogue v0.1, A-02):
    - may assess clarity, relevance, feasibility, falsifiability
    - may classify inquiry type
    - must NOT declare novelty
    - must NOT invent literature, evidence, variables or context
    - missing information is reported as missing, never fabricated
    """

    inquiry_type: Literal[
        "descriptive",
        "comparative",
        "relational",
        "causal",
        "exploratory",
        "design",
        "other",
    ]
    constructs: list[str] = Field(description="Scientific constructs explicitly present or directly implied in the question text.")
    population: Optional[str] = Field(default=None, description="Population as stated in the question, or null if not stated. Never invent one.")
    context: Optional[str] = Field(default=None, description="Study context as stated, or null if not stated.")
    relationships: Optional[str] = Field(default=None, description="Relationship(s) between constructs as stated, or null.")
    findings: list[CritiqueFinding] = Field(min_length=4, max_length=4, description="Exactly one finding per criterion: clarity, relevance, feasibility, falsifiability.")
    assumptions_exposed: list[str]
    missing_information: list[MissingInformation]
    revision_prompts: list[str] = Field(description="Concrete prompts the researcher can act on to produce the next version. Only for RQ-formulation-stage defects, never for operationalisation detail.")
    operationalisation_notes: list[str] = Field(
        default_factory=list,
        description="Methodological decisions the RESEARCH DESIGN stage will need to resolve (instruments, thresholds, measurement procedures, statistical criteria, sampling). These are forward guidance for a later module, NOT defects of the research question, and must never be reasons to request revision.",
    )
    uncertainty: str = Field(description="What the agent cannot assess from the text alone and why.")
    recommended_next_event: Literal[
        "question_revision_requested",
        "question_ready_for_validation",
    ]
