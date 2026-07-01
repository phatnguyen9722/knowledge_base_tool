"""Desktop launcher: runs the web app + a system-tray icon.

Starts Uvicorn in a background thread, opens the browser, and shows a tray icon
with "Open" / "Quit". Works in dev and inside a PyInstaller bundle.
"""

from __future__ import annotations

import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from app.config import load_settings

_settings = load_settings()
PORT = _settings.port
URL = f"http://{_settings.host}:{PORT}"


def run_server():
    from app.main import app

    uvicorn.run(app, host=_settings.host, port=PORT, log_level="error")


def open_browser(icon=None, item=None):
    webbrowser.open(URL)


def quit_app(icon, item):
    icon.stop()
    sys.exit(0)


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def main():
    import pystray
    from PIL import Image

    # Start the server in the background, then open the browser.
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1.5)
    open_browser()

    icon_path = _base() / "static" / "icon.png"
    img = Image.open(str(icon_path))
    menu = pystray.Menu(
        pystray.MenuItem("Open Knowledge Base", open_browser, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )
    pystray.Icon("KnowledgeBase", img, "KB Tool", menu).run()


if __name__ == "__main__":
    main()
