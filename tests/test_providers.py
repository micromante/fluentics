import pytest

from app.config import Settings
from app.preferences import UserPreferences
from app.providers import ProviderError, build_provider
from app.providers.base import parse_result


@pytest.mark.parametrize("provider", ["openai", "claude", "gemini", "grok", "deepseek"])
def test_factory_supports_all_configured_providers(provider):
    settings = Settings(_env_file=None)
    preferences = UserPreferences(provider=provider, model="test-model", api_keys={provider: "test-key"})
    result = build_provider(settings, preferences)
    assert result.model == "test-model"


def test_preferences_key_overrides_environment_key():
    settings = Settings(_env_file=None, openai_api_key="environment-key")
    preferences = UserPreferences(api_keys={"openai": "interface-key"})
    result = build_provider(settings, preferences)
    assert result.client.api_key == "interface-key"


def test_parse_result_validates_structured_response():
    result = parse_result('{"corrected_text":"Hola","translation":"Hello","alternatives":["Hi","Greetings"],"detected_language":"en","corrections":[]}')
    assert result["translation"] == "Hello"


def test_parse_result_rejects_invalid_response():
    with pytest.raises(ProviderError):
        parse_result("not json")
