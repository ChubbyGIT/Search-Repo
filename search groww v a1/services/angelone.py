import time
import uuid

import requests

from .common import build_row, option_type_from_symbol

SEARCH_URL = "https://global-search-bbe-prod.angelone.in/v5/search"
ORIGIN = "https://www.angelone.in"
TOKEN_COOKIE = "prod_non_trade_access_token"
SEARCH_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "app-version": "sparkweb1",
    "applicationname": "Spark-Web",
    "content-type": "application/json",
    "origin": ORIGIN,
    "referer": ORIGIN + "/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "x-build-number": "100",
    "x-sourceid": "3",
    "x-tokentype": "non_trade_access_token",
}
RESULT_CACHE_TTL = 300

_result_cache = {}


def _exchange_from_scriptype(scrip_type):
    st = (scrip_type or "").lower()
    if st.startswith("nse"):
        return "NSE"
    if st.startswith("bse"):
        return "BSE"
    if st.startswith("mcx"):
        return "MCX"
    if st.startswith("cd") or st.startswith("cur"):
        return "CDS"
    return None


def _strike(v):
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _expiry(v):
    if not v or v == "01 Jan 1980":
        return None
    return v


def _option_type(item, sym):
    ot = (item.get("optType") or "").upper()
    if ot in ("CE", "PE"):
        return ot
    if (item.get("instName") or "").upper().startswith("FUT"):
        return "FUT"
    return option_type_from_symbol(sym)


def _exch_label(exchange, inst_name):
    if not exchange:
        return None
    is_fo = (inst_name or "").upper().startswith(("FUT", "OPT"))
    return f"{exchange} FO" if is_fo else exchange


def _row_from_search_item(item):
    sym = item.get("tradeSymbol") or item.get("symbolName")
    name = item.get("compName") or item.get("symbolName")
    inst_name = item.get("instName") or item.get("astCls")
    exchange = _exchange_from_scriptype(item.get("scripType"))
    row = build_row(sym, name, name, exchange, inst_name,
                    _expiry(item.get("expirydate")), _strike(item.get("strkPrice")),
                    _option_type(item, sym), item.get("token"))
    row["exch_label"] = _exch_label(exchange, inst_name)
    return row


def _search_live(keyword, ntt_token):
    token = (ntt_token or "").strip()
    if not token:
        raise RuntimeError("NTT token required")
    headers = {**SEARCH_HEADERS, "x-deviceid": str(uuid.uuid4()), "x-requestid": str(uuid.uuid4())}
    cookies = {TOKEN_COOKIE: token}
    params = {"userType": "B2C", "accountType": "D", "keyword": keyword}
    r = requests.get(SEARCH_URL, params=params, headers=headers, cookies=cookies, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(data.get("message") or "Angel One search failed")
    items = (data.get("data") or {}).get("dataList") or []
    seen, rows = set(), []
    for item in items:
        if item.get("type") != "scrip":
            continue
        key = (item.get("tradeSymbol"), item.get("token"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row_from_search_item(item))
    return rows


def search(keyword, ntt_token, limit=25):
    key = (keyword.strip().lower(), ntt_token.strip())
    hit = _result_cache.get(key)
    if hit and time.time() - hit[0] < RESULT_CACHE_TTL:
        return [dict(r) for r in hit[1]], hit[2]

    rows = _search_live(keyword, ntt_token)[:limit]
    source = "live"
    _result_cache[key] = (time.time(), [dict(r) for r in rows], source)
    return rows, source
