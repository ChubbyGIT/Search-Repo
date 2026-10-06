# Broker Search Compare (Angel One vs Groww)

1. Start the backend: `python run.py` (project root). It has no web page of its own.
2. `chrome://extensions` → Developer Mode → **Load unpacked** → pick this folder.
3. Click the extension icon → **Open compare page**, enter keywords, click Search.

- **Angel One**: real results from Angel One's official SmartAPI search (credentials in `.env`).
- **Groww**: the extension opens groww.in's search page in a background tab, reads the
  rendered results, and stores them via the backend.

If different keywords show identical Groww rows, the page selector is too broad and needs fixing.
