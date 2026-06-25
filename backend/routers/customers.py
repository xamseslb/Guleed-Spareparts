"""
routers/customers.py – API endpoints for managing customers.

A "router" is a group of related API routes.
This file handles everything about customers: create, read, update, delete.

All routes here require the user to be logged in (current_user dependency).
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.customer import Customer
from backend.models.order import Order
from backend.models.loan import Loan
from backend.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from backend.services.auth_service import get_current_user
from backend.models.user import User

# Create a router with the prefix /api/customers
# All routes in this file will start with /api/customers/...
router = APIRouter(prefix="/api/customers", tags=["Customers"])


# GET /api/customers/ – returns a list of all customers
@router.get("/", response_model=List[CustomerOut])
def get_customers(
    skip: int = 0,          # pagination: how many to skip (for page 2, skip=10)
    limit: int = 100,       # pagination: how many to return at most
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # must be logged in
):
    # Query the database for all customers, with optional pagination
    return db.query(Customer).offset(skip).limit(limit).all()


# GET /api/customers/{id} – returns one specific customer by ID
@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Look for a customer with this ID
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        # If not found, return a 404 error
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


# POST /api/customers/ – creates a new customer
@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,   # the new customer's data comes from the request body
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Create a Customer object from the incoming data
    customer = Customer(**data.model_dump())
    db.add(customer)        # add it to the database session
    db.commit()             # save it to the actual database file
    db.refresh(customer)    # reload from DB to get the auto-generated ID
    return customer


# PUT /api/customers/{id} – updates an existing customer
@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,   # only the fields you want to change
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find the customer first
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Only update the fields that were actually sent (exclude_unset=True)
    # e.g. if you only sent {"phone": "12345"}, only phone is updated
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)

    db.commit()
    db.refresh(c)
    return c


# DELETE /api/customers/{id} – deletes a customer
@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find the customer
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Don't orphan order/loan history – block deletion if the customer is referenced
    order_count = db.query(Order).filter(Order.customer_id == customer_id).count()
    loan_count = db.query(Loan).filter(Loan.customer_id == customer_id).count()
    if order_count or loan_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete customer: {order_count} order(s) and {loan_count} loan(s) are linked to them.",
        )

    db.delete(c)    # mark for deletion
    db.commit()     # actually delete from the database
    # Returns 204 No Content (success with no response body)
