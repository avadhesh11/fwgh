"""
Backend Configuration Settings.
Provides environment-aware and relative path discovery for cached data.
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    PROJECT_NAME: str = "Wind Forecast Decision Portal API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    PORT: int = int(os.environ.get("PORT", "8000"))
    
    # Scope defaults
    DEFAULT_SCOPE: str = "B"
    DEFAULT_CUTOFF_TIME: str = "09:00"  # 09:00 UK local time
    
    # Scope definitions
    SCOPE_A_START: str = "2026-01-01"
    SCOPE_A_END: str = "2026-01-31"
    
    SCOPE_B_START: str = "2026-01-02"
    SCOPE_B_END: str = "2026-02-01"

    # Supported cached dataset delivery boundaries
    SUPPORTED_DELIVERY_START: str = "2026-01-01"
    SUPPORTED_DELIVERY_END: str = "2026-02-01"

    # Keep-alive loop configuration (default: 720s / 12 mins, within 10-14 min window)
    @property
    def KEEP_ALIVE_INTERVAL_SECONDS(self) -> int:
        try:
            return int(os.environ.get("KEEP_ALIVE_INTERVAL_SECONDS", "720"))
        except (ValueError, TypeError):
            return 720

    @property
    def KEEP_ALIVE_ENABLED(self) -> bool:
        """
        Determine if the background keep-alive ping loop should run.
        Explicitly controlled via KEEP_ALIVE_ENABLED ("true" / "false").
        Defaults to True on Render environments or when KEEP_ALIVE_URL is provided,
        and False during local development / testing to avoid unintended pings.
        """
        env_val = os.environ.get("KEEP_ALIVE_ENABLED")
        if env_val is not None:
            return env_val.strip().lower() in ("true", "1", "yes")
        return bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KEEP_ALIVE_URL"))

    @property
    def KEEP_ALIVE_URL(self) -> str:
        """
        Resolve the target health-check URL for keep-alive pings.
        Priority:
        1. Explicit KEEP_ALIVE_URL environment variable
        2. RENDER_EXTERNAL_URL provided by Render platform (e.g. https://<app>.onrender.com)
        3. Default Render production domain fallback
        4. Localhost fallback
        """
        explicit = os.environ.get("KEEP_ALIVE_URL")
        if explicit and explicit.strip():
            return explicit.strip()
        render_ext = os.environ.get("RENDER_EXTERNAL_URL")
        if render_ext and render_ext.strip():
            return f"{render_ext.strip().rstrip('/')}{self.API_PREFIX}/health"
        if os.environ.get("RENDER"):
            return f"https://gridbricks-backend.onrender.com{self.API_PREFIX}/health"
        return f"http://127.0.0.1:{self.PORT}{self.API_PREFIX}/health"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """
        Parse allowed CORS origins from CORS_ORIGINS environment variable (comma-separated).
        Defaults to standard development and production frontend origins.
        """
        origins_env = os.environ.get("CORS_ORIGINS")
        if origins_env:
            return [o.strip() for o in origins_env.split(",") if o.strip()]
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:80",
            "http://127.0.0.1:80",
            "http://localhost",
            "http://127.0.0.1",
            "https://gridbricks-frontend.onrender.com",
        ]

    @classmethod
    def get_data_dir(cls) -> Path:
        """
        Locate data directory using relative candidate search:
        1. DATA_DIR environment variable
        2. fwgh/backend/data
        3. scripts/ directory in workspace root
        """
        env_dir = os.environ.get("DATA_DIR")
        if env_dir:
            p = Path(env_dir)
            if p.exists():
                return p

        # Backend data dir
        backend_data = Path(__file__).resolve().parent.parent / "data"
        if backend_data.exists():
            return backend_data

        # Workspace scripts dir fallback
        scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
        if scripts_dir.exists():
            return scripts_dir

        return Path("data")


settings = Settings()
