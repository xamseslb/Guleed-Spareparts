"""
services/analytics.py – Data analysis using SciPy and Pandas.

This file calculates business insights from the database:
  - Which items are running low on stock?
  - What is the stock value per category?
  - Are orders increasing or decreasing over time? (linear regression)
  - What is the overall inventory summary?

SciPy  → used for statistics (linear regression on order trends)
Pandas → used for data manipulation (grouping parts by category, aggregating)
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models.part import Part
from backend.models.order import Order, OrderStatus
from backend.models.loan import Loan


def _price(v) -> float:
    """A blank imported price can be NaN; treat it as 0 so sums stay valid."""
    try:
        v = float(v)
        return 0.0 if v != v else v   # v != v is True only for NaN
    except (ValueError, TypeError):
        return 0.0


def get_low_stock_parts(db: Session) -> List[Dict[str, Any]]:
    """
    Returns all parts where stock is at or below the low-stock threshold.
    Sorted by criticality – the most urgent (lowest ratio) comes first.

    'criticality_ratio' = stock / threshold
       e.g. 2 items left with threshold 10 → ratio = 0.2 (very critical)
            5 items left with threshold 5  → ratio = 1.0 (just at limit)
    """
    parts = db.query(Part).all()
    low_stock = []

    for p in parts:
        if p.stock_quantity <= p.low_stock_threshold:
            # How full is this item compared to its threshold? (0 = empty, 1 = just at limit)
            ratio = p.stock_quantity / max(p.low_stock_threshold, 1)
            low_stock.append({
                "id": p.id,
                "part_number": p.part_number,
                "name": p.name,
                "stock_quantity": p.stock_quantity,
                "low_stock_threshold": p.low_stock_threshold,
                "status": p.stock_status,
                "criticality_ratio": round(ratio, 2),
            })

    # Sort: most critical (lowest ratio) first
    low_stock.sort(key=lambda x: x["criticality_ratio"])
    return low_stock


def get_category_stats(db: Session) -> List[Dict[str, Any]]:
    """
    Uses Pandas to group all parts by category and calculate statistics.

    For each category we calculate:
      - How many different parts are in it
      - Total value of all stock in that category (price × quantity)
      - Average price of parts in that category
      - How many parts in that category have low stock
    """
    parts = db.query(Part).all()
    if not parts:
        return []

    # Convert the list of Part objects to a Pandas DataFrame (like an Excel table)
    df = pd.DataFrame([{
        "category": p.category,
        "unit_price": _price(p.unit_price),
        "stock_quantity": p.stock_quantity,
        "low_stock": p.stock_quantity <= p.low_stock_threshold,  # True/False
        "total_value": _price(p.unit_price) * p.stock_quantity,
    } for p in parts])

    # Group by category and calculate summary stats for each group
    grouped = df.groupby("category").agg(
        total_parts=("unit_price", "count"),
        total_stock_value=("total_value", "sum"),
        average_price=("unit_price", "mean"),
        low_stock_count=("low_stock", "sum"),   # True counts as 1, False as 0
    ).reset_index()

    # Round decimals for cleaner output
    grouped["average_price"] = grouped["average_price"].round(2)
    grouped["total_stock_value"] = grouped["total_stock_value"].round(2)

    return grouped.to_dict(orient="records")


def get_order_trend(db: Session, days: int = 30) -> Dict[str, Any]:
    """
    Uses SciPy linear regression to detect if orders are going up or down.

    Linear regression draws a "best fit line" through the daily order data.
    - Positive slope  → orders are INCREASING
    - Negative slope  → orders are DECREASING
    - Near-zero slope → orders are STABLE

    r_squared: how well the line fits the data (0 = no fit, 1 = perfect fit)
    p_value:   how statistically confident we are (< 0.05 = significant trend)
    """
    # Count units actually SOLD each day: delivered orders (by order date) plus
    # paid credit sales (by payment date). This mirrors the Sales screen, so
    # credit sales show up here too – not just plain orders.
    rows = []
    for o in db.query(Order).filter(Order.status == OrderStatus.LEVERT).all():
        d = _naive(o.order_date)
        if d:
            rows.append((d, o.quantity or 0))
    for l in db.query(Loan).filter(Loan.status == "paid").all():
        d = _naive(l.returned_date) or _naive(l.loan_date)
        if d:
            rows.append((d, l.quantity or 0))

    if not rows:
        return {"trend": "no data", "daily_counts": []}

    df = pd.DataFrame(rows, columns=["date", "quantity"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    daily = df.groupby("date")["quantity"].sum().reset_index().sort_values("date")
    counts = [{"date": str(r["date"].date()), "quantity": int(r["quantity"])} for _, r in daily.iterrows()]

    # A trend line needs at least two different days.
    if len(daily) < 2:
        return {"trend": "not enough data", "daily_counts": counts}

    x = np.arange(len(daily))
    y = daily["quantity"].values.astype(float)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    trend_label = "Increasing" if slope > 0.1 else "Decreasing" if slope < -0.1 else "Stable"

    return {
        "trend": trend_label,
        "slope": round(slope, 4),
        "r_squared": round(r_value ** 2, 4),
        "p_value": round(p_value, 4),
        "daily_counts": counts,
    }


def get_inventory_summary(db: Session) -> Dict[str, Any]:
    """
    Returns a quick overview of the entire inventory.
    Used for the summary cards at the top of the dashboard.
    """
    parts = db.query(Part).all()
    if not parts:
        return {}

    # Total value of everything in stock (price × quantity for each part, then sum)
    total_value = sum(_price(p.unit_price) * p.stock_quantity for p in parts)

    return {
        "total_parts": len(parts),
        "total_stock_value_nok": round(total_value, 2),         # total stock value in NOK
        "low_stock": sum(1 for p in parts if p.stock_quantity <= p.low_stock_threshold),
        "out_of_stock": sum(1 for p in parts if p.stock_quantity == 0),
        "total_on_loan": sum(p.loaned_quantity for p in parts),
    }


def _naive(dt):
    """Drop timezone info so SQLite (naive) and Postgres (aware) compare alike."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt


