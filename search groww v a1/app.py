"""Backend + dashboard server.

- Serves the dashboard (web/) at http://127.0.0.1:8000
- Angel One: angelone.in's own website search backend, authenticated per-request with the NTT
  token pasted into the page (DevTools -> a logged-in angelone.in session). The token is never
  stored — it's sent with each /api/search call and held only in memory for the request.
- Groww: groww.in's public JSON search endpoint; last result is saved as a fallback snapshot.
- Groww Individual: the same Groww search endpoint, but called with the user's own logged-in
  session credential (pasted per run, never stored). No snapshot fallback.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from services import angelone, groww, groww_individual, snapshots
from services.common import strip_internal_fields

app = FastAPI(title="Search Compare")
BROKERS = ("angelone", "groww", "groww_ind")


@app.get("/")
def home():
    return RedirectResponse("/ui/runner.html")


@app.get("/api/health")
def status():
    return {"ok": True}


def _lookup(name, keyword, ntt_token="", groww_token=""):
    try:
        if name == "angelone":
            if not ntt_token.strip():
                return {"source": "error", "error": "Paste an Angel One NTT token"}
            rows, src = angelone.search(keyword, ntt_token)
            return {"source": src, "rows": [strip_internal_fields(r) for r in rows]}
        if name == "groww_ind":
            if not groww_token.strip():
                return {"source": "error", "error": "Paste a Groww session token"}
            rows, src = groww_individual.search(keyword, groww_token)
            return {"source": src, "rows": rows}
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
        return {"source": "error", "error": "Groww search unreachable and no captured snapshot"}
    except Exception as e:
        return {"source": "error", "error": str(e), "rows": []}


@app.get("/api/search")
def search(keyword: str, ntt_token: str = "", groww_token: str = "", brokers: str = ""):
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(400, "keyword required")
    wanted = [b for b in brokers.split(",") if b in BROKERS] or ["angelone", "groww"]
    return {"keyword": keyword, **{b: _lookup(b, keyword, ntt_token, groww_token) for b in wanted}}


app.mount("/ui", StaticFiles(directory=str(Path(__file__).parent / "web")), name="ui")
