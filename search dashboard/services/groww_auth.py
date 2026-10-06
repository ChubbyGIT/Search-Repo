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
