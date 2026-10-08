# Angel One vs Groww — Search Compare

Type a word like `nifty` or `gold` and see what **Angel One** and **Groww** return for it, side by side, in a dark terminal-style page.

No browser extension and no downloads beyond Python packages. Works on Windows, macOS and Linux.

## Workflow

1. Run `python run.py`
2. Open http://127.0.0.1:8000
3. Type keyword(s), press Enter, read the results

## Project layout

| Path | What it does |
|---|---|
| `run.py` | Launcher: installs missing packages and starts the server. |
| `app.py` | FastAPI server. Serves the dashboard and `/api/search`. |
| `web/` | The dashboard page (HTML, CSS, JS). |
| `services/angelone.py`, `angelone_auth.py` | Angel One SmartAPI search + login. |
| `services/groww.py` | Groww search through groww.in's public JSON endpoint. |
| `services/snapshots.py` | Saves the last Groww result per keyword (SQLite) as an offline fallback. |
| `services/cache.py`, `common.py` | Instrument-list caching and shared helpers. |
| `.env.example` | Template for your Angel One credentials. |

## How it works

- **Angel One:** the backend logs in and calls the official SmartAPI search. That search only matches the **start** of a name and returns A→Z, so the backend also adds substring matches from Angel One's instrument list (tagged `TXT`) and sorts by relevance.
- **Groww:** the backend calls `https://groww.in/v1/api/search/v1/entity?q=<keyword>`, the same endpoint groww.in's search box uses. No login or API key. Each result is saved in `snapshots.db`; if Groww can't be reached later, the last saved result is shown (badge `CAPTURED`).

## Setup

**Requirements:** Python 3.9+, internet access to `angelone.in` and `groww.in`, and an Angel One account (Angel One column only).

1. Get the code (`git clone` or Download ZIP).
2. Copy `.env.example` to `.env` and fill in the four Angel One values (see below).
3. In a terminal inside the folder: `python run.py` (Mac/Linux: `python3 run.py`). First run installs packages.
4. Open http://127.0.0.1:8000. Top right should say **backend online**.

### Angel One keys
1. Log in at https://smartapi.angelone.in/ → **My Apps** → **Add App**.
2. Redirect URL: `https://www.google.com`. Primary Static IP: your public IP.
3. Copy the **API Key**.
4. **Enable TOTP**; copy the **text code** under the QR code (this is the TOTP secret) and scan the QR in an authenticator app.
5. Client ID = your Angel One login ID. Password = your 4-digit PIN.

Put them in `.env` with no spaces around `=` and no quotes.

> Never commit your real `.env`. It is in `.gitignore`.

## Using the dashboard

- Several keywords: separate with commas, e.g. `nifty, sensex, gold`.
- **Both / Angel One / Groww** chooses which side to run. **Clear** wipes the page.
- Angel One is deliberately slow (~5–7 s per word) because its search allows one request per second.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not recognised | Install Python and tick **Add Python to PATH**, or use `python3`. |
| **backend offline** | `python run.py` isn't running. |
| Page doesn't load data | Open it via http://127.0.0.1:8000, not as a file. Hard refresh (Ctrl/Cmd+Shift+R). |
| Angel One badge says **TEXT MATCH** only | Login failed. Check the four `.env` values and that TOTP is enabled; restart. |
| Angel One "access denied / rate" | Searched too fast. Wait a few seconds. |
| Groww shows `ERROR` / `CAPTURED` | `groww.in` is blocked on your network, or Groww changed its endpoint (`services/groww.py`). |

## Notes

- Groww's search endpoint is unofficial and could change without notice.
- Prices and % change appear for Angel One only; Groww rows carry name, type, exchange and expiry.
- Everything runs on `127.0.0.1`; nothing is hosted.
- A comparison tool, not financial advice.
