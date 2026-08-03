"""Offline unit tests: schemas and event builders. No network required."""
from src.domain import events as ev
from src.domain.research_question import (
    A02CritiqueOutput,
    ResearchQuestionDoc,
    ResearchQuestionVersion,
)


def test_event_chain():
    e1 = ev.research_question_submitted(
        project_id="p", question_id="q", version_id="v", text="t",
        language="en", researcher_id="genaro", correlation_id="c",
    )
    e2 = ev.question_critique_started(
        project_id="p", question_id="q", version_id="v",
        criteria=["clarity"], correlation_id="c", causation_id=e1.event_id,
    )
    assert e1.event_type == "research_question_submitted"
    assert e2.causation_id == e1.event_id
    assert e1.correlation_id == e2.correlation_id
    assert e1.payload["text"] == "t"


def test_rq_documents():
    doc = ResearchQuestionDoc(
        project_id="p", current_version_id="v", status="draft", inquiry_type="unclassified"
    )
    ver = ResearchQuestionVersion(
        text="t", language="en", author_type="researcher", author_id="genaro"
    )
    assert doc.schema_version == "0.1"
    assert ver.critique_refs == []


def test_critique_schema_enforces_four_findings():
    finding = {"criterion": "clarity", "assessment": "ok", "severity": "ok"}
    payload = {
        "inquiry_type": "causal",
        "constructs": ["x"],
        "population": None,
        "context": None,
        "relationships": None,
        "findings": [
            {**finding, "criterion": c}
            for c in ["clarity", "relevance", "feasibility", "falsifiability"]
        ],
        "assumptions_exposed": [],
        "missing_information": [],
        "revision_prompts": ["p"],
        "uncertainty": "u",
        "recommended_next_event": "question_revision_requested",
    }
    obj = A02CritiqueOutput.model_validate(payload)
    assert len(obj.findings) == 4
