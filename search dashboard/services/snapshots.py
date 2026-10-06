import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "snapshots.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker TEXT NOT NULL, keyword TEXT NOT NULL,
        captured_at TEXT NOT NULL, rows_json TEXT NOT NULL)""")
    return c


def _norm(k):
    return (k or "").strip().lower()


def save_snapshot(broker, keyword, rows):
    ts = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute("INSERT INTO snapshots (broker, keyword, captured_at, rows_json) VALUES (?,?,?,?)",
                  (broker, _norm(keyword), ts, json.dumps(rows)))
    return ts


def get_latest_snapshot(broker, keyword):
    with _conn() as c:
        r = c.execute("SELECT captured_at, rows_json FROM snapshots WHERE broker=? AND keyword=? "
                      "ORDER BY id DESC LIMIT 1", (broker, _norm(keyword))).fetchone()
    if not r:
        return None
    return {"captured_at": r[0], "rows": json.loads(r[1])}


def list_captured_keywords(broker=None):
    q = "SELECT DISTINCT broker, keyword FROM snapshots"
    args = ()
    if broker:
        q += " WHERE broker=?"
        args = (broker,)
    with _conn() as c:
        return [{"broker": b, "keyword": k} for b, k in c.execute(q, args).fetchall()]
