"""
services/auth_service.py – Everything related to login and security.

This file handles:
1. Hashing passwords (so we never store plain text passwords)
2. Creating JWT tokens (a "key" the user gets after logging in)
3. Checking if a token is valid on each request

NOTE: We use the 'bcrypt' library directly (instead of passlib)
because passlib is not yet compatible with bcrypt 5.0 on Python 3.14.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User
from backend.config import SECRET_KEY

# --- Config ---
# SECRET_KEY (from backend.config) is used to sign JWT tokens.
ALGORITHM = "HS256"               # The algorithm used to sign the token
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # Token expires after 8 hours

# oauth2_scheme tells FastAPI: "look for a Bearer token in the Authorization header"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain-text password matches the stored hashed version.
    bcrypt.checkpw() does the comparison securely.
    Returns True if they match, False if not.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def hash_password(password: str) -> str:
    """
    Turns a plain-text password into a secure bcrypt hash.
    We always store the hash, never the real password.
    bcrypt.gensalt() creates a random 'salt' so two equal passwords
    produce different hashes – making rainbow-table attacks impossible.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT token containing user info (like username and role).
    The token has an expiry time – after that, the user must log in again.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire   # Add expiry time into the token payload
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),  # FastAPI extracts the token from the header
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency – used on every protected route.
    1. Reads the JWT token from the request header
    2. Decodes and validates it
    3. Looks up the user in the database
    4. Returns the user object (so routes know who is making the request)

    If anything is wrong (bad token, expired, user deleted), it returns 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the token and extract the username ("sub" = subject)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        # Token is malformed or signature is wrong
        raise credentials_exception

    # Find the user in the database using the username from the token
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Extra protection layer – only allows Admin users through.
    Add this as a dependency on any route only admins should access.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
