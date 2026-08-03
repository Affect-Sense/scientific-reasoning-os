# Scientific Reasoning OS — Beta

Agentic research-support system. AffectSense, 2026.

## First slice
Rough research question → A-02 Scientific Question Agent (Gemini on Vertex AI)
→ validated ResearchQuestion object → Firestore events + audit trail.

## Run
```bash
source .venv/bin/activate
python -m src.cli.main --text "your research question" --language en
```

Source of truth: PRD v0.1, Agent Catalogue v0.1, Event Catalogue v0.1,
Firestore Object Model v0.1 (docs/).
