"""
routers/auth.py – API endpoints for login and user management.

This file handles:
  - POST /api/auth/login    → user submits username + password, gets a JWT token back
  - POST /api/auth/register → admin creates a new employee account
  - GET  /api/auth/me       → logged-in user can see their own profile info
"""

import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.schemas.customer import UserCreate, UserAdminUpdate, Token
from backend.services.auth_service import (
    verify_password, hash_password, create_access_token, get_current_user
)

# All routes in this file start with /api/auth/...
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ─── Simple in-memory brute-force throttle for login ──────────────────
# Blocks a username after too many failed attempts within a time window.
# Note: per-process only; behind multiple workers, enforce at the proxy too.
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes
_failed_logins: dict[str, list[float]] = defaultdict(list)


def _check_login_rate_limit(username: str) -> None:
    now = time.time()
    recent = [t for t in _failed_logins[username] if now - t < _LOGIN_WINDOW_SECONDS]
    _failed_logins[username] = recent
    if len(recent) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )


# GET /api/auth/users – list users.
# Default: active users only (used for the employee dropdown in the loan form).
# Admins can pass ?include_inactive=true to also see disabled accounts (Users page).
@router.get("/users")
def list_users(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active == True)
    users = query.order_by(User.username).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "last_login": u.last_login,
        }
        for u in users
    ]


# POST /api/auth/login
# The frontend sends a form with username + password
# If correct, we return a JWT token the frontend stores and uses on all future requests
@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # reads username/password from the form
    db: Session = Depends(get_db),
):
    # Step 0: Throttle repeated failed attempts for this username
    _check_login_rate_limit(form_data.username)

    # Step 1: Find the user in the database by username
    user = db.query(User).filter(User.username == form_data.username).first()

    # Step 2: Check if the user exists AND the password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        _failed_logins[form_data.username].append(time.time())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Check the account is still active (not disabled by admin)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been disabled")

    # Step 4: Successful login – clear failed-attempt history and record the time
    _failed_logins.pop(form_data.username, None)
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Step 5: Create a JWT token and return it
    # The token contains the username and role so we don't need to look them up every request
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, token_type="bearer", role=user.role, full_name=user.full_name)


# POST /api/auth/register
# Only admins can create new user accounts
# The new user gets a hashed password stored – never the plain text!
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # must be logged in
):
    # Check that the logged-in user is an admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create new users")

    # Check that the username isn't already taken
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create the new user with a hashed (secure) password
    user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),  # hash it before saving!
        role=data.role,
    )
    db.add(user)
    db.commit()
    return {"message": f"User '{data.username}' created successfully", "role": data.role}


# PUT /api/auth/users/{id} – admin edits a user (rename, change role, enable/disable)
@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can manage users")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fields = data.model_dump(exclude_unset=True)
    new_password = fields.pop("password", None)

    if "role" in fields and fields["role"] is not None:
        valid = {r.value for r in UserRole}
        if fields["role"] not in valid:
            raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {', '.join(sorted(valid))}")

    # Don't let an admin lock themselves out
    if user.id == current_user.id:
        if fields.get("is_active") is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
        if "role" in fields and fields["role"] not in (None, "admin"):
            raise HTTPException(status_code=400, detail="You cannot change your own admin role")

    for field, value in fields.items():
        setattr(user, field, value)

    if new_password is not None:
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.hashed_password = hash_password(new_password)

    db.commit()
    return {"message": f"User '{user.username}' updated"}


# GET /api/auth/me
# Returns the currently logged-in user's profile
# Useful for the frontend to know who is logged in and what role they have
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "email": current_user.email,
    }
