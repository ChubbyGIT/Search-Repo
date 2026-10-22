"""Groww Individual: the same Groww search endpoint, called with YOUR logged-in session.

Credential: copy it from a logged-in groww.in tab (DevTools -> Network -> the `entity?...q=`
search request -> Request Headers). Accepted pasted forms:
  - the Authorization header value ("Bearer eyJ..." or the bare JWT), or
  - the whole Cookie header value (anything containing "name=value" pairs).
Never stored: used in memory for one request plus a short in-process cache.
"""
import time

import requests

from .groww import HEADERS, SEARCH_URL, rows_from_response

RESULT_CACHE_TTL = 300
_result_cache = {}


def _auth_headers(credential):
    c = credential.strip()
    if c.lower().startswith("cookie:"):
        c = c[7:].strip()
    if c.lower().startswith("authorization:"):
        c = c[14:].strip()
    if "=" in c and not c.lower().startswith("bearer "):
        return {"Cookie": c}
    if not c.lower().startswith("bearer "):
        c = "Bearer " + c
    return {"Authorization": c}


def search(keyword, credential, size=25):
    key = (keyword.strip().lower(), credential.strip())
    hit = _result_cache.get(key)
    if hit and time.time() - hit[0] < RESULT_CACHE_TTL:
        return [dict(r) for r in hit[1]], "live"
    resp = requests.get(SEARCH_URL, headers={**HEADERS, **_auth_headers(credential)}, timeout=15,
                        params={"app": "false", "page": 0, "q": keyword, "size": size})
    if resp.status_code in (401, 403):
        raise RuntimeError(f"Groww rejected the credential (HTTP {resp.status_code}) - token expired?")
    resp.raise_for_status()
    rows = rows_from_response(resp.json())
    _result_cache[key] = (time.time(), [dict(r) for r in rows])
    return rows, "live"
