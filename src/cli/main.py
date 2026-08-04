"""CLI for the Research Question lifecycle (Milestone 2).

  python -m src.cli.main submit   --file lak_question.txt --language en
  python -m src.cli.main revise   --question-id rq_x --file revised.txt --change-note "..."
  python -m src.cli.main validate --question-id rq_x --decision-note "..."
  python -m src.cli.main show     --question-id rq_x
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.settings import settings


def _configure_logging() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logfile = settings.log_dir / f"run_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(logfile)],
    )


def _read_text(args) -> str:
    text = args.text if getattr(args, "text", None) else Path(args.file).read_text(encoding="utf-8").strip()
    if not text:
        print("Empty question text.", file=sys.stderr)
        raise SystemExit(2)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Scientific Reasoning OS — RQ lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Submit a new research question")
    g = p_submit.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    p_submit.add_argument("--language", choices=["es", "en"], required=True)
    p_submit.add_argument("--project-id", default="proj_lak2027")
    p_submit.add_argument("--researcher-id", default="genaro")
    p_submit.add_argument("--change-note", default=None)

    p_rev = sub.add_parser("revise", help="Submit a revised version of an existing question")
    p_rev.add_argument("--question-id", required=True)
    g = p_rev.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    p_rev.add_argument("--researcher-id", default="genaro")
    p_rev.add_argument("--change-note", required=True,
                       help="What changed and why — this is scientific provenance, not a git nicety")

    p_val = sub.add_parser("validate", help="RESEARCHER validates and locks the question")
    p_val.add_argument("--question-id", required=True)
    p_val.add_argument("--researcher-id", default="genaro")
    p_val.add_argument("--decision-note", required=True)

    p_show = sub.add_parser("show", help="Show version history and latest critique")
    p_show.add_argument("--question-id", required=True)

    args = parser.parse_args()
    _configure_logging()

    from src.application import rq_lifecycle as app
    from src.services.firestore_repository import FirestoreRepository

    if args.command == "submit":
        repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
        repo.ensure_project(
            args.project_id,
            owner_id=args.researcher_id,
            title="LAK 2027 — Behavioural representation of learner state",
            language=args.language,
        )
        result = app.submit(
            text=_read_text(args),
            language=args.language,
            researcher_id=args.researcher_id,
            project_id=args.project_id,
            change_note=args.change_note,
        )
    elif args.command == "revise":
        result = app.revise(
            question_id=args.question_id,
            text=_read_text(args),
            researcher_id=args.researcher_id,
            change_note=args.change_note,
        )
    elif args.command == "validate":
        result = app.validate(
            question_id=args.question_id,
            researcher_id=args.researcher_id,
            decision_note=args.decision_note,
        )
    else:
        result = app.show(question_id=args.question_id)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
