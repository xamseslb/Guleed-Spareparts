from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services import analytics
from backend.services.auth_service import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/api/analytics", tags=["Analytikk"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Rask oversikt over hele lageret."""
    return analytics.get_inventory_summary(db)


@router.get("/low-stock")
def get_low_stock(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Alle varer med lavt eller tomt lager, sortert etter kritikalitet."""
    return analytics.get_low_stock_parts(db)


@router.get("/categories")
def get_category_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Statistikk per kategori (antall varer, lagerverdi, gjennomsnittspris)."""
    return analytics.get_category_stats(db)


@router.get("/order-trend")
def get_order_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Salgstrend beregnet med SciPy lineær regresjon."""
    return analytics.get_order_trend(db, days=days)
