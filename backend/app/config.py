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
    
    # Scope defaults
    DEFAULT_SCOPE: str = "A"
    DEFAULT_CUTOFF_TIME: str = "09:00"  # 09:00 UK local time
    
    # Scope definitions
    SCOPE_A_START: str = "2026-01-01"
    SCOPE_A_END: str = "2026-01-31"
    
    SCOPE_B_START: str = "2026-01-02"
    SCOPE_B_END: str = "2026-02-01"

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
