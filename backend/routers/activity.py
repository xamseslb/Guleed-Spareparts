"""
routers/activity.py – Admin-only view of the audit trail.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.activity import ActivityLog
from backend.models.user import User, UserRole
from backend.services.auth_service import get_current_user

router = APIRouter(prefix="/api/activity", tags=["Activity"])


@router.get("/")
def list_activity(
    limit: int = 300,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view the activity log")
    rows = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "username": r.username,
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "detail": r.detail,
        }
        for r in rows
    ]
