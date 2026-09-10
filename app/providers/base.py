import json
from typing import Protocol

from app.schemas import ModelResult


class ProviderError(Exception):
    """Raised when a provider cannot return a valid translation result."""


class LLMProvider(Protocol):
    async def generate(self, instructions: str, text: str, schema: dict) -> dict: ...


def parse_result(raw_text: str) -> dict:
    try:
        result = ModelResult.model_validate(json.loads(raw_text))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ProviderError("Provider returned invalid structured output") from exc
    if not result.translation.strip():
        raise ProviderError("Provider returned an empty translation")
    return result.model_dump()

