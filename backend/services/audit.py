"""
services/audit.py – Records data-changing requests into the activity log.

Used by a middleware so every successful create/update/delete is logged with
the acting user, with no per-endpoint code.
"""

from jose import jwt, JWTError
from backend.database import SessionLocal
from backend.models.activity import ActivityLog
from backend.config import SECRET_KEY

ALGORITHM = "HS256"


def _username_from_auth(auth_header: str):
    """Pull the username out of the Bearer token (None if missing/invalid)."""
    if auth_header and auth_header.startswith("Bearer "):
        try:
            payload = jwt.decode(auth_header[7:], SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub")
        except JWTError:
            return None
    return None


def record_activity(auth_header: str, method: str, path: str, status_code: int):
    db = SessionLocal()
    try:
        db.add(ActivityLog(
            username=_username_from_auth(auth_header),
            method=method,
            path=path,
            status_code=status_code,
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
