from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/webhooks.db"
    worker_poll_interval_seconds: int = 10
    max_delivery_attempts: int = 5
    request_timeout_seconds: int = 10
    app_secret_key: str = "change-me"


settings = Settings()
