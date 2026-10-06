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
