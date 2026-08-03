"""CLI entry point for the RQ critique slice.

Usage:
  python -m src.cli.main --text "..." --language en
  python -m src.cli.main --file question.txt --language es
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
    logging.getLogger(__name__).info("logging to %s", logfile)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scientific Reasoning OS — RQ critique slice")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--text", help="Research question text")
    src_group.add_argument("--file", help="Path to a text file containing the question")
    parser.add_argument("--language", choices=["es", "en"], required=True)
    parser.add_argument("--project-id", default="proj_lak2027")
    parser.add_argument("--researcher-id", default="genaro")
    parser.add_argument("--change-note", default=None)
    args = parser.parse_args()

    _configure_logging()

    text = args.text if args.text else Path(args.file).read_text(encoding="utf-8").strip()
    if not text:
        print("Empty question text.", file=sys.stderr)
        return 2

    # Import after logging is configured so client libs log properly.
    from src.application.diagnose_research_question import diagnose
    from src.services.firestore_repository import FirestoreRepository

    repo = FirestoreRepository(settings.gcp_project_id, settings.firestore_database)
    repo.ensure_project(
        args.project_id,
        owner_id=args.researcher_id,
        title="LAK 2027 — Behavioural representation of learner state",
        language=args.language,
    )

    result = diagnose(
        text=text,
        language=args.language,
        researcher_id=args.researcher_id,
        project_id=args.project_id,
        change_note=args.change_note,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print(
        f"\nInspect: https://console.cloud.google.com/firestore/databases/-default-/data"
        f"?project={settings.gcp_project_id}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
