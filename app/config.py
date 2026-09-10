from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-nano"
    llm_fallback_model: str = "gpt-5-nano"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    xai_api_key: str = ""
    deepseek_api_key: str = ""
    max_text_length: int = 5000
    request_timeout_seconds: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
