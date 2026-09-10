from app.config import Settings
from app.preferences import UserPreferences
from app.providers.base import ProviderError
from app.providers.claude import ClaudeProvider
from app.providers.gemini import GeminiProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


def build_provider(settings: Settings, preferences: UserPreferences):
    provider = preferences.provider
    model = preferences.model
    environment_keys = {
        "openai": settings.openai_api_key,
        "claude": settings.anthropic_api_key,
        "gemini": settings.gemini_api_key,
        "grok": settings.xai_api_key,
        "deepseek": settings.deepseek_api_key,
    }
    api_key = preferences.api_key_for(provider) or environment_keys.get(provider, "")
    if not api_key:
        raise ProviderError(f"No API key configured for provider: {provider}")
    if provider == "openai":
        return OpenAICompatibleProvider(api_key, model, "https://api.openai.com/v1", "openai", settings.request_timeout_seconds)
    if provider == "grok":
        return OpenAICompatibleProvider(api_key, model, "https://api.x.ai/v1", "grok", settings.request_timeout_seconds)
    if provider == "deepseek":
        return OpenAICompatibleProvider(api_key, model, "https://api.deepseek.com", "deepseek", settings.request_timeout_seconds)
    if provider == "gemini":
        return GeminiProvider(api_key, model, settings.request_timeout_seconds)
    if provider == "claude":
        return ClaudeProvider(api_key, model, settings.request_timeout_seconds)
    raise ProviderError(f"Unsupported provider: {provider}")
