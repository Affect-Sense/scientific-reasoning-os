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
from dataclasses import dataclass
from typing import Type, TypeVar

from google import genai
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
