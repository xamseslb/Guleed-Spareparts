"""
main.py – The starting point for the entire backend application.

When you run: uvicorn backend.main:app --reload
Python loads this file, creates the FastAPI 'app' object,
and starts listening for incoming HTTP requests.

This file does 4 things:
  1. Creates all database tables (if they don't exist yet)
  2. Runs seed data (adds sample parts/users on first run)
  3. Configures middleware (CORS, static files)
  4. Registers all API routers (parts, orders, customers, auth, analytics)
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from backend.database import engine
# Import models so SQLAlchemy knows about the tables – even if not used directly here
from backend.models import Part, Order, Customer, User  # noqa: F401
from backend.database import Base
from backend.routers import auth, parts, orders, customers, analytics, activity
from backend.routers import loans as loans_router
from backend.seed import seed, ensure_admin
from backend.config import ALLOWED_ORIGINS, SEED_ON_STARTUP, IS_PRODUCTION
from backend.services.audit import record_activity

# Step 1: Database schema.
# In production the schema is managed by Alembic migrations – run
# `alembic upgrade head` before starting the app. Locally we create the
# tables directly for convenience.
if not IS_PRODUCTION:
    Base.metadata.create_all(bind=engine)

# Step 2: Insert sample data on first run (only runs if DB is empty).
# Disabled by default in production – set SEED_ON_STARTUP=true to enable.
if SEED_ON_STARTUP:
    seed()

# Bootstrap the first admin from ADMIN_USERNAME/ADMIN_PASSWORD (no-op if unset
# or an admin already exists). This is how production gets its first login.
ensure_admin()

# Step 3: Create the FastAPI application.
# Interactive API docs are disabled in production to avoid exposing the API surface.
app = FastAPI(
    title="Guleed Spareparts API",
    description="Inventory management system for Guleed Spareparts auto parts store",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
)

# Step 4: Add CORS middleware
# CORS = Cross-Origin Resource Sharing
# Without this, the browser would block the frontend from calling the backend
# (because they run on different ports: 3000 vs 8000)
# In production, replace "*" with your actual domain name
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # configurable via ALLOWED_ORIGINS env var
    allow_credentials=False,         # we authenticate with Bearer tokens, not cookies
    allow_methods=["*"],             # allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],             # allow all headers (including Authorization)
)


# Audit trail: record every successful data change (who + when + what)
@app.middleware("http")
async def audit_log_middleware(request, call_next):
    response = await call_next(request)
    try:
        path = request.url.path
        if (
            request.method in ("POST", "PUT", "DELETE", "PATCH")
            and path.startswith("/api/")
            and path != "/api/auth/login"          # don't log logins
            and response.status_code < 400          # only successful changes
        ):
            record_activity(
                request.headers.get("authorization", ""),
                request.method, path, response.status_code,
                detail=request.scope.get("audit_detail"),
            )
        # Tell the browser to always revalidate the app shell (HTML/CSS/JS),
        # so a new deploy is never hidden behind a stale cached copy. The files
        # still send ETags, so unchanged ones come back as a cheap 304.
        if path.startswith("/app") and path.rsplit(".", 1)[-1] in ("html", "css", "js", "json"):
            response.headers["Cache-Control"] = "no-cache"
    except Exception:
        pass
    return response

# Step 5: Serve uploaded images as static files
# When you upload a part image, it's saved in the 'uploads/' folder
# This makes those files accessible at: http://localhost:8000/uploads/filename.jpg
# UPLOAD_DIR / FRONTEND_DIR are overridable via env vars so the packaged
# desktop app can point them at a writable data folder and the bundled files.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR") or os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)  # create the folder if it doesn't exist
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Also serve the frontend HTML files (optional – you can also just open them directly)
FRONTEND_DIR = os.environ.get("FRONTEND_DIR") or os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# Step 6: Register all routers
# Each router handles a different section of the API
app.include_router(auth.router)          # /api/auth/...
app.include_router(parts.router)         # /api/parts/...
app.include_router(orders.router)        # /api/orders/...
app.include_router(customers.router)     # /api/customers/...
app.include_router(analytics.router)     # /api/analytics/...
app.include_router(loans_router.router)  # /api/loans/...
app.include_router(activity.router)      # /api/activity/...


# Visiting the bare domain sends people straight to the app's login page
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/login.html")


@app.get("/health", tags=["Health"])
def health():
    """Minimal check – returns OK if server is up."""
    return {"status": "ok"}