def get_sales_summary(db: Session, period: str = "month") -> Dict[str, Any]:
    """Units sold and revenue from delivered orders + paid credit sales.

    period: 'today' | 'week' | 'month' | 'all'. A sale counts on the day the
    order was delivered, or the day a credit sale was paid.
    """
    now = datetime.utcnow()
    cutoff = None
    if period == "today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        cutoff = now - timedelta(days=7)
    elif period == "month":
        cutoff = now - timedelta(days=30)

    rows = []  # one entry per sold line
    for o in db.query(Order).filter(Order.status == OrderStatus.LEVERT).all():
        d = _naive(o.order_date)
        if cutoff and (d is None or d < cutoff):
            continue
        rows.append({
            "part_id": o.part_id,
            "name": o.part.name if o.part else f"#{o.part_id}",
            "part_number": o.part.part_number if o.part else "",
            "units": o.quantity or 0,
            "revenue": _price(o.unit_price_at_order) * (o.quantity or 0),
            "kind": "order",
        })
    for l in db.query(Loan).filter(Loan.status == "paid").all():
        d = _naive(l.returned_date) or _naive(l.loan_date)
        if cutoff and (d is None or d < cutoff):
            continue
        rows.append({
            "part_id": l.part_id,
            "name": l.part.name if l.part else f"#{l.part_id}",
            "part_number": l.part.part_number if l.part else "",
            "units": l.quantity or 0,
            "revenue": _price(l.loan_price) * (l.quantity or 0),
            "kind": "credit",
        })

    by_part = {}
    for r in rows:
        b = by_part.setdefault(r["part_id"], {
            "name": r["name"], "part_number": r["part_number"], "units": 0, "revenue": 0.0,
        })
        b["units"] += r["units"]
        b["revenue"] += r["revenue"]
    top_parts = sorted(by_part.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    for b in top_parts:
        b["revenue"] = round(b["revenue"], 2)

    return {
        "period": period,
        "total_units": sum(r["units"] for r in rows),
        "total_revenue": round(sum(r["revenue"] for r in rows), 2),
        "transactions": len(rows),
        "top_parts": top_parts,
    }
