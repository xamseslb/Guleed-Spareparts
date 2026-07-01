"""
schemas/loan.py – Pydantic validation schemas for loans.

LoanCreate  → sent when registering a new loan
LoanUpdate  → sent when updating (e.g. marking as returned)
LoanOut     → returned by the API (includes joined customer/part names)
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class LoanCreate(BaseModel):
    customer_id: int = Field(..., gt=0, description="ID of the customer borrowing the item")
    part_id: int = Field(..., gt=0, description="ID of the part being borrowed")
    quantity: int = Field(1, ge=1, description="Number of items borrowed")
    loan_price: float = Field(0.0, ge=0, description="Price per item for the loan")
    employee_name: str = Field(..., min_length=1, max_length=200, description="Name of the employee handling this loan")
    loan_date: Optional[datetime] = None              # defaults to now if not provided
    expected_return_date: Optional[datetime] = None   # when it should come back
    notes: Optional[str] = None
    group_ref: Optional[str] = None                   # shared id for multi-item sales


class LoanUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)
    loan_price: Optional[float] = Field(None, ge=0)
    employee_name: Optional[str] = None
    expected_return_date: Optional[datetime] = None
    returned_date: Optional[datetime] = None          # set this to mark as returned
    status: Optional[str] = None                      # 'active' | 'returned' | 'overdue'
    notes: Optional[str] = None
    group_ref: Optional[str] = None                   # link a single loan into a shared receipt


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    part_id: int
    quantity: int
    loan_price: float
    total_price: float         # computed: loan_price × quantity
    employee_name: str
    loan_date: datetime
    expected_return_date: Optional[datetime]
    returned_date: Optional[datetime]
    status: str
    notes: Optional[str]
    group_ref: Optional[str] = None
    created_at: datetime

    # Joined fields populated by the router (names instead of just IDs)
    customer_name: Optional[str] = None
    part_name: Optional[str] = None
    part_number: Optional[str] = None
