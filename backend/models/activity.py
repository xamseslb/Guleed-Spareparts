"""
models/activity.py – Audit trail of every data change.

One row per create/update/delete, recording who did it, when, and what.
Gives admins full accountability (e.g. "hamse deleted order #5 at 14:32").
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from backend.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    username = Column(String(100), nullable=True)   # who (None if not logged in)
    method = Column(String(10), nullable=False)      # POST / PUT / DELETE
    path = Column(String(300), nullable=False)       # e.g. /api/orders/5
    status_code = Column(Integer, nullable=False)    # result of the action
    detail = Column(String(300), nullable=True)      # human label, e.g. "part 81551-90k09 (Brake Pad)"
