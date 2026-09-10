import pytest

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.translator import TranslationServiceError


class FakeTranslationService:
    def __init__(self, result=None, error=False):
        self.result = result or {
            "corrected_text": "Hola.",
            "translation": "Hello.",
            "alternatives": ["Hi.", "Greetings."],
            "detected_language": "es",
            "corrections": [{"original": "Helo", "corrected": "Hello"}],
        }
        self.error = error
        self.received_text = None

    async def translate(self, text, preferences=None):
        self.received_text = text
        if self.error:
            raise TranslationServiceError
        return self.result


def make_client(service=None, **settings_overrides):
    settings = Settings(openai_api_key="test-key", **settings_overrides)
    return TestClient(create_app(settings=settings, translation_service=service or FakeTranslationService()))


def test_health_and_config():
    client = make_client()
    assert client.get("/health").json() == {"status": "ok"}
    config = client.get("/api/config").json()
    assert config["model"] == "gpt-5.4-nano"
    assert config["fallback_model"] == "gpt-5-nano"
    assert config["provider"] == "openai"
    assert config["direction"] == "auto"
    assert config["prompt"]


def test_updates_config_without_calling_openai(tmp_path):
    service = FakeTranslationService()
    settings = Settings(openai_api_key="test-key")
    app = create_app(settings=settings, translation_service=service)
    app.state.preferences_store.path = tmp_path / "settings.json"
    client = TestClient(app)
    response = client.put(
        "/api/config",
        json={"provider": "gemini", "model": "gemini-test", "fallback_model": "gemini-fallback", "direction": "es-en", "prompt": "Test prompt", "api_keys": {"gemini": "gemini-secret"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "gemini"
    assert body["model"] == "gemini-test"
    assert body["fallback_model"] == "gemini-fallback"
    assert body["api_keys"]["gemini"] == "gemini-secret"
    assert (tmp_path / "settings.json").exists()


def test_rejects_invalid_config():
    response = make_client().put(
        "/api/config",
        json={"model": "", "direction": "invalid", "prompt": "x"},
    )
    assert response.status_code == 400


def test_translate_returns_clean_result_and_corrections():
    service = FakeTranslationService()
    response = make_client(service).post("/api/translate", json={"text": "  Ola  "})
    body = response.json()
    assert response.status_code == 200
    assert service.received_text == "Ola"
    assert body["translation"] == "Hello."
    assert body["corrected_text"] == "Hola."
    assert body["alternatives"] == ["Hi.", "Greetings."]
    assert body["corrections"] == [{"original": "Helo", "corrected": "Hello"}]
    assert isinstance(body["latency_ms"], int)


def test_rejects_empty_text():
    response = make_client().post("/api/translate", json={"text": "   "})
    assert response.status_code == 400


def test_rejects_text_over_limit():
    response = make_client(max_text_length=4).post("/api/translate", json={"text": "12345"})
    assert response.status_code == 413


def test_provider_factory_rejects_missing_key():
    from app.providers import ProviderError, build_provider
    from app.preferences import UserPreferences

    with pytest.raises(ProviderError):
        build_provider(Settings(_env_file=None, openai_api_key=""), UserPreferences())


def test_returns_bad_gateway_when_service_fails():
    response = make_client(FakeTranslationService(error=True)).post("/api/translate", json={"text": "Hello"})
    assert response.status_code == 502
