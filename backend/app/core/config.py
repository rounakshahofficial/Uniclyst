"""Application configuration.

Every secret comes from environment variables — never commit real keys.
`.env.example` documents the placeholders.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings:
    # --- Database ---
    # Production: postgresql+psycopg://user:pass@host:5432/uniclyst
    # Local demo:  sqlite:///backend/uniclyst.db (default)
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'uniclyst.db'}"
    )

    # --- Auth ---
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-only-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = int(os.environ.get("JWT_EXPIRES_MINUTES", "1440"))
    ACCESS_TOKEN_COOKIE_NAME: str = "uniclyst_token"

    # --- Application ---
    APP_NAME: str = "Uniclyst"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    AUTO_CREATE_TABLES: bool = os.environ.get("AUTO_CREATE_TABLES", "1") == "1"
    AUTO_SEED: bool = os.environ.get("AUTO_SEED", "1") == "1"
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # --- TinyFish web intelligence (step 4 of the build) ---
    # The browser NEVER calls TinyFish. All calls go through the backend.
    TINYFISH_API_KEY: str = os.environ.get("TINYFISH_API_KEY", "")
    TINYFISH_SEARCH_URL: str = "https://api.search.tinyfish.ai"
    TINYFISH_FETCH_URL: str = "https://api.fetch.tinyfish.ai"
    TINYFISH_AGENT_URL: str = "https://agent.tinyfish.ai/v1/automation/run-sse"
    TINYFISH_TIMEOUT_SECONDS: float = float(os.environ.get("TINYFISH_TIMEOUT_SECONDS", "30"))
    TINYFISH_MAX_RETRIES: int = int(os.environ.get("TINYFISH_MAX_RETRIES", "2"))
    TINYFISH_CACHE_TTL_SECONDS: int = int(os.environ.get("TINYFISH_CACHE_TTL_SECONDS", "3600"))

    # Seed demo password — documented dev-only credential, disabled unless AUTO_SEED.
    DEMO_PASSWORD: str = os.environ.get("DEMO_PASSWORD", "demo123")


settings = Settings()
