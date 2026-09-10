import json
import os
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas import Correction


class HistoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str
    original_text: str
    corrected_text: str
    translation: str
    alternatives: list[str] = Field(min_length=2, max_length=2)
    corrections: list[Correction] = Field(default_factory=list)
    detected_language: str
    provider: str
    model: str
    latency_ms: int


class HistoryStore:
    def __init__(self, path: str | Path = "/data/history.json"):
        self.path = Path(os.getenv("HISTORY_FILE", path))

    def load(self) -> list[HistoryEntry]:
        try:
            raw_entries = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw_entries, list):
                return []
            return [HistoryEntry.model_validate(entry) for entry in raw_entries]
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return []

    def add(self, entry: HistoryEntry) -> None:
        self._save([entry, *self.load()])

    def get(self, entry_id: str) -> HistoryEntry | None:
        return next((entry for entry in self.load() if entry.id == entry_id), None)

    def delete(self, entry_id: str) -> bool:
        entries = self.load()
        remaining = [entry for entry in entries if entry.id != entry_id]
        if len(remaining) == len(entries):
            return False
        self._save(remaining)
        return True

    def clear(self) -> None:
        self._save([])

    def _save(self, entries: list[HistoryEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([entry.model_dump() for entry in entries], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
