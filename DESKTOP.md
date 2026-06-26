# Guleed Spareparts — Offline Desktop App

Run the whole system **locally on a shop PC, with no internet**. Data is stored
in a SQLite file on that computer. This is the recommended setup for use where
the internet is unstable — it works 24/7 regardless of connectivity.

It is the **same app** as the cloud website; it just uses a **local database**
instead of Supabase (selected automatically by `desktop.py`).

---

## 1. Run it from source (needs Python installed)

```bash
pip install -r backend/requirements.txt
pip install -r requirements-desktop.txt
python desktop.py
```

A window titled **Guleed Spareparts** opens. Log in with:

* **Username:** `admin`
* **Password:** `admin`  → change it after first login (create real employee accounts under **Users**).

Data is stored in:

```
%LOCALAPPDATA%\GuleedSpareparts\guleed.db      (database)
%LOCALAPPDATA%\GuleedSpareparts\uploads\       (part images)
```

---

## 2. Build a standalone .exe (no Python needed on the shop PC)

Do this **once on a Windows machine**. Employees then just copy and double-click
the resulting `GuleedSpareparts.exe`.

```bash
pip install -r backend/requirements.txt
pip install -r requirements-desktop.txt

pyinstaller --noconfirm --onefile --name GuleedSpareparts ^
  --add-data "frontend;frontend" ^
  --collect-all backend ^
  --collect-submodules uvicorn ^
  desktop.py
```

The app appears at `dist\GuleedSpareparts.exe`.

* First build with a console (above) so you can see any errors.
* For the final, polished build add `--windowed` to hide the console.
* If launching the .exe shows a `ModuleNotFoundError`, add
  `--collect-all <module>` (e.g. `--collect-all scipy`) and rebuild.

The .exe is large (~200–400 MB) because it bundles Python + scipy/pandas. That's
normal for a self-contained app.

---

## 3. Make it start automatically (optional)

To launch on boot, put a shortcut to `GuleedSpareparts.exe` in:

```
shell:startup        (paste into the Windows Run dialog, Win+R)
```

---

## 4. Backups (important!)

All data lives in one file: `%LOCALAPPDATA%\GuleedSpareparts\guleed.db`.
Copy it regularly to a USB stick or cloud drive. To restore, just put the file
back. (Close the app first.)

---

## Local vs Cloud — which database?

`desktop.py` sets `DATABASE_URL` to the local SQLite file, so the desktop app is
fully offline. The cloud website (Render) sets `DATABASE_URL` to Supabase. The
two databases are **separate** — data does not flow between them automatically.
