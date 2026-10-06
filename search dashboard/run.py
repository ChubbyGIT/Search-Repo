"""Single-command launcher: python run.py"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
MODULES = ["fastapi", "uvicorn", "pandas", "requests", "dotenv", "pyotp"]


def ensure_deps():
    if any(importlib.util.find_spec(m) is None for m in MODULES):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])


if __name__ == "__main__":
    ensure_deps()
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, app_dir=str(ROOT))
