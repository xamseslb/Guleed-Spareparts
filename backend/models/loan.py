"""
models/loan.py – Database table for items currently on loan.

Tracks who borrowed what, how much it costs,
when it was borrowed, expected return date, and which employee handled it.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base


class Loan(Base):
    __tablename__ = "loans"

    id             = Column(Integer, primary_key=True, index=True)

    # Who borrowed it (references the customers table)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Which part was borrowed (references the parts table)
    part_id        = Column(Integer, ForeignKey("parts.id"), nullable=False)

    # How many items were borrowed
    quantity       = Column(Integer, default=1, nullable=False)

    # What it costs to borrow (per item or total – staff decides)
    loan_price     = Column(Float, nullable=False, default=0.0)

    # The employee who registered this loan (stored as their full name or username)
    employee_name  = Column(String(200), nullable=False)

    # When the item was handed out
    loan_date      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # When it should be returned (optional – can be open-ended)
    expected_return_date = Column(DateTime(timezone=True), nullable=True)

    # When it was actually returned (null = still on loan)
    returned_date  = Column(DateTime(timezone=True), nullable=True)

    # Status: 'active' | 'returned' | 'overdue'
    status         = Column(String(20), default="active", nullable=False)

    # Optional internal notes
    notes          = Column(Text, nullable=True)

    # Shared id when several parts are sold/loaned together (one "receipt")
    group_ref      = Column(String(40), nullable=True, index=True)

    # Timestamps
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships – lets us join to customer/part data easily
    customer       = relationship("Customer", backref="loans")
    part           = relationship("Part", backref="loans")

    @property
    def total_price(self) -> float:
        """Total loan cost = price × quantity."""
        return round(self.loan_price * self.quantity, 2)
