"""Groww search via Groww's own public JSON search endpoint (the one groww.in's search box uses).
No browser, no extension, no login. Works the same on Windows and macOS.
"""
import requests

SEARCH_URL = "https://groww.in/v1/api/search/v1/entity"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def search(keyword, size=25):
    resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15,
                        params={"app": "false", "page": 0, "q": keyword, "size": size})
    resp.raise_for_status()
    rows = []
    for e in resp.json().get("content") or []:
        title = e.get("title") or e.get("company_short_name") or e.get("symbol")
        if not title:
            continue
        underlying = e.get("underlying_scrip_code") or e.get("symbol") or e.get("company_short_name")
        rows.append({
            "symbol": title, "full_name": title, "underlying": underlying,
            "exchange": e.get("exchange"), "segment": e.get("entity_type"),
            "expiry": e.get("expiry"), "strike": None,
            "option_type": e.get("option_type") if e.get("option_type") in ("CE", "PE") else None,
            "price": None, "change_pct": None,
        })
    return rows
