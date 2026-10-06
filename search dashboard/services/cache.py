import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path(os.getenv("MASTER_FILE_CACHE_DIR", ".cache"))
TTL_HOURS = float(os.getenv("MASTER_FILE_CACHE_TTL_HOURS", "24"))


def fetch_with_cache(url: str, filename: str, timeout: int = 30) -> bytes:
    """Download url into the cache dir unless a fresh copy exists; return bytes."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / filename
    if path.exists() and (time.time() - path.stat().st_mtime) < TTL_HOURS * 3600:
        return path.read_bytes()
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return resp.content
