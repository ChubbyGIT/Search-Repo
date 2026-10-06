# Recreate: Angel One vs Groww â€” Search Compare

Paste this whole file into a fresh Claude session and say:
**"Build exactly this project. Create every file below with the exact contents. Then walk me through running it."**

Everything below is the complete spec plus the real source code. Secrets are placeholders.

---

## 1. What it is

A local tool that compares search results for a keyword (e.g. `nifty`, `sens`, `gold`) between **Angel One** and **Groww**, shown side by side in a dark, terminal-style page.

- **A Python FastAPI backend** (runs on `127.0.0.1:8000`, no web page of its own).
- **A Chrome extension (Manifest V3)** whose full-tab page (`runner.html`) is the only UI.

## 2. Why the two brokers are handled differently (important)

| Broker | Approach |
|---|---|
| **Angel One** | Has an official, documented search API (`searchScrip`) via SmartAPI. The backend logs in (client ID + PIN + TOTP) and calls it. |
| **Groww** | No public search API. The extension opens Groww's normal search page (`https://groww.in/search?q=<keyword>`) in a background tab in the user's **own browser** (a normal page visit), reads the rendered DOM, and POSTs rows to the backend. **Never call Groww's private/undocumented endpoints** (their robots.txt disallows `/v1/api/*`). |

