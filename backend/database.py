"""
database.py – Sets up the connection to the database.

This file is run once when the app starts.
All other files import 'get_db' from here to talk to the database.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# The database file location.
# Locally we use SQLite (a simple file-based database, no server needed).
# In production, swap this for a real PostgreSQL database URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./guleed_spareparts.db")
# Some hosts (Render, Heroku, …) hand out a legacy "postgres://" scheme,
# but SQLAlchemy 2.x requires "postgresql://". Normalize it.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create the database engine (the "driver" that talks to the DB file)
engine = create_engine(
    DATABASE_URL,
    # SQLite needs this setting to work with FastAPI's async threads
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# SessionLocal creates a new database "session" (connection) per request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class all our database models (tables) inherit from
Base = declarative_base()


def get_db():
    """
    FastAPI dependency – gives each API request its own database session.
    The session is automatically closed when the request is done (finally block).
    """
    db = SessionLocal()
    try:
        yield db       # hand the session to the route function
    finally:
        db.close()     # always close, even if something goes wrong
