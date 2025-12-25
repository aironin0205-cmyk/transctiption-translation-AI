from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    assemblyai_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    picovoice_access_key: str = Field(default="")

    app_env: str = "local"
    data_dir: str = "/data"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "subtitle_ai"
    postgres_user: str = "subtitle_ai"
    postgres_password: str = "subtitle_ai_password"

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "openai/text-embedding-3-large"

    tm_auto_reuse_threshold: float = 0.88
    tm_judge_threshold: float = 0.82

    max_lines: int = 2
    max_chars_per_line: int = 42
    target_cps: float = 15.0
    min_cue_ms: int = 900
    max_cue_ms: int = 6500
    translation_batch_size: int = 20

    model_strategist_low: str = "google/gemini-3-flash"
    model_strategist_high: str = "deepseek/deepseek-r1-0528"
    fallback_strategist_high: str = "google/gemini-3-pro,openai/gpt-5.2"

    model_terminologist_mid: str = "deepseek/deepseek-v3.2"
    model_terminologist_hard: str = "deepseek/deepseek-r1-0528"
    fallback_terminologist: str = "google/gemini-3-pro,openai/gpt-5.2"

    model_translator_easy: str = "anthropic/claude-haiku-4.5"
    model_translator_mid: str = "google/gemini-3-pro"
    model_translator_hard: str = "openai/gpt-5.2"
    fallback_translator_mid: str = "anthropic/claude-sonnet-4.5,openai/gpt-5.2"
    fallback_translator_hard: str = "anthropic/claude-sonnet-4.5,deepseek/deepseek-r1-0528"

    model_qa_easy: str = "google/gemini-3-flash"
    model_qa_hard: str = "google/gemini-3-pro"
    fallback_qa_hard: str = "anthropic/claude-sonnet-4.5,openai/gpt-5.2"

    model_tm_judge: str = "google/gemini-3-flash"

    model_librarian: str = "deepseek/deepseek-v3.2"
    fallback_librarian: str = "deepseek/deepseek-r1-0528,google/gemini-3-pro"

settings = Settings()
