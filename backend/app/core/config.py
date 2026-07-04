import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    BaseSettings = object


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_BUCKET: str = "exports"
    NVIDIA_KEY: str = ""
    LLM_MODEL: str = "google/gemma-4-31b-it"
    LLM_EMBEDDING_MODEL: str = "baai/bge-m3"
    VECTOR_MATCH_THRESHOLD: float = 0.35
    VECTOR_MATCH_COUNT: int = 20
    LLM_EXPLANATIONS_ENABLED: bool = True
    AFP_USE_MOCK_DB: bool = True

    if BaseSettings is not object:
        model_config = SettingsConfigDict(
            env_file=Path(__file__).resolve().parents[2] / ".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )
    else:
        def __init__(self):
            self.SUPABASE_URL = os.getenv("SUPABASE_URL", self.SUPABASE_URL)
            self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", self.SUPABASE_SERVICE_ROLE_KEY)
            self.SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", self.SUPABASE_BUCKET)
            use_mock = os.getenv("AFP_USE_MOCK_DB")
            if use_mock is not None:
                self.AFP_USE_MOCK_DB = use_mock.lower() in {"1", "true", "yes", "on"}


settings = Settings()
