import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas import TranslationRequest, TranslationResponse
from app.preferences import UserPreferences
from app.history import HistoryEntry
from app.services.translator import TranslationServiceError

router = APIRouter()
SUPPORTED_PROVIDERS = {"openai", "claude", "gemini", "grok", "deepseek"}
ENV_KEY_FIELDS = {
    "openai": "openai_api_key",
    "claude": "anthropic_api_key",
    "gemini": "gemini_api_key",
    "grok": "xai_api_key",
    "deepseek": "deepseek_api_key",
}


class ConfigResponse(BaseModel):
    provider: str
    model: str
    fallback_model: str
    direction: str
    prompt: str
    api_keys: dict[str, str]


class ConfigUpdate(BaseModel):
    provider: str = "openai"
    model: str
    fallback_model: str = ""
    direction: str = "auto"
    prompt: str = Field(min_length=1, max_length=12000)
    api_keys: dict[str, str] = Field(default_factory=dict)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/history", response_model=list[HistoryEntry])
async def history(request: Request) -> list[HistoryEntry]:
    return request.app.state.history_store.load()


@router.get("/api/history/{entry_id}", response_model=HistoryEntry)
async def history_entry(request: Request, entry_id: str) -> HistoryEntry:
    entry = request.app.state.history_store.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    return entry


@router.delete("/api/history/{entry_id}", status_code=204)
async def delete_history_entry(request: Request, entry_id: str) -> None:
    try:
        deleted = request.app.state.history_store.delete(entry_id)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not update history") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="History entry not found")


@router.delete("/api/history", status_code=204)
async def clear_history(request: Request) -> None:
    try:
        request.app.state.history_store.clear()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not clear history") from exc


@router.get("/api/config", response_model=ConfigResponse)
async def config(request: Request) -> ConfigResponse:
    preferences = request.app.state.user_preferences
    settings = request.app.state.settings
    api_keys = {
        provider: preferences.api_key_for(provider) or getattr(settings, ENV_KEY_FIELDS[provider])
        for provider in SUPPORTED_PROVIDERS
    }
    return ConfigResponse(
        provider=preferences.provider,
        model=preferences.model,
        fallback_model=preferences.fallback_model,
        direction=preferences.direction,
        prompt=preferences.prompt,
        api_keys=api_keys,
    )


@router.put("/api/config", response_model=ConfigResponse)
async def update_config(request: Request, payload: ConfigUpdate) -> ConfigResponse:
    api_keys = request.app.state.user_preferences.api_keys.copy()
    api_keys.update({key: value.strip() for key, value in payload.api_keys.items() if value.strip()})
    preferences = UserPreferences(
        provider=payload.provider,
        model=payload.model,
        fallback_model=payload.fallback_model.strip(),
        direction=payload.direction,
        prompt=payload.prompt,
        api_keys=api_keys,
    )
    preferences.provider = preferences.provider.strip().lower()
    preferences.model = preferences.model.strip()
    preferences.prompt = preferences.prompt.strip()
    if preferences.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    if not preferences.model:
        raise HTTPException(status_code=400, detail="The model cannot be empty")
    if not preferences.fallback_model:
        raise HTTPException(status_code=400, detail="The fallback model cannot be empty")
    if preferences.direction not in {"auto", "en-es", "es-en"}:
        raise HTTPException(status_code=400, detail="Invalid translation direction")
    if not preferences.prompt:
        raise HTTPException(status_code=400, detail="The prompt cannot be empty")
    try:
        request.app.state.preferences_store.save(preferences)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not save configuration") from exc
    request.app.state.user_preferences = preferences
    return await config(request)


@router.post("/api/translate", response_model=TranslationResponse)
async def translate(request: Request, payload: TranslationRequest) -> TranslationResponse:
    settings = request.app.state.settings
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Enter some text")
    if len(text) > settings.max_text_length:
        raise HTTPException(
            status_code=413,
            detail=f"Text cannot exceed {settings.max_text_length} characters",
        )
    started = time.perf_counter()
    try:
        result = await request.app.state.translation_service.translate(
            text, request.app.state.user_preferences
        )
    except TranslationServiceError as exc:
        raise HTTPException(status_code=502, detail="The translation could not be completed") from exc

    response = TranslationResponse(
        corrected_text=result.get("corrected_text", text).strip(),
        translation=result["translation"].strip(),
        alternatives=[item.strip() for item in result["alternatives"][:2]],
        detected_language=result["detected_language"],
        latency_ms=round((time.perf_counter() - started) * 1000),
        corrections=result.get("corrections", []),
    )
    try:
        request.app.state.history_store.add(
            HistoryEntry(
                created_at=datetime.now(timezone.utc).isoformat(),
                original_text=text,
                corrected_text=response.corrected_text,
                translation=response.translation,
                alternatives=response.alternatives,
                corrections=response.corrections,
                detected_language=response.detected_language,
                provider=request.app.state.user_preferences.provider,
                model=request.app.state.user_preferences.model,
                latency_ms=response.latency_ms,
            )
        )
    except OSError:
        pass
    return response
