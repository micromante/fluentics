import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from app.prompts import INSTRUCTIONS


class UserPreferences(BaseModel):
    provider: str = "openai"
    model: str = "gpt-5.4-nano"
    fallback_model: str = "gpt-5-nano"
    direction: str = "auto"
    prompt: str = Field(default=INSTRUCTIONS, max_length=12000)
    api_keys: dict[str, str] = Field(default_factory=dict)

    def api_key_for(self, provider: str) -> str:
        return self.api_keys.get(provider, "").strip()


class PreferencesStore:
    def __init__(self, path: str | Path = "/data/settings.json"):
        self.path = Path(os.getenv("PREFERENCES_FILE", path))

    def load(self, defaults: UserPreferences) -> UserPreferences:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return UserPreferences.model_validate({**defaults.model_dump(), **data})
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return defaults

    def save(self, preferences: UserPreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(preferences.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
