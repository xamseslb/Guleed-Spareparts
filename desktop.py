"""
desktop.py – Run Guleed Spareparts as a LOCAL, OFFLINE desktop application.

It starts the FastAPI backend on a local port, stores all data in a SQLite
file on THIS computer, and opens the app in its own window. No internet needed.

  Run from source:          python desktop.py
  Build a standalone .exe:   see DESKTOP.md

Data location (database + uploaded images):
  %LOCALAPPDATA%\\GuleedSpareparts\\   (Windows)
"""

import os
import sys
import time
import socket
import threading


def resource_base():
    """Folder that contains the bundled 'backend' and 'frontend' files."""
    if getattr(sys, "frozen", False):          # running inside a PyInstaller bundle
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Writable folder for the database + uploads (persists across app updates)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "GuleedSpareparts")
    os.makedirs(d, exist_ok=True)
    return d


def find_free_port(preferred=8765):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", preferred))
        return preferred
    except OSError:
        s.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        return port
    finally:
        s.close()


# ── Configure for LOCAL OFFLINE use (must run BEFORE importing backend) ──
BASE = resource_base()
DATA = data_dir()

os.environ.setdefault("ENVIRONMENT", "local")          # not "production" → tables auto-create
db_path = os.path.join(DATA, "guleed.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"    # local file – no internet, no Supabase
os.environ.setdefault("SECRET_KEY", "local-offline-secret")
os.environ.setdefault("SEED_ON_STARTUP", "false")      # no demo data
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin")       # default local admin – CHANGE after first login
os.environ["UPLOAD_DIR"] = os.path.join(DATA, "uploads")
os.environ["FRONTEND_DIR"] = os.path.join(BASE, "frontend")

if BASE not in sys.path:
    sys.path.insert(0, BASE)

PORT = find_free_port(8765)
URL = f"http://127.0.0.1:{PORT}/app/login.html"


def run_migrations():
    """
    Bring the local database schema up to date with Alembic, so new versions
    of the app can add columns/tables WITHOUT losing existing data.

    - Fresh database  → migrations create everything.
    - Existing (migrated) database → only new migrations are applied.
    - A pre-migration database (made by an older build) is adopted by stamping
      it to head; brand-new installs never hit that path.
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect

    url = os.environ["DATABASE_URL"]
    cfg = Config(os.path.join(BASE, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)

    engine = create_engine(url)
    insp = inspect(engine)
    has_version = insp.has_table("alembic_version")
    has_data = insp.has_table("parts")
    engine.dispose()

    try:
        if has_data and not has_version:
            command.stamp(cfg, "head")     # adopt a legacy DB into migration control
        else:
            command.upgrade(cfg, "head")   # fresh or already-migrated DB
    except Exception as exc:
        print(f"[warn] migration step skipped: {exc}")


def start_server():
    import uvicorn
    import backend.main  # importing also bootstraps the admin user
    # uvicorn skips signal handlers when not on the main thread, so this is safe
    uvicorn.run(backend.main.app, host="127.0.0.1", port=PORT, log_level="warning")


def wait_until_up(timeout=25):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    print(f"Starting Guleed Spareparts…  data: {DATA}")
    run_migrations()
    threading.Thread(target=start_server, daemon=True).start()
    wait_until_up()
    try:
        import webview  # native window (pip install pywebview)
        webview.create_window("Guleed Spareparts", URL, width=1280, height=820)
        webview.start()
    except Exception:
        # Fall back to the default browser if pywebview isn't available
        import webbrowser
        webbrowser.open(URL)
        print(f"Running at {URL}\nClose this window to stop the program.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
