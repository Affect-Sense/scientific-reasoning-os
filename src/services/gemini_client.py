"""Gemini client (Vertex AI mode) with schema-validated structured output.

Discipline (persona brief):
- structured output where supported;
- validate every model response before persisting;
- on validation failure retry once with repair instructions;
- otherwise raise so the caller records a failed run — never persist malformed objects.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Type, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class GeminiUsage:
    prompt_tokens: int
    output_tokens: int
    total_tokens: int


class GeminiStructuredError(RuntimeError):
    """Raised when the model cannot produce a schema-valid response after one repair retry."""


class GeminiUnavailableError(RuntimeError):
    """Raised when Vertex keeps throttling or erroring after transport retries (429/5xx)."""


RETRYABLE_CODES = {429, 500, 503}
BACKOFF_SECONDS = (2, 6)


def _error_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int):
            return v
    return None


def should_retry(exc: Exception) -> bool:
    return isinstance(exc, genai_errors.APIError) and _error_code(exc) in RETRYABLE_CODES


class GeminiClient:
    def __init__(self, project: str, location: str, model: str):
        self._client = genai.Client(vertexai=True, project=project, location=location)
        self.model = model

    def generate_structured(
        self,
        *,
        system_instruction: str,
        user_content: str,
        schema: Type[T],
        temperature: float = 0.2,
    ) -> tuple[T, GeminiUsage, str]:
        """Returns (validated object, token usage, raw response text)."""
        contents = user_content
        last_error: str | None = None

        for attempt in (1, 2):
            if attempt == 2:
                contents = (
                    user_content
                    + "\n\nYour previous response failed schema validation with this error:\n"
                    + str(last_error)
                    + "\nRespond again with ONLY a JSON object that satisfies the schema exactly."
                )
            response = None
            for t_attempt, exc_ok in enumerate([True] * len(BACKOFF_SECONDS) + [False]):
                try:
                    response = self._client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            response_schema=schema,
                            temperature=temperature,
                        ),
                    )
                    break
                except genai_errors.APIError as exc:
                    if exc_ok and should_retry(exc):
                        wait = BACKOFF_SECONDS[t_attempt]
                        log.warning("Vertex transient error %s; retry in %ss", _error_code(exc), wait)
                        time.sleep(wait)
                        continue
                    if should_retry(exc):
                        raise GeminiUnavailableError(
                            f"Vertex still unavailable after retries (code {_error_code(exc)})"
                        ) from exc
                    raise
            raw = response.text or ""
            usage = GeminiUsage(
                prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
                total_tokens=getattr(response.usage_metadata, "total_token_count", 0) or 0,
            )
            try:
                obj = schema.model_validate_json(raw)
                return obj, usage, raw
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                log.warning("Gemini structured output failed validation (attempt %s): %s", attempt, exc)

        raise GeminiStructuredError(f"Schema validation failed after repair retry: {last_error}")
