from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    upload_dir: str = "uploads"
    max_upload_size_bytes: int = 2 * 1024 * 1024

    frankfurter_base_url: str = "https://api.frankfurter.dev/v1"
    exchange_rate_base_currency: str = "USD"
    rate_staleness_hours: int = 36
    exchange_rate_refresh_hour_utc: int = 2

    cors_allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:8080,http://127.0.0.1:8080"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
