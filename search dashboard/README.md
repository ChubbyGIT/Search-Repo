# Angel One vs Groww — Search Compare

Type a word like `nifty` or `gold`. See what **Angel One** and **Groww** show for it, side by side, in a dark terminal-style page.

## What is in this folder?

| Thing | What it does |
|---|---|
| `run.py` | Starts the small helper program (the "backend"). You run this one. |
| `app.py` | The helper program itself. |
| `services/` | The code that talks to Angel One and stores Groww results. |
| `extension/` | A Chrome extension. This is the page you actually look at. |
| `.env` | Where you type your Angel One secret details. **Placeholders only for now.** |
| `recreate.md` | A full copy of all the code + build notes, to rebuild this elsewhere. |

## How it works (in plain words)

- **Angel One:** your helper program asks Angel One's official search. Results come back live.
- **Groww:** Groww has no official search for outsiders. So the Chrome extension opens Groww's normal search page in a background tab (just like you would), reads what is on screen, and saves it.
- The extension page then shows both lists next to each other.

> Angel One's official search only matches the **start** of a name, and returns things A→Z. So this tool also adds matches from Angel One's own instrument list (tagged `TXT`) and sorts by relevance. That sorting is done by this tool, not by Angel One.

---

## Step-by-step setup

You do this once. Take your time.

### Step 0 — Things you need first
1. A computer with **Windows, Mac or Linux**.
2. **Google Chrome**.
3. **Python 3.9 or newer**. Check: open a terminal (see Step 1) and type `python --version`. If it shows a number, you have it. If not, download it from https://www.python.org/downloads/ and **tick "Add Python to PATH"** while installing.
4. An **Angel One account** (needed for the Angel One column only).

### Step 1 — Download this folder
1. On the GitHub page, click the green **Code** button.
2. Click **Download ZIP**.
3. Find the ZIP in your Downloads. Right-click → **Extract All**.
4. Remember where the folder is. Example: `Desktop\search-dashboard`.

### Step 2 — Open a terminal inside the folder
- **Windows:** open the folder, click the address bar at the top, type `powershell`, press Enter.
- **Mac:** right-click the folder → **New Terminal at Folder**.

A black or white window opens. Keep it open.

### Step 3 — Get your Angel One keys
1. Go to https://smartapi.angelone.in/ and log in.
2. Click **My Apps** (or go to https://smartapi.angelone.in/new/apps) → **Add App**.
3. Fill the form:
   - **App Name:** anything, e.g. `dashboard search`
   - **Redirect URL:** `https://www.google.com` (it does not accept localhost; this is never used)
   - **Post back URL:** leave empty
   - **Primary Static IP:** your public IP. Google "what is my ip" and copy the number.
4. Click **Add**.
5. Open the new app and **copy the API Key**. Paste it in a notepad for now.
6. Click **Enable TOTP** at the top of the SmartAPI site and follow the steps. It shows a QR code and a **text code** under it. **Copy the text code.** That is your *TOTP secret*. Also scan the QR code with an authenticator app (Google Authenticator) to finish enabling.
7. Find your **Client ID** (your Angel One login ID, like `A123456`) and your 4-digit **login PIN**.

### Step 4 — Put your keys in `.env`
1. In the folder, open the file named `.env` with Notepad (right-click → Open with → Notepad).
   - Can't see it? On Windows, in File Explorer click **View → Show → Hidden items**.
2. Replace the placeholder words:

```
ANGEL_ONE_API_KEY=paste the API key here
ANGEL_ONE_CLIENT_ID=paste your client ID here
ANGEL_ONE_PASSWORD=paste your 4-digit PIN here
ANGEL_ONE_TOTP_SECRET=paste the text code here
```
3. No spaces around `=`. No quotes. Save the file.

> ⚠️ **Never upload your real `.env` to GitHub or send it to anyone.** Anyone with those values can access your account.

### Step 5 — Start the helper program
In the terminal from Step 2, type this and press Enter:

```
python run.py
```
- First time, it installs a few things. Wait. This can take a minute.
- When you see `Uvicorn running on http://127.0.0.1:8000`, it is working.
- **Leave this window open.** Closing it stops everything.

(Mac/Linux: if `python` doesn't work, use `python3 run.py`.)

### Step 6 — Install the Chrome extension
1. Open Chrome. In the address bar type `chrome://extensions` and press Enter.
2. Turn on **Developer mode** (switch at the top right).
3. Click **Load unpacked**.
4. Choose the **`extension`** folder inside this project (not the main folder).
5. "Broker Search Compare" now appears in the list.
6. Click the puzzle-piece icon in Chrome's toolbar → click the **pin** next to the extension so it stays visible.

> If "Load unpacked" is blocked, your computer (often a work/school laptop) has a rule against it. Use a personal computer.

### Step 7 — Use it
1. Click the extension icon → **Open Search Compare**. A new tab opens.
2. Top right should say **backend online** with a green dot. If red, go back to Step 5.
3. In the search bar type a word. For several, separate with commas: `nifty, sensex, gold`.
4. Press **Enter** (or click **Run search**).
5. Wait a few seconds. Angel One is slow on purpose (about 5–7 seconds per word) because its search only allows one request per second.
6. Tables appear. Left: Angel One. Right: Groww.

Buttons: **Both / Angel One / Groww** pick which side to run. **Clear** wipes the page.

### Step 8 — Next time
1. Open a terminal in the folder → `python run.py`.
2. Open the extension page.
3. Search.

If you changed any extension file, go to `chrome://extensions` and click the **reload** (circular arrow) on the extension.

---

## If something goes wrong

| Problem | Fix |
|---|---|
| `python` not recognised | Reinstall Python and tick **Add Python to PATH**, or try `python3`. |
| Red **backend offline** | `python run.py` is not running. Start it (Step 5). |
| Angel One badge says **TEXT MATCH** only | Login failed. Re-check the four values in `.env` (no spaces, PIN not password). Restart `python run.py`. Make sure TOTP is enabled. |
| Angel One shows "access denied / rate" | You searched too fast. Wait a few seconds. |
| Groww says "0 rows, not saved" | Groww changed its page. The selectors in `extension/runner.js` (`growwPageScript`) need updating. |
| "Tabs cannot be edited" | You were dragging a tab. It retries by itself; don't drag tabs while it runs. |
| Changes not showing | Reload the extension on `chrome://extensions`, then reopen the page. |

## Things to know
- Groww is read only by loading its normal public page in **your own browser**, like a person would. This tool never calls Groww's private APIs.
- Prices and % change show for Angel One only (they come from Angel One's quote API).
- Groww results only carry name + underlying (no strike/expiry/type).
- Everything runs on your own computer (`127.0.0.1`). Nothing is hosted.
- This is a comparison tool, not financial advice.
