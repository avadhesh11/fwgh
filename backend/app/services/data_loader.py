"""
Data Loading Layer.
Loads previously fetched and validated Elexon BMRS datasets from local cached files.
Ensures no live external API calls are made during normal request handling.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings

# In-memory cached datasets
_FUELHH_CACHE: Optional[List[Dict[str, Any]]] = None
_WINDFOR_CACHE: Optional[List[Dict[str, Any]]] = None


def find_data_file(filename: str, custom_dir: Optional[Path] = None) -> Path:
    """Locate a data file in the configured data directory or search fallbacks."""
    data_dir = custom_dir or settings.get_data_dir()
    filepath = data_dir / filename
    if filepath.exists():
        return filepath

    # Secondary check in scripts folder
    fallback_scripts = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / filename
    if fallback_scripts.exists():
        return fallback_scripts

    raise FileNotFoundError(
        f"Data file '{filename}' could not be located in '{data_dir}' or '{fallback_scripts.parent}'"
    )


def load_fuelhh_data(force_reload: bool = False, custom_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load FUELHH actuals data from local JSON file."""
    global _FUELHH_CACHE
    if _FUELHH_CACHE is not None and not force_reload:
        return _FUELHH_CACHE

    filepath = find_data_file("raw_fuelhh_cached.json", custom_dir)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _FUELHH_CACHE = data
    return _FUELHH_CACHE


def load_windfor_data(force_reload: bool = False, custom_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load WINDFOR forecast data from local JSON file."""
    global _WINDFOR_CACHE
    if _WINDFOR_CACHE is not None and not force_reload:
        return _WINDFOR_CACHE

    filepath = find_data_file("raw_windfor_cached.json", custom_dir)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _WINDFOR_CACHE = data
    return _WINDFOR_CACHE


def set_cached_data(fuelhh: Optional[List[Dict[str, Any]]] = None, windfor: Optional[List[Dict[str, Any]]] = None) -> None:
    """Inject cached datasets directly (used in automated unit and integration tests)."""
    global _FUELHH_CACHE, _WINDFOR_CACHE
    if fuelhh is not None:
        _FUELHH_CACHE = fuelhh
    if windfor is not None:
        _WINDFOR_CACHE = windfor


def clear_cache() -> None:
    """Clear in-memory dataset cache."""
    global _FUELHH_CACHE, _WINDFOR_CACHE
    _FUELHH_CACHE = None
    _WINDFOR_CACHE = None
