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


def test_revision_loop_event_builders():
    e_req = ev.question_revision_requested(
        project_id="p", question_id="q", version_id="v1",
        reasons=["r"], prompts=["do x"], correlation_id="c", causation_id="e3",
    )
    e_sub = ev.question_revision_submitted(
        project_id="p", question_id="q", parent_version_id="v1",
        new_version_id="v2", text="t2", change_note="cn",
        researcher_id="genaro", correlation_id="c2",
    )
    e_ready = ev.question_ready_for_validation(
        project_id="p", question_id="q", version_id="v2",
        assessments=[{"criterion": "clarity"}], unresolved_items=[],
        correlation_id="c2", causation_id="e",
    )
    e_val = ev.question_validated(
        project_id="p", question_id="q", version_id="v2",
        decision_note="ok", researcher_id="genaro", correlation_id="c3",
    )
    assert e_req.event_type == "question_revision_requested"
    assert e_req.actor_type == "agent"
    assert e_sub.payload["parent_version_id"] == "v1"
    assert e_sub.actor_type == "researcher"
    assert e_ready.payload["requires_human_notice"] is True
    assert e_val.actor_type == "researcher" and e_val.producer == "cli"


def test_version_parent_link():
    v2 = ResearchQuestionVersion(
        text="t2", language="en", parent_version_id="v1",
        author_type="researcher", author_id="genaro", change_note="refined",
    )
    assert v2.parent_version_id == "v1"
