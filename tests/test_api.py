import pytest

from fastapi.testclient import TestClient

from app.config import Settings
from app.history import HistoryStore
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


def make_client(service=None, history_path=None, **settings_overrides):
    settings = Settings(openai_api_key="test-key", **settings_overrides)
    app = create_app(settings=settings, translation_service=service or FakeTranslationService())
    if history_path:
        app.state.history_store = HistoryStore(history_path)
    return TestClient(app)


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


def test_translate_returns_clean_result_and_corrections(tmp_path):
    service = FakeTranslationService()
    response = make_client(service, history_path=tmp_path / "history.json").post("/api/translate", json={"text": "  Ola  "})
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


def test_translation_is_saved_in_history(tmp_path):
    client = make_client(history_path=tmp_path / "history.json")
    response = client.post("/api/translate", json={"text": "Hello"})
    assert response.status_code == 200
    entries = client.get("/api/history").json()
    assert len(entries) == 1
    assert entries[0]["original_text"] == "Hello"
    assert entries[0]["translation"] == "Hello."


def test_history_can_open_delete_and_clear_entries(tmp_path):
    client = make_client(history_path=tmp_path / "history.json")
    client.post("/api/translate", json={"text": "First"})
    client.post("/api/translate", json={"text": "Second"})
    entries = client.get("/api/history").json()
    assert entries[0]["original_text"] == "Second"
    entry_id = entries[0]["id"]
    assert client.get(f"/api/history/{entry_id}").json()["id"] == entry_id
    assert client.delete(f"/api/history/{entry_id}").status_code == 204
    assert len(client.get("/api/history").json()) == 1
    assert client.delete("/api/history").status_code == 204
    assert client.get("/api/history").json() == []


def test_history_store_survives_reload(tmp_path):
    path = tmp_path / "history.json"
    store = HistoryStore(path)
    entry = {
        "created_at": "2026-01-01T00:00:00+00:00",
        "original_text": "Hello",
        "corrected_text": "Hello",
        "translation": "Hola",
        "alternatives": ["Buenas", "Hola"],
        "detected_language": "en",
        "provider": "openai",
        "model": "test-model",
        "latency_ms": 10,
    }
    from app.history import HistoryEntry
    store.add(HistoryEntry(**entry))
    assert HistoryStore(path).load()[0].translation == "Hola"
