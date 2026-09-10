from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1)


class Correction(BaseModel):
    original: str
    corrected: str


class ModelResult(BaseModel):
    corrected_text: str
    translation: str
    alternatives: list[str] = Field(min_length=2, max_length=2)
    detected_language: str
    corrections: list[Correction] = Field(default_factory=list)


class TranslationResponse(BaseModel):
    corrected_text: str
    translation: str
    alternatives: list[str] = Field(default_factory=list)
    detected_language: str
    latency_ms: int
    corrections: list[Correction] = Field(default_factory=list)
