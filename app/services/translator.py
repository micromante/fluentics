from app.config import Settings
from app.preferences import UserPreferences
from app.prompts import RESPONSE_SCHEMA, build_instructions
from app.providers import ProviderError, build_provider


class TranslationServiceError(Exception):
    """Raised when neither the primary nor fallback model can translate."""


class TranslationService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def translate(self, text: str, preferences: UserPreferences) -> dict:
        try:
            provider = build_provider(self.settings, preferences)
            return await provider.generate(
                build_instructions(preferences.prompt, preferences.direction),
                text,
                RESPONSE_SCHEMA,
            )
        except ProviderError:
            fallback = preferences.fallback_model
            if not fallback or fallback == preferences.model:
                raise TranslationServiceError from None
            try:
                fallback_preferences = preferences.model_copy(update={"model": fallback})
                provider = build_provider(self.settings, fallback_preferences)
                return await provider.generate(
                    build_instructions(fallback_preferences.prompt, fallback_preferences.direction),
                    text,
                    RESPONSE_SCHEMA,
                )
            except ProviderError:
                raise TranslationServiceError from None
