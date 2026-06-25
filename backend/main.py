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
from backend.database import engine
# Import models so SQLAlchemy knows about the tables – even if not used directly here
from backend.models import Part, Order, Customer, User  # noqa: F401
from backend.database import Base
from backend.routers import auth, parts, orders, customers, analytics
from backend.routers import loans as loans_router
from backend.seed import seed
from backend.config import ALLOWED_ORIGINS, SEED_ON_STARTUP, IS_PRODUCTION

# Step 1: Create all database tables from our model definitions
# If the tables already exist, this does nothing (safe to call every startup)
Base.metadata.create_all(bind=engine)

# Step 2: Insert sample data on first run (only runs if DB is empty).
# Disabled by default in production – set SEED_ON_STARTUP=true to enable.
if SEED_ON_STARTUP:
    seed()

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

# Step 5: Serve uploaded images as static files
# When you upload a part image, it's saved in the 'uploads/' folder
# This makes those files accessible at: http://localhost:8000/uploads/filename.jpg
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)  # create the folder if it doesn't exist
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Also serve the frontend HTML files (optional – you can also just open them directly)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
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


# A simple health check route – useful to confirm the server is running
@app.get("/", tags=["Health"])
def root():
    return {
        "system": "Guleed Spareparts",
        "status": "online",
        "docs": "/docs",        # visit this for the interactive API explorer
        "frontend": "/app",
    }


@app.get("/health", tags=["Health"])
def health():
    """Minimal check – returns OK if server is up."""
    return {"status": "ok"}
