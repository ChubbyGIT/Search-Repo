"""Backend for the Broker Capture extension (no UI of its own).

- Angel One: calls Angel One's official SmartAPI search (credentials in .env).
- Groww: stores/serves snapshots the extension captured from groww.in.
"""
from typing import List

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from services import angelone, groww, snapshots
from services.common import strip_internal_fields

app = FastAPI(title="Broker Capture Backend")
BROKERS = ("angelone", "groww")


@app.get("/")
def status():
    return {"ok": True, "message": "Backend running. Use the Broker Capture extension."}


def _lookup(name, keyword):
    try:
        if name == "angelone":
            rows, src = angelone.search(keyword)
            return {"source": src, "rows": [strip_internal_fields(r) for r in rows]}
        snap = snapshots.get_latest_snapshot("groww", keyword)
        if snap:
            return {"source": "captured", "captured_at": snap["captured_at"], "rows": snap["rows"]}
        rows = groww.search(keyword)
        return {"source": "fallback", "rows": [strip_internal_fields(r) for r in rows]}
    except Exception as e:
        return {"source": "error", "error": str(e), "rows": []}


@app.get("/api/search")
def search(keyword: str):
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(400, "keyword required")
    return {"keyword": keyword, **{b: _lookup(b, keyword) for b in BROKERS}}


class SnapshotIn(BaseModel):
    broker: str
    keyword: str
    rows: List[dict]


CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*"}


@app.options("/api/snapshot")
def snapshot_preflight():
    return Response(status_code=204, headers=CORS)


@app.post("/api/snapshot")
def save_snapshot(body: SnapshotIn, response: Response):
    for k, v in CORS.items():  # CORS open on this route only (localhost-bound server)
        response.headers[k] = v
    if body.broker.lower() != "groww":
        raise HTTPException(400, "only groww snapshots are supported")
    ts = snapshots.save_snapshot("groww", body.keyword, body.rows)
    return {"ok": True, "captured_at": ts, "count": len(body.rows)}
