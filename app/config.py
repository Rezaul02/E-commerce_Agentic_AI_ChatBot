"""Central config. Sob env variable ek jaygay."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o-mini"
    TEMPERATURE: float = 0.2

    # Redis / history
    REDIS_URL: str = "redis://localhost:6379/0"
    HISTORY_TTL: int = 86400
    HISTORY_WINDOW: int = 20

    # Dummy API
    DUMMY_API_URL: str = "http://localhost:8001"

    # Agent
    MAX_ITERATIONS: int = 8


settings = Settings()
