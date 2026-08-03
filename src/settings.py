"""Environment configuration. Reads .env at repo root."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    gcp_project_id: str = os.environ.get("GCP_PROJECT_ID", "affectsense-openface-research")
    gcp_location: str = os.environ.get("GCP_LOCATION", "us-central1")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    firestore_database: str = os.environ.get("FIRESTORE_DATABASE", "(default)")
    prompt_dir: Path = REPO_ROOT / "config" / "prompts"
    log_dir: Path = REPO_ROOT / "logs"


settings = Settings()
settings.log_dir.mkdir(exist_ok=True)
