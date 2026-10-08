"""Backend + dashboard server.

- Serves the dashboard (web/) at http://127.0.0.1:8000
- Angel One: official SmartAPI search (credentials in .env)
- Groww: groww.in's public JSON search endpoint; last result is saved as a fallback
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from services import angelone, groww, snapshots
from services.common import strip_internal_fields

app = FastAPI(title="Search Compare")
BROKERS = ("angelone", "groww")


@app.get("/")
def home():
    return RedirectResponse("/ui/runner.html")


@app.get("/api/health")
def status():
    return {"ok": True}


def _lookup(name, keyword):
    try:
        if name == "angelone":
            rows, src = angelone.search(keyword)
            return {"source": src, "rows": [strip_internal_fields(r) for r in rows]}
        try:
            live = groww.search(keyword)
            if live:
                snapshots.save_snapshot("groww", keyword, live)
                return {"source": "live", "rows": live}
        except Exception:
            pass
        snap = snapshots.get_latest_snapshot("groww", keyword)
        if snap:
            return {"source": "captured", "captured_at": snap["captured_at"], "rows": snap["rows"]}
        return {"source": "error", "error": "Groww search unreachable and no saved result", "rows": []}
    except Exception as e:
        return {"source": "error", "error": str(e), "rows": []}


@app.get("/api/search")
def search(keyword: str):
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(400, "keyword required")
    return {"keyword": keyword, **{b: _lookup(b, keyword) for b in BROKERS}}


app.mount("/ui", StaticFiles(directory=str(Path(__file__).parent / "web")), name="ui")
