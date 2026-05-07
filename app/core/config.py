from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "NutriBin Backend"
    APP_ENV: str = "dev"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./nutribin.db"
    DEFAULT_DEVICE_ID: str = "ESP32_BIN_01"
    DEFAULT_DEVICE_NAME: str = "NutriBin Device"
    DEFAULT_DEVICE_API_KEY: str = "nutribin-dev-key"
    ONLINE_WINDOW_SECONDS: int = 120
    INGEST_RATE_LIMIT_SECONDS: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
