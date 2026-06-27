"""
routers/loans.py – API endpoints for loan management.

Endpoints:
  GET    /api/loans/           → list all loans (with optional filters)
  GET    /api/loans/{id}       → get one loan
  POST   /api/loans/           → register a new loan
  PUT    /api/loans/{id}       → update a loan
  POST   /api/loans/{id}/return → mark a loan as returned
  DELETE /api/loans/{id}       → delete a loan record

When a loan is created:  part.loaned_quantity increases by quantity
When a loan is returned: part.loaned_quantity decreases by quantity
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.loan import Loan
from backend.models.part import Part
from backend.models.customer import Customer
from backend.schemas.loan import LoanCreate, LoanUpdate, LoanOut
from backend.services.auth_service import get_current_user
from backend.models.user import User, UserRole

router = APIRouter(prefix="/api/loans", tags=["Loans"])


def enrich(loan: Loan) -> LoanOut:
    """
    Converts a Loan DB object into a LoanOut schema,
    adding human-readable customer name, part name, and part number.
    """
    out = LoanOut.model_validate(loan)
    out.total_price = loan.total_price
    if loan.customer:
        out.customer_name = loan.customer.name
    if loan.part:
        out.part_name = loan.part.name
        out.part_number = loan.part.part_number
    return out


# GET /api/loans/ – list all loans with optional filters
@router.get("/", response_model=List[LoanOut])
def get_loans(
    status: Optional[str] = Query(None, description="Filter by status: active, returned, overdue"),
    customer_id: Optional[int] = Query(None),
    part_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Auto-mark loans as overdue if expected return date has passed
    now = datetime.now(timezone.utc)
    overdue = db.query(Loan).filter(
        Loan.status == "unpaid",
        Loan.expected_return_date != None,
        Loan.expected_return_date < now
    ).all()
    for loan in overdue:
        loan.status = "overdue"
    if overdue:
        db.commit()

    # Build query with optional filters
    q = db.query(Loan)
    if status:
        q = q.filter(Loan.status == status)
    if customer_id:
        q = q.filter(Loan.customer_id == customer_id)
    if part_id:
        q = q.filter(Loan.part_id == part_id)

    loans = q.order_by(Loan.loan_date.desc()).all()
    return [enrich(l) for l in loans]


# GET /api/loans/{id} – get one specific loan
@router.get("/{loan_id}", response_model=LoanOut)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return enrich(loan)


# POST /api/loans/ – register a new loan
@router.post("/", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def create_loan(
    data: LoanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check that the customer exists
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check that the part exists and has enough stock
    part = db.query(Part).filter(Part.id == data.part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    available = part.stock_quantity - part.loaned_quantity
    if data.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock. Available: {available}, requested: {data.quantity}"
        )

    # Create the loan record
    loan = Loan(
        customer_id=data.customer_id,
        part_id=data.part_id,
        quantity=data.quantity,
        loan_price=data.loan_price,
        employee_name=data.employee_name,
        loan_date=data.loan_date or datetime.now(timezone.utc),
        expected_return_date=data.expected_return_date,  # used as the expected payment date
        notes=data.notes,
        group_ref=data.group_ref,
        status="unpaid",
    )
    db.add(loan)

    # Increase loaned_quantity on the part so stock overview stays correct
    part.loaned_quantity += data.quantity

    db.commit()
    db.refresh(loan)
    return enrich(loan)


# PUT /api/loans/{id} – update loan details
@router.put("/{loan_id}", response_model=LoanOut)
def update_loan(
    loan_id: int,
    data: LoanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(loan, field, value)

    db.commit()
    db.refresh(loan)
    return enrich(loan)


# POST /api/loans/{id}/return – mark a loan as returned
@router.post("/{loan_id}/return", response_model=LoanOut)
def return_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status == "paid":
        raise HTTPException(status_code=400, detail="This credit sale is already marked as paid")

    # Mark as paid. The part is sold – clear the outstanding amount AND remove it
    # from stock. It is NOT returned to inventory.
    loan.status = "paid"
    loan.returned_date = datetime.now(timezone.utc)  # used as the payment date

    part = db.query(Part).filter(Part.id == loan.part_id).first()
    if part:
        part.loaned_quantity = max(0, part.loaned_quantity - loan.quantity)
        part.stock_quantity = max(0, part.stock_quantity - loan.quantity)

    db.commit()
    db.refresh(loan)
    return enrich(loan)


# DELETE /api/loans/{id} – delete a loan record (admin only)
@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # Only admins may delete
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete records")

    # If still unpaid (not yet a finalized sale), release the reserved quantity back
    if loan.status in ("unpaid", "overdue"):
        part = db.query(Part).filter(Part.id == loan.part_id).first()
        if part:
            part.loaned_quantity = max(0, part.loaned_quantity - loan.quantity)

    db.delete(loan)
    db.commit()
