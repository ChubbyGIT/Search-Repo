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
