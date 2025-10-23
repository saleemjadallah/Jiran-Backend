from functools import lru_cache

from pydantic import AnyUrl, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Souk Loop"
    ENVIRONMENT: str = Field("local", description="Environment name e.g. local, staging, production")
    DEBUG: bool = False

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "soukloop"
    DATABASE_PASSWORD: str = "soukloop"
    DATABASE_NAME: str = "soukloop"
    DATABASE_SCHEMA: str = "public"

    DATABASE_URL: PostgresDsn | None = None
    ASYNC_DATABASE_URL: AnyUrl | None = None

    REDIS_URL: AnyUrl = Field(default="redis://localhost:6379/0")
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    SECRET_KEY: str = Field(min_length=32, description="Secret key for JWT tokens - MUST be set in environment")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours for better UX during video uploads
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"

    # CORS origins for development only (mobile apps bypass CORS)
    # iOS/Android native apps don't need CORS - this is only for local Flutter web development
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]
    )

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "eu-central-1"
    B2_BUCKET_NAME: str | None = None
    B2_ENDPOINT_URL: AnyUrl | None = None

    SOCKET_IO_MESSAGE_QUEUE: AnyUrl | None = None

    # ZeptoMail API Configuration
    ZEPTO_API_URL: str = "https://api.zeptomail.com/v1.1/email"
    ZEPTO_SEND_TOKEN: str | None = None
    ZEPTO_FROM_EMAIL: str = "support@jiran.app"
    ZEPTO_FROM_NAME: str = "Jiran"

    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return str(self.DATABASE_URL)
        return (
            f"postgresql+psycopg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def async_database_url(self) -> str:
        if self.ASYNC_DATABASE_URL:
            return str(self.ASYNC_DATABASE_URL)
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

