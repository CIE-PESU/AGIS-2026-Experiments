"""
core/config.py — Application configuration via Pydantic Settings.

Reads all values from environment variables (or .env file).
Never hardcode secrets. Every field here must come from the environment.
"""
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration class. All fields are read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    APP_NAME: str = "AGIS Entrepreneurship Coach Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # ── MongoDB ────────────────────────────────────────────────────────────────
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "agis"
    MONGODB_MAX_POOL_SIZE: int = 10
    MONGODB_MIN_POOL_SIZE: int = 2

    # ── JWT ────────────────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRY_DAYS: int = 7
    FERNET_KEY: str

    # ── PES Auth ───────────────────────────────────────────────────────────────
    PES_AUTH_URL: str                    # e.g. https://auth.pes.edu/api/v1/validate
    PES_AUTH_TIMEOUT_SECONDS: float = 5.0

    # ── Kafka ──────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str         # e.g. localhost:9092
    KAFKA_SECURITY_PROTOCOL: str = "PLAINTEXT"

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g. "http://localhost:3000,https://app.agis.edu"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Internal Worker ────────────────────────────────────────────────────────
    WORKER_INTERNAL_SECRET: str


    # ── Rate Limiting ──────────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5    # per IP
    RATE_LIMIT_API_PER_MINUTE: int = 60     # per user_id

    # ── Payload ────────────────────────────────────────────────────────────────
    MAX_REQUEST_BODY_BYTES: int = 10_485_760  # 10 MB (C4: returns 413 above this)
    # ── Agent Worker ──────────────────────────────────────────────────────────────
    WORKER_BACKEND_URL: str = "http://127.0.0.1:8000"
    WORKER_ID: str = "combined-agent-worker-1"
    AGENT_TIMEOUT_SECONDS: int = 1800
    AGENT_MAX_RETRIES: int = 3
    TAVILY_API_KEY: str
    # ── LLM / CrewAI ───────────────────────────────────────────────────────────
    OPENAI_MODEL_NAME: str
    OPENAI_API_KEY: str
    LM_STUDIO_URL: str
    LOG_LEVEL: str = "INFO" # or DEBUG

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ALLOWED_ORIGINS into a list."""
        origins = [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]
        if not self.is_production and "*" not in origins:
            origins.append("*")
        return origins

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


# Singleton settings instance used across the entire application.
settings = Settings()