Angel One `searchScrip` quirks discovered by testing:
1. It only matches the **start** of a trading symbol (so `24` returns nothing) and returns results **alphabetically**.
2. Per exchange, "no match" comes back as `status=False, "Scrip not found in scrip master cache for the given exchange"` â€” treat that as *zero results for that exchange*, **not** a failure (otherwise one empty exchange kills the whole search).
3. Rate limit â‰ˆ 1 request/second (403 "Access denied because of exceeding access rate"). Space calls â‰¥1.1s and retry.
4. Search exchanges: `NSE, BSE, NFO, BFO` (BFO = SENSEX derivatives) and `MCX` (commodities such as gold).
5. So the backend also does a substring match over Angel One's public instrument list (`OpenAPIScripMaster.json`) for partial input, tags those rows `match="text"`, then **ranks everything by relevance** (exact name > prefix > contains; index > equity > futures > options; nearest expiry first). The ranking is this tool's own and the UI says so.
6. In the master file, index rows have `instrumenttype` `AMXIDX`; derivatives are `OPTIDX`/`FUTIDX` etc. (so don't test `"IDX" in type` first â€” check OPT/FUT first).

Other gotchas:
- Pandas `NaN` is not valid JSON â†’ every field goes through `_nan_to_none`.
- `NaN` is truthy â†’ use `pd.notna()` not `if x`.
- Angel One's `strike` field in the master file is Ã—100.
- Chrome rejects tab edits while a tab is dragged ("Tabs cannot be edited right now") â†’ retry.
- Groww's CSS-module class names have hashed suffixes â†’ match by prefix `[class*="SearchPageV2_suggestionItem"]`, and scope to the element right after the "SEARCH RESULTS" heading so the unrelated "trending" widget isn't picked up. Always test with â‰¥2 keywords; identical rows across keywords = selector too broad.

## 3. Design / fonts

- Theme: **dark, terminal-like**. Inspired by Angel One's web app layout (small text, pill buttons, thin-bordered panels, small tag badges, right-aligned numbers).
- Fonts (Google Fonts): **Inter** (400/500/600/700) for UI text, **JetBrains Mono** (400/500/600) for symbols, numbers, search box and console. Fallbacks: Segoe UI / Consolas.
- Colors: bg `#07090c`, panel `#0f1318`, lines `#1c222b`, text `#d7dce4`, blue `#5b8cff` (accent + table headers), green `#1fc77e`, red `#f2545b`, amber `#e9a23b`, violet `#a07cff`.
- Top bar: logo `â–²`, search box with green `>` prompt (comma-separated keywords, Enter to run, Ctrl+K focus), backend status dot. Below: chip toggle **Both / Angel One / Groww**, **Run search**, **Clear**. Then two info cards (the Groww URL is shown as fixed, non-editable text), a console panel (timestamps, colored lines, blinking cursor), then result blocks: one per keyword, two cards side by side (stack under 1100px) with source tags (LIVE API / + TEXT MATCH / TEXT MATCH / CAPTURED / ERROR), table columns `# Â· Instrument Â· Underlying Â· Strike Â· LTP Â· Change`, tags for type (CE green, PE red, FUT violet, EQ blue), exchange (grey) and `TXT` (amber), â–²/â–¼ with green/red.

## 4. Folder structure

```
search dashboard/
â”œâ”€â”€ .env                    (placeholders - user fills in)
â”œâ”€â”€ .gitignore
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ run.py
â”œâ”€â”€ app.py
â”œâ”€â”€ README.md               (beginner setup guide, write one)
â”œâ”€â”€ services/
â”‚   â”œâ”€â”€ cache.py
â”‚   â”œâ”€â”€ common.py
â”‚   â”œâ”€â”€ snapshots.py
â”‚   â”œâ”€â”€ angelone_auth.py
â”‚   â”œâ”€â”€ angelone.py
â”‚   â”œâ”€â”€ groww_auth.py
â”‚   â””â”€â”€ groww.py
â””â”€â”€ extension/
    â”œâ”€â”€ manifest.json
    â”œâ”€â”€ popup.html
    â”œâ”€â”€ popup.js
    â”œâ”€â”€ runner.html
    â”œâ”€â”€ runner.css
    â”œâ”€â”€ runner.js
    â””â”€â”€ README.md
```

Note `services/` needs to be a package: Python 3 namespace packages work without `__init__.py`, which is how this was run.

## 5. How to run

1. `python run.py` (installs requirements if missing, starts uvicorn on 127.0.0.1:8000).
2. Chrome â†’ `chrome://extensions` â†’ Developer mode â†’ Load unpacked â†’ pick `extension/`.
3. Click extension icon â†’ open page â†’ type keywords â†’ Enter.

## 6. Angel One SmartAPI app setup (for `.env`)

- Create app at smartapi.angelone.in â†’ *Add App*. Redirect URL can't be localhost â†’ use any public URL such as `https://www.google.com` (never used). Primary static IP: user's public IP.
- Copy API key. Enable TOTP and copy the **text secret** shown under the QR code.
- `.env`: `ANGEL_ONE_API_KEY`, `ANGEL_ONE_CLIENT_ID`, `ANGEL_ONE_PASSWORD` (the 4-digit login **PIN**), `ANGEL_ONE_TOTP_SECRET`.

## 7. Known limits

- Angel One's real app search is internal and unavailable; this approximates it.
- Groww rows have only name + underlying (no strike/expiry/type) unless the extension is extended.
- New Angel One keyword takes ~5â€“7 s (rate limit); repeats within 5 min are cached.
- The Chrome extension was not testable on machines where policy blocks "Load unpacked".
- Never commit a real `.env`.

---

## 8. Source code (create each file exactly)

### `requirements.txt`

~~~text
fastapi
uvicorn
pandas
requests
python-dotenv
pyotp
~~~

### `.env`

~~~ini
# Angel One (SmartAPI) - https://smartapi.angelone.in/
ANGEL_ONE_API_KEY=YOUR_API_KEY
ANGEL_ONE_CLIENT_ID=YOUR_CLIENT_ID
ANGEL_ONE_PASSWORD=YOUR_PASSWORD
ANGEL_ONE_TOTP_SECRET=YOUR_TOTP_SECRET

# Groww Trade API (optional - only used for price fallback, not needed for the extension)
GROWW_API_KEY=YOUR_API_KEY
GROWW_API_SECRET=YOUR_API_SECRET
GROWW_ACCESS_TOKEN=YOUR_ACCESS_TOKEN

# Cache settings
MASTER_FILE_CACHE_DIR=.cache
MASTER_FILE_CACHE_TTL_HOURS=24
~~~

### `.gitignore`

~~~text
.env
.cache/
snapshots.db
__pycache__/
~~~

### `run.py`

~~~python
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
~~~

### `app.py`

~~~python
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
~~~

### `services/cache.py`

~~~python
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
~~~

### `services/common.py`

~~~python
import math


def _nan_to_none(value):
    """Pandas yields NaN for missing values; NaN is not valid JSON."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        import pandas as pd
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):  # numpy scalar -> python
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def build_row(symbol=None, full_name=None, underlying=None, exchange=None, segment=None,
              expiry=None, strike=None, option_type=None, token=None):
    return {
        "symbol": _nan_to_none(symbol),
        "full_name": _nan_to_none(full_name),
        "underlying": _nan_to_none(underlying),
        "exchange": _nan_to_none(exchange),
        "segment": _nan_to_none(segment),
        "expiry": _nan_to_none(expiry),
        "strike": _nan_to_none(strike),
        "option_type": _nan_to_none(option_type),
        "price": None,
        "change_pct": None,
        "_token": _nan_to_none(token),
        "_volume": None,
    }


def option_type_from_symbol(symbol):
    s = (_nan_to_none(symbol) or "").upper()
    if s.endswith("CE"):
        return "CE"
    if s.endswith("PE"):
        return "PE"
    if s.endswith("FUT"):
        return "FUT"
    return None


def sort_by_liquidity(rows):
    """Sort by _volume desc, only if any row has volume data."""
    if not any(r.get("_volume") for r in rows):
        return rows
    return sorted(rows, key=lambda r: r.get("_volume") or 0, reverse=True)


def compute_change_pct(last, prev_close):
    try:
        if last is None or not prev_close:
            return None
        return round((float(last) - float(prev_close)) / float(prev_close) * 100, 2)
    except (TypeError, ValueError):
        return None


def strip_internal_fields(row):
    return {k: v for k, v in row.items() if not k.startswith("_")}
~~~

### `services/snapshots.py`

~~~python
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
~~~

### `services/angelone_auth.py`

~~~python
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
SESSION_TTL = 6 * 3600
_session = {"jwt": None, "at": 0}


def _is_placeholder(v):
    return not v or v.startswith("YOUR_")


def credentials():
    return {k: os.getenv(f"ANGEL_ONE_{k}", "") for k in ("API_KEY", "CLIENT_ID", "PASSWORD", "TOTP_SECRET")}


def has_credentials():
    return not any(_is_placeholder(v) for v in credentials().values())


def api_key():
    return credentials()["API_KEY"]


def get_jwt():
    """Return a cached JWT, logging in with TOTP when needed. None if unavailable."""
    if _session["jwt"] and time.time() - _session["at"] < SESSION_TTL:
        return _session["jwt"]
    if not has_credentials():
        return None
    import pyotp
    c = credentials()
    headers = {
        "Content-Type": "application/json", "Accept": "application/json",
        "X-UserType": "USER", "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00", "X-PrivateKey": c["API_KEY"],
    }
    body = {"clientcode": c["CLIENT_ID"], "password": c["PASSWORD"],
            "totp": pyotp.TOTP(c["TOTP_SECRET"]).now()}
    r = requests.post(LOGIN_URL, json=body, headers=headers, timeout=15)
    data = r.json()
    if not data.get("status"):
        return None
    _session.update(jwt=data["data"]["jwtToken"], at=time.time())
    return _session["jwt"]


def auth_headers():
    jwt = get_jwt()
    if not jwt:
        return None
    return {
        "Authorization": f"Bearer {jwt}", "Content-Type": "application/json",
        "Accept": "application/json", "X-UserType": "USER", "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1", "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00", "X-PrivateKey": api_key(),
    }
~~~

### `services/angelone.py`

~~~python
import json
import time
from datetime import datetime

import requests

from . import angelone_auth
from .cache import fetch_with_cache
from .common import build_row, compute_change_pct, option_type_from_symbol

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
BASE = "https://apiconnect.angelone.in/rest/secure/angelbroking"
# Cash first, then F&O. BFO = SENSEX/BANKEX derivatives, MCX = commodities (gold etc.)
SEARCH_EXCHANGES = ["NSE", "BSE", "NFO", "BFO", "MCX"]
SEARCH_INTERVAL = 1.1      # searchScrip is rate limited to ~1 request/second
RESULT_CACHE_TTL = 300     # seconds; avoids re-hitting the rate limit for repeat searches

_master = None   # list of dicts
_by_key = None   # (exch, token) -> dict
_last_call = 0.0
_result_cache = {}  # keyword -> (time, rows)


def _load_master():
    global _master, _by_key
    if _master is None:
        _master = json.loads(fetch_with_cache(MASTER_URL, "angelone_master.json", timeout=60))
        _by_key = {(m.get("exch_seg"), m.get("token")): m for m in _master}
    return _master


def _row_from_master(m):
    sym = m.get("symbol")
    itype = m.get("instrumenttype") or ""
    strike = None
    try:
        s = float(m.get("strike") or -1)
        strike = s / 100 if s > 0 else None
    except ValueError:
        pass
    if itype.startswith("OPT"):
        otype = option_type_from_symbol(sym)
    elif itype.startswith("FUT"):
        otype = "FUT"
    else:
        otype = "EQ" if (m.get("exch_seg") in ("NSE", "BSE") and not itype) else (itype or None)
    return build_row(sym, m.get("name"), m.get("name"), m.get("exch_seg"), itype or None,
                     m.get("expiry") or None, strike, otype, m.get("token"))


def _expiry_key(m):
    try:
        return datetime.strptime(m.get("expiry") or "", "%d%b%Y")
    except ValueError:
        return datetime.max


def _search_text(keyword, limit, exclude=()):
    """Substring match anywhere in symbol or name over Angel One's instrument list.
    Cash/index instruments first, then derivatives by nearest expiry."""
    kw = keyword.lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hits = []
    for m in _load_master():
        if (m.get("exch_seg"), m.get("token")) in exclude:
            continue
        if kw in (m.get("symbol") or "").lower() or kw in (m.get("name") or "").lower():
            exp = _expiry_key(m)
            if exp != datetime.max and exp < today:
                continue  # skip expired contracts
            hits.append(m)
    hits.sort(key=lambda m: (0 if m.get("exch_seg") in ("NSE", "BSE") else 1, _expiry_key(m), m.get("symbol") or ""))
    return [_row_from_master(m) for m in hits[:limit]]


def _search_scrip(exchange, keyword, headers):
    """One searchScrip call, respecting the rate limit. Returns list (possibly empty)."""
    global _last_call
    for attempt in range(3):
        wait = SEARCH_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        r = requests.post(f"{BASE}/order/v1/searchScrip",
                          json={"exchange": exchange, "searchscrip": keyword}, headers=headers, timeout=15)
        if r.status_code == 403 and "rate" in r.text.lower():
            time.sleep(1.5)
            continue
        try:
            data = r.json()
        except ValueError:
            return []
        # "Scrip not found ..." comes back as status=False - that just means no matches here.
        return (data.get("data") or []) if data.get("status") else []
    return []


def _search_live(keyword, limit):
    headers = angelone_auth.auth_headers()
    if not headers:
        raise RuntimeError("no Angel One session")
    _load_master()
    seen, rows = set(), []
    for exch in SEARCH_EXCHANGES:
        for item in _search_scrip(exch, keyword, headers):
            key = (item.get("exchange"), item.get("symboltoken"))
            if key in seen:
                continue
            seen.add(key)
            m = _by_key.get(key)
            row = _row_from_master(m) if m else build_row(
                item.get("tradingsymbol"), None, None, item.get("exchange"), None, None, None,
                option_type_from_symbol(item.get("tradingsymbol")), item.get("symboltoken"))
            row["match"] = "api"
            rows.append(row)
    return rows, seen


def _attach_quotes(rows):
    try:
        headers = angelone_auth.auth_headers()
        if not headers or not rows:
            return
        grouped = {}
        for r in rows:
            if r["_token"] and r["exchange"]:
                grouped.setdefault(r["exchange"], []).append(r["_token"])
        resp = requests.post(f"{BASE}/market/v1/quote",
                             json={"mode": "FULL", "exchangeTokens": grouped}, headers=headers, timeout=15)
        fetched = (resp.json().get("data") or {}).get("fetched") or []
        q = {(f.get("exchange"), f.get("symbolToken")): f for f in fetched}
        for r in rows:
            f = q.get((r["exchange"], r["_token"]))
            if f:
                r["price"] = f.get("ltp")
                r["_volume"] = f.get("tradeVolume")
                r["change_pct"] = compute_change_pct(f.get("ltp"), f.get("close"))
    except Exception:
        pass  # quotes are optional


def _kind_rank(r):
    """Lower = more prominent. Index < equity < futures < options < other NSE series (-AF/-BL/-RL...)."""
    seg = (r.get("segment") or "").upper()
    sym = (r.get("symbol") or "").upper()
    ot = r.get("option_type")
    if ot == "FUT" or seg.startswith("FUT"):
        return 2
    if ot in ("CE", "PE") or seg.startswith("OPT"):
        return 3
    if seg == "AMXIDX" or seg.endswith("IDX"):
        return 0
    if r.get("exchange") in ("NSE", "BSE"):
        if "-" not in sym or sym.endswith("-EQ"):
            return 1
        return 4
    return 3


def _rank(rows, keyword):
    kw = keyword.strip().lower()

    def key(r):
        sym = (r.get("symbol") or "").lower()
        base = sym.split("-")[0]
        name = (r.get("underlying") or "").lower()
        if kw in (base, name):
            closeness = 0
        elif base.startswith(kw) or name.startswith(kw):
            closeness = 1
        else:
            closeness = 2
        try:
            exp = datetime.strptime(r.get("expiry") or "", "%d%b%Y")
        except ValueError:
            exp = datetime.max
        return (closeness, _kind_rank(r), exp, 0 if r.get("match") == "api" else 1, sym)

    return sorted(rows, key=key)


def search(keyword, limit=25):
    """Returns (rows, source).
    Angel One's searchScrip API only matches the start of a trading symbol and returns results
    alphabetically, so we gather all API matches, add substring matches from Angel One's
    instrument list, then rank by relevance (exact name > prefix > contains; index > equity >
    futures > options; nearest expiry first) before taking the top `limit`.
    source: 'live' (all shown rows from the API), 'mixed' (some text matches), 'local' (API unavailable).
    Each row has match='api' or match='text'."""
    key = keyword.strip().lower()
    hit = _result_cache.get(key)
    if hit and time.time() - hit[0] < RESULT_CACHE_TTL:
        return [dict(r) for r in hit[1]], hit[2]

    api_ok = True
    try:
        api_rows, seen = _search_live(keyword, limit)
    except Exception:
        api_ok, api_rows, seen = False, [], set()
    extra = _search_text(keyword, 400, exclude=seen)
    for r in extra:
        r["match"] = "text"
    rows = _rank(api_rows + extra, keyword)[:limit]

    if not api_ok or not api_rows:
        source = "local"
    elif all(r["match"] == "api" for r in rows):
        source = "live"
    else:
        source = "mixed"

    _attach_quotes(rows)
    _result_cache[key] = (time.time(), [dict(r) for r in rows], source)
    return rows, source
~~~

### `services/groww_auth.py`

~~~python
import os

from dotenv import load_dotenv

load_dotenv()


def has_credentials():
    t = os.getenv("GROWW_ACCESS_TOKEN")
    return bool(t) and not t.startswith("YOUR_")


def auth_headers():
    """Daily access token from the Groww profile (Trading APIs section)."""
    if not has_credentials():
        return None
    return {"Authorization": f"Bearer {os.getenv('GROWW_ACCESS_TOKEN')}",
            "Accept": "application/json", "X-API-VERSION": "1.0"}
~~~

### `services/groww.py`

~~~python
import io

import pandas as pd
import requests

from . import groww_auth
from .cache import fetch_with_cache
from .common import build_row, compute_change_pct, option_type_from_symbol, sort_by_liquidity

# Verify against https://groww.in/trade-api/docs if this breaks.
MASTER_URL = "https://growwapi-assets.groww.in/instruments/instrument.csv"
QUOTE_URL = "https://api.groww.in/v1/live-data/quote"
_df = None


def _load():
    global _df
    if _df is None:
        _df = pd.read_csv(io.BytesIO(fetch_with_cache(MASTER_URL, "groww_instruments.csv", timeout=60)),
                          low_memory=False)
    return _df


def _col(df, *names):
    for n in names:
        if n in df.columns:
            return n
    return None


def _attach_quotes(rows):
    headers = groww_auth.auth_headers()
    if not headers:
        return
    for r in rows:  # one call per symbol - Groww has no batch endpoint
        try:
            resp = requests.get(QUOTE_URL, headers=headers, timeout=10, params={
                "exchange": r["exchange"], "segment": r["segment"], "trading_symbol": r["symbol"]})
            p = resp.json().get("payload") or {}
            r["price"] = p.get("last_price")
            r["_volume"] = p.get("volume")
            r["change_pct"] = compute_change_pct(p.get("last_price"), (p.get("ohlc") or {}).get("close"))
        except Exception:
            continue


def search(keyword, limit=25):
    df = _load()
    kw = keyword.lower()
    sc = _col(df, "trading_symbol", "tradingsymbol")
    nc = _col(df, "name")
    gc = _col(df, "groww_symbol")
    mask = df[sc].fillna("").astype(str).str.lower().str.contains(kw, regex=False)
    if nc:
        mask |= df[nc].fillna("").astype(str).str.lower().str.contains(kw, regex=False)
    if gc:
        mask |= df[gc].fillna("").astype(str).str.lower().str.contains(kw, regex=False)
    rows = []
    for _, m in df[mask].head(limit).iterrows():
        g = lambda c: m[c] if c in df.columns else None
        sym = m[sc]
        itype = g("instrument_type")
        otype = option_type_from_symbol(sym) if itype in ("CE", "PE") or "OPT" in str(itype) else itype
        otype = otype or ("EQ" if itype == "EQ" else itype)
        strike = g("strike_price")
        rows.append(build_row(sym, g("name"), g("underlying_symbol") if pd.notna(g("underlying_symbol")) else g("name"),
                              g("exchange"), g("segment"), g("expiry_date"),
                              strike if pd.notna(strike) and strike else None, otype, sym))
    _attach_quotes(rows)
    return sort_by_liquidity(rows)
~~~

### `extension/manifest.json`

~~~json
{
  "manifest_version": 3,
  "name": "Broker Search Compare",
  "version": "0.2.0",
  "description": "Compare search results for a keyword across Angel One and Groww.",
  "permissions": ["tabs", "scripting", "storage"],
  "host_permissions": ["https://groww.in/*", "http://localhost:8000/*", "http://127.0.0.1:8000/*"],
  "action": {"default_popup": "popup.html"}
}
~~~

### `extension/popup.html`

~~~html
<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;width:220px;background:#07090c;font-family:Inter,Segoe UI,sans-serif">
<button id="open" style="width:100%;padding:14px;background:#0f1318;color:#d7dce4;border:0;border-bottom:2px solid #5b8cff;font-weight:600;font-size:13px;cursor:pointer">▲ Open Search Compare</button>
<script src="popup.js"></script></body></html>
~~~

### `extension/popup.js`

~~~javascript
document.getElementById("open").onclick = () => chrome.tabs.create({ url: chrome.runtime.getURL("runner.html") });
~~~

### `extension/runner.html`

~~~html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Search Compare — Angel One vs Groww</title>
<meta name="description" content="Compare search results for a keyword across Angel One and Groww side by side.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="runner.css">
</head>
<body>
<header class="topbar">
  <div class="brand">
    <span class="logo">▲</span>
    <span class="brand-name">Search Compare</span>
    <span class="brand-sub">Angel One · Groww</span>
  </div>
  <form class="searchbox" id="search-form">
    <span class="prompt">&gt;</span>
    <input id="kws" placeholder="Search keywords, comma separated — e.g. nifty, sens, gold" autocomplete="off" spellcheck="false">
    <kbd>Enter</kbd>
  </form>
  <div class="status" id="backend"><span class="dot"></span><span class="status-text">checking</span></div>
</header>

<nav class="tabs">
  <span class="tabs-label">Compare</span>
  <div class="chips" id="chips">
    <button class="chip active" data-b="all" id="chip-all">Both</button>
    <button class="chip" data-b="angelone" id="chip-angelone">Angel One</button>
    <button class="chip" data-b="groww" id="chip-groww">Groww</button>
  </div>
  <div class="spacer"></div>
  <button class="btn primary" id="go">Run search</button>
  <button class="btn" id="clear">Clear</button>
</nav>

<main>
  <section class="info-row">
    <div class="info" id="info-angelone">
      <span class="tag tag-blue">AO</span>
      <div><div class="info-title">Angel One</div>
        <div class="info-sub">Official SmartAPI search via local backend</div></div>
    </div>
    <div class="info" id="info-groww">
      <span class="tag tag-green">GW</span>
      <div><div class="info-title">Groww</div>
        <div class="info-sub mono" id="groww-url"></div></div>
    </div>
  </section>

  <section class="console" id="console">
    <div class="console-head">
      <span>console</span>
      <span class="console-hint">python run.py must be running</span>
    </div>
    <pre id="log"><span class="muted">ready.</span></pre>
  </section>

  <section id="results"></section>
</main>
<script src="runner.js"></script>
</body>
</html>
~~~

### `extension/runner.css`

~~~css
:root{
  --bg:#07090c; --bg-2:#0c0f14; --panel:#0f1318; --panel-2:#131820; --line:#1c222b; --line-2:#252c37;
  --text:#d7dce4; --text-2:#a3abb8; --mute:#6b7380;
  --blue:#5b8cff; --blue-bg:#5b8cff1a; --green:#1fc77e; --green-bg:#1fc77e17;
  --red:#f2545b; --red-bg:#f2545b17; --amber:#e9a23b; --amber-bg:#e9a23b17; --violet:#a07cff; --violet-bg:#a07cff17;
  --sans:Inter,"Segoe UI",system-ui,sans-serif; --mono:"JetBrains Mono",Consolas,ui-monospace,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:13px;-webkit-font-smoothing:antialiased}
body{min-height:100vh;background:
  linear-gradient(var(--bg),var(--bg)) padding-box,
  repeating-linear-gradient(0deg,#ffffff03 0 1px,transparent 1px 3px)}
.mono{font-family:var(--mono)}
.muted{color:var(--mute)}
button{font-family:inherit}

/* ---------- top bar ---------- */
.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:24px;padding:10px 24px;
  background:#090c10ee;border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.brand{display:flex;align-items:baseline;gap:10px;white-space:nowrap}
.logo{color:var(--blue);font-size:15px;transform:translateY(1px)}
.brand-name{font-weight:700;font-size:14px;letter-spacing:.2px}
.brand-sub{color:var(--mute);font-size:11.5px}
.searchbox{flex:1;max-width:620px;margin-left:auto;display:flex;align-items:center;gap:8px;
  background:var(--bg-2);border:1px solid var(--line-2);border-radius:6px;padding:0 10px;transition:border-color .15s,box-shadow .15s}
.searchbox:focus-within{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-bg)}
.prompt{font-family:var(--mono);color:var(--green);font-weight:600}
.searchbox input{flex:1;background:none;border:0;outline:none;color:var(--text);font-family:var(--mono);font-size:12.5px;padding:9px 0}
.searchbox input::placeholder{color:var(--mute)}
kbd{font-family:var(--mono);font-size:10.5px;color:var(--mute);border:1px solid var(--line-2);border-radius:4px;padding:1px 6px}
.status{display:flex;align-items:center;gap:7px;font-size:11.5px;color:var(--mute);white-space:nowrap}
.dot{width:7px;height:7px;border-radius:50%;background:var(--mute)}
.status.ok .dot{background:var(--green);box-shadow:0 0 8px var(--green)}
.status.ok{color:var(--text-2)}
.status.down .dot{background:var(--red);box-shadow:0 0 8px var(--red)}
.status.down{color:var(--red)}

/* ---------- tab row ---------- */
.tabs{display:flex;align-items:center;gap:14px;padding:10px 24px;border-bottom:1px solid var(--line);background:var(--bg-2)}
.tabs-label{font-weight:600;font-size:12.5px;color:var(--text-2)}
.chips{display:flex;gap:8px}
.chip{background:transparent;color:var(--text-2);border:1px solid var(--line-2);border-radius:5px;padding:6px 14px;
  font-size:11.5px;font-weight:500;letter-spacing:.2px;cursor:pointer;transition:all .15s}
.chip:hover{border-color:var(--mute);color:var(--text)}
.chip.active{background:var(--blue-bg);border-color:var(--blue);color:var(--blue)}
.spacer{flex:1}
.btn{background:transparent;color:var(--text-2);border:1px solid var(--line-2);border-radius:5px;padding:7px 16px;
  font-size:11.5px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;cursor:pointer;transition:all .15s}
.btn:hover{color:var(--text);border-color:var(--mute)}
.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}
.btn.primary:hover{filter:brightness(1.1)}
.btn:disabled{opacity:.5;cursor:progress}

main{padding:18px 24px 40px;max-width:1800px;margin:0 auto}

/* ---------- info row ---------- */
.info-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-bottom:14px}
.info{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 16px}
.info.hidden{display:none}
.info-title{font-weight:600;font-size:12.5px}
.info-sub{color:var(--mute);font-size:11.5px;margin-top:2px}
.info-sub.mono{font-size:11px;user-select:all}

/* ---------- tags ---------- */
.tag{display:inline-flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:10px;font-weight:600;
  border-radius:3px;padding:2px 6px;letter-spacing:.3px;line-height:1.4}
.tag-blue{background:var(--blue-bg);color:var(--blue)}
.tag-green{background:var(--green-bg);color:var(--green)}
.tag-red{background:var(--red-bg);color:var(--red)}
.tag-amber{background:var(--amber-bg);color:var(--amber)}
.tag-violet{background:var(--violet-bg);color:var(--violet)}
.tag-grey{background:#ffffff0d;color:var(--text-2)}
.info .tag{width:30px;height:30px;font-size:11px;border-radius:5px}

/* ---------- console ---------- */
.console{background:#05070a;border:1px solid var(--line);border-radius:8px;margin-bottom:22px;overflow:hidden}
.console-head{display:flex;justify-content:space-between;padding:7px 14px;border-bottom:1px solid var(--line);
  font-family:var(--mono);font-size:10.5px;color:var(--mute);text-transform:uppercase;letter-spacing:.6px}
#log{margin:0;padding:10px 14px;font-family:var(--mono);font-size:11.5px;line-height:1.7;color:var(--text-2);
  max-height:150px;overflow:auto;white-space:pre-wrap}
#log .ok{color:var(--green)} #log .warn{color:var(--amber)} #log .err{color:var(--red)} #log .ts{color:var(--mute)}
#log::after{content:"▌";color:var(--green);animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}

/* ---------- result blocks ---------- */
.kw-block{margin-bottom:28px;animation:fade .25s ease both}
@keyframes fade{from{opacity:0;transform:translateY(4px)}}
.kw-head{display:flex;align-items:baseline;gap:12px;margin-bottom:10px}
.kw-head h2{margin:0;font-size:15px;font-weight:700}
.kw-head .q{font-family:var(--mono);color:var(--blue)}
.kw-head .meta{color:var(--mute);font-size:11.5px}
.grid{display:grid;grid-template-columns:repeat(var(--cols,2),minmax(0,1fr));gap:16px}
@media(max-width:1100px){.grid{grid-template-columns:1fr}}

.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.card-h{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line)}
.card-h h3{margin:0;font-size:13px;font-weight:600}
.card-h .badges{margin-left:auto;display:flex;gap:6px;align-items:center}
.card-note{padding:7px 16px;font-size:11px;color:var(--mute);border-bottom:1px solid var(--line);background:var(--bg-2)}

.scroll{max-height:62vh;overflow:auto}
.scroll::-webkit-scrollbar{width:8px;height:8px}
.scroll::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:4px}
table{width:100%;border-collapse:collapse}
th{position:sticky;top:0;background:var(--panel-2);text-align:left;color:var(--blue);font-weight:500;font-size:11px;
  padding:9px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
th.r,td.r{text-align:right}
td{padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap;font-size:12px;vertical-align:middle}
tr:last-child td{border-bottom:0}
tbody tr{transition:background .12s}
tbody tr:hover td{background:#ffffff05}
td.idx{color:var(--mute);font-family:var(--mono);font-size:11px;width:28px}
.sym{font-weight:600;color:var(--text);letter-spacing:.1px}
.sym-sub{color:var(--mute);font-size:11px;margin-left:6px}
.inst{display:flex;align-items:center;gap:6px;flex-wrap:nowrap}
.num{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums}
.up{color:var(--green)} .down{color:var(--red)}
.empty{padding:36px;text-align:center;color:var(--mute);font-size:12px}
.loader{display:inline-block;font-family:var(--mono);color:var(--blue)}
.loader::after{content:"⠋";animation:spin .8s steps(1) infinite}
@keyframes spin{0%{content:"⠋"}12%{content:"⠙"}25%{content:"⠹"}37%{content:"⠸"}50%{content:"⠼"}62%{content:"⠴"}75%{content:"⠦"}87%{content:"⠧"}}
~~~

### `extension/runner.js`

~~~javascript
// Angel One vs Groww search compare.
// Groww: opens groww.in in a background tab (a normal visit in your own browser), reads the
//        rendered results, stores them via the local backend.
// Angel One: the local backend calls Angel One's official SmartAPI search.
const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BASE = "http://127.0.0.1:8000";
const GROWW_URL = "https://groww.in/search?q={q}";   // fixed, not user-editable
const NAMES = { angelone: "Angel One", groww: "Groww" };
const TAGS = { angelone: ["AO", "tag-blue"], groww: ["GW", "tag-green"] };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

$("groww-url").textContent = GROWW_URL;

// ---------- console ----------
let logStarted = false;
function log(msg, cls = "") {
  if (!logStarted) { $("log").innerHTML = ""; logStarted = true; }
  const ts = new Date().toLocaleTimeString("en-GB");
  $("log").insertAdjacentHTML("beforeend", `<span class="ts">${ts}</span>  <span class="${cls}">${esc(msg)}</span>\n`);
  $("log").scrollTop = 1e9;
}

// ---------- broker chips + persistence ----------
let broker = "all";
function setBroker(b) {
  broker = b;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c.dataset.b === b));
  const sel = selectedBrokers();
  ["angelone", "groww"].forEach((x) => $("info-" + x).classList.toggle("hidden", !sel.includes(x)));
  chrome.storage.local.set({ broker: b });
}
function selectedBrokers() { return broker === "all" ? ["angelone", "groww"] : [broker]; }
document.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => setBroker(c.dataset.b)));

chrome.storage.local.get(["kws", "broker"], (d) => {
  if (d.kws) $("kws").value = d.kws.replace(/\n+/g, ", ");
  setBroker(["all", "angelone", "groww"].includes(d.broker) ? d.broker : "all");
});
$("kws").addEventListener("input", () => chrome.storage.local.set({ kws: $("kws").value }));

// ---------- backend status ----------
async function checkBackend() {
  const el = $("backend");
  try {
    await fetch(BASE + "/");
    el.className = "status ok"; el.querySelector(".status-text").textContent = "backend online";
  } catch {
    el.className = "status down"; el.querySelector(".status-text").textContent = "backend offline";
  }
}
checkBackend(); setInterval(checkBackend, 10000);

// ---------- tab helpers (retry: Chrome rejects tab edits while a tab is being dragged) ----------
async function retry(fn, tries = 10) {
  for (let i = 0; ; i++) {
    try { return await fn(); } catch (e) {
      if (i >= tries || !/cannot be edited|dragging/i.test(e.message || "")) throw e;
      await sleep(400);
    }
  }
}
function waitForLoad(tabId, timeout = 20000) {
  return new Promise((resolve) => {
    const done = () => { chrome.tabs.onUpdated.removeListener(l); clearTimeout(t); resolve(); };
    const l = (id, info) => { if (id === tabId && info.status === "complete") done(); };
    const t = setTimeout(done, timeout);
    chrome.tabs.onUpdated.addListener(l);
    chrome.tabs.get(tabId, (tab) => { if (tab && tab.status === "complete") done(); });
  });
}

// ---------- injected into the Groww page ----------
function growwPageScript() {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const lines = (el) => el.innerText.split("\n").map((s) => s.trim()).filter(Boolean);
  const read = () => {
    // Scope to the block right after the "SEARCH RESULTS" heading so the unrelated
    // "trending" widget is never picked up.
    const h = [...document.querySelectorAll("*")].find(
      (e) => e.children.length === 0 && /^search results$/i.test(e.textContent.trim()));
    if (!h) return [];
    const scope = h.nextElementSibling || (h.parentElement && h.parentElement.nextElementSibling);
    if (!scope) return [];
    return [...scope.querySelectorAll('[class*="SearchPageV2_suggestionItem"]')].map((el) => {
      const t = lines(el); return { symbol: t[0], underlying: t[1] || null };
    });
  };
  return (async () => {
    let last = -1, stable = 0, rows = [];
    for (let i = 0; i < 40; i++) {
      await wait(300);
      rows = read();
      if (rows.length && rows.length === last) { if (++stable >= 3) break; } else stable = 0;
      last = rows.length;
    }
    return { rows, note: rows.length ? "" : "no results found on the page" };
  })();
}

async function captureGroww(kw) {
  const url = GROWW_URL.replace("{q}", encodeURIComponent(kw));
  const tab = await retry(() => chrome.tabs.create({ url, active: false }));
  try {
    await waitForLoad(tab.id);
    const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: growwPageScript });
    const { rows: raw, note } = res.result || { rows: [], note: "script returned nothing" };
    if (!raw.length) { log(`groww  "${kw}"  0 rows, not saved (${note})`, "warn"); return; }
    const rows = raw.map((r) => ({
      symbol: r.symbol, full_name: r.underlying, underlying: r.underlying, exchange: null,
      segment: null, expiry: null, strike: null, option_type: null, price: null, change_pct: null }));
    const resp = await fetch(BASE + "/api/snapshot", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ broker: "groww", keyword: kw, rows }) });
    log(`groww  "${kw}"  ${rows.length} rows captured  [${resp.status}]`, resp.ok ? "ok" : "err");
  } finally {
    await retry(() => chrome.tabs.remove(tab.id)).catch(() => {});
  }
}

// ---------- rendering ----------
function badges(d) {
  switch (d.source) {
    case "live": return `<span class="tag tag-blue">LIVE API</span>`;
    case "mixed": return `<span class="tag tag-blue">LIVE API</span><span class="tag tag-amber">+ TEXT MATCH</span>`;
    case "local": return `<span class="tag tag-amber">TEXT MATCH</span>`;
    case "captured": return `<span class="tag tag-green">CAPTURED</span>`;
    case "error": return `<span class="tag tag-red">ERROR</span>`;
    default: return `<span class="tag tag-amber">FALLBACK</span>`;
  }
}
function note(d) {
  switch (d.source) {
    case "mixed": return `Angel One's API only matches the start of a symbol — rows tagged TXT come from Angel One's instrument list. Order is relevance-ranked by this tool.`;
    case "local": return `Angel One's API returned nothing — rows are substring matches from Angel One's instrument list.`;
    case "captured": return `Captured from groww.in · ${esc(d.captured_at)}`;
    case "error": return esc(d.error);
    case "fallback": return `Not captured — plain text match on the instrument list, not Groww's real search.`;
    default: return "";
  }
}
const TYPE_TAG = { CE: "tag-green", PE: "tag-red", FUT: "tag-violet", EQ: "tag-blue" };
function fmtNum(v) { return v == null ? "" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

function row(r, i) {
  const c = r.change_pct;
  const dir = c > 0 ? "up" : c < 0 ? "down" : "";
  const arrow = c > 0 ? " ▲" : c < 0 ? " ▼" : "";
  const tags = [
    r.option_type ? `<span class="tag ${TYPE_TAG[r.option_type] || "tag-grey"}">${esc(r.option_type)}</span>` : "",
    r.exchange ? `<span class="tag tag-grey">${esc(r.exchange)}</span>` : "",
    r.match === "text" ? `<span class="tag tag-amber">TXT</span>` : "",
  ].join("");
  return `<tr>
    <td class="idx">${i + 1}</td>
    <td><div class="inst"><span class="sym">${esc(r.symbol)}</span>${r.expiry ? `<span class="sym-sub">${esc(r.expiry)}</span>` : ""}${tags}</div></td>
    <td class="muted">${esc(r.underlying)}</td>
    <td class="r num">${r.strike != null ? fmtNum(r.strike) : ""}</td>
    <td class="r num ${dir}">${r.price != null ? "₹" + fmtNum(r.price) + arrow : ""}</td>
    <td class="r num ${dir}">${c != null ? (c > 0 ? "+" : "") + c.toFixed(2) + "%" : ""}</td>
  </tr>`;
}
function card(b, d) {
  const [t, cls] = TAGS[b];
  let body;
  if (!d) body = `<div class="empty"><span class="loader"></span> fetching</div>`;
  else if (!d.rows.length) body = `<div class="empty">No results</div>`;
  else body = `<div class="scroll"><table><thead><tr>
      <th>#</th><th>Instrument</th><th>Underlying</th><th class="r">Strike</th><th class="r">LTP</th><th class="r">Change</th>
    </tr></thead><tbody>${d.rows.map(row).join("")}</tbody></table></div>`;
  const n = d ? note(d) : "";
  return `<section class="card">
    <div class="card-h"><span class="tag ${cls}">${t}</span><h3>${NAMES[b]}</h3>
      <div class="badges">${d ? `<span class="muted">${d.rows.length} results</span>` + badges(d) : ""}</div></div>
    ${n ? `<div class="card-note">${n}</div>` : ""}
    ${body}</section>`;
}
function renderBlock(kw, brokers, data) {
  const id = "kw-" + kw.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  let el = document.getElementById(id);
  if (!el) {
    el = document.createElement("div");
    el.id = id; el.className = "kw-block";
    $("results").prepend(el);
  }
  const when = new Date().toLocaleTimeString("en-GB");
  el.innerHTML = `<div class="kw-head"><h2>Results for <span class="q">"${esc(kw)}"</span></h2><span class="meta">${when}</span></div>
    <div class="grid" style="--cols:${brokers.length}">${brokers.map((b) => card(b, data && data[b])).join("")}</div>`;
}

// ---------- main ----------
async function run() {
  const brokers = selectedBrokers();
  const kws = $("kws").value.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
  if (!kws.length) { log("enter at least one keyword", "warn"); $("kws").focus(); return; }
  $("go").disabled = true;
  log(`run  [${brokers.map((b) => NAMES[b]).join(" + ")}]  ${kws.length} keyword(s)`);
  try {
    for (const kw of kws) {
      renderBlock(kw, brokers, null);
      if (brokers.includes("groww")) {
        try { await captureGroww(kw); } catch (e) { log(`groww  "${kw}"  failed: ${e.message || e}`, "err"); }
      }
      try {
        const data = await (await fetch(`${BASE}/api/search?keyword=${encodeURIComponent(kw)}`)).json();
        if (brokers.includes("angelone")) log(`angel  "${kw}"  ${data.angelone.rows.length} rows (${data.angelone.source})`, "ok");
        renderBlock(kw, brokers, data);
      } catch (e) {
        log(`backend unreachable at ${BASE} — is python run.py running?`, "err");
        renderBlock(kw, brokers, Object.fromEntries(brokers.map((b) => [b, { source: "error", error: "backend not reachable", rows: [] }])));
      }
      await sleep(400);
    }
    log("done", "ok");
  } finally {
    $("go").disabled = false;
  }
}
$("go").addEventListener("click", run);
$("search-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
$("clear").addEventListener("click", () => { $("results").innerHTML = ""; $("log").innerHTML = '<span class="muted">cleared.</span>'; logStarted = false; });
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("kws").focus(); }
});
~~~

### `extension/README.md`

~~~~markdown
# Broker Search Compare (Angel One vs Groww)

1. Start the backend: `python run.py` (project root). It has no web page of its own.
2. `chrome://extensions` → Developer Mode → **Load unpacked** → pick this folder.
3. Click the extension icon → **Open compare page**, enter keywords, click Search.

- **Angel One**: real results from Angel One's official SmartAPI search (credentials in `.env`).
- **Groww**: the extension opens groww.in's search page in a background tab, reads the
  rendered results, and stores them via the backend.

If different keywords show identical Groww rows, the page selector is too broad and needs fixing.
~~~~


