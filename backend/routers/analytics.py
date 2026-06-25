from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services import analytics
from backend.services.auth_service import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Quick overview of the entire inventory."""
    return analytics.get_inventory_summary(db)


@router.get("/low-stock")
def get_low_stock(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """All parts with low or empty stock, sorted by criticality."""
    return analytics.get_low_stock_parts(db)


@router.get("/categories")
def get_category_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Statistics per category (number of parts, stock value, average price)."""
    return analytics.get_category_stats(db)


@router.get("/order-trend")
def get_order_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sales trend calculated with SciPy linear regression."""
    return analytics.get_order_trend(db, days=days)
