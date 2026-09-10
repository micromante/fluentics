from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.history import HistoryStore
from app.preferences import PreferencesStore, UserPreferences
from app.routes import router
from app.services.translator import TranslationService


def create_app(settings: Settings | None = None, translation_service: TranslationService | None = None) -> FastAPI:
    app = FastAPI(title="FluenTics", docs_url=None, redoc_url=None)
    app.state.settings = settings or Settings()
    defaults = UserPreferences(
        provider=app.state.settings.llm_provider,
        model=app.state.settings.llm_model,
        fallback_model=app.state.settings.llm_fallback_model,
    )
    app.state.preferences_store = PreferencesStore()
    app.state.history_store = HistoryStore()
    app.state.user_preferences = app.state.preferences_store.load(defaults)
    app.state.translation_service = translation_service or TranslationService(app.state.settings)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(router)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/history")
    async def history() -> FileResponse:
        return FileResponse(static_dir / "history.html")

    return app


app = create_app()
