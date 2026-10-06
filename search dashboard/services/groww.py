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
