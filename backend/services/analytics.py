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
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models.part import Part
from backend.models.order import Order


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
        "unit_price": p.unit_price,
        "stock_quantity": p.stock_quantity,
        "low_stock": p.stock_quantity <= p.low_stock_threshold,  # True/False
        "total_value": p.unit_price * p.stock_quantity,
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
    orders = db.query(Order).all()
    if not orders:
        return {"trend": "no data", "daily_counts": []}

    # Convert orders to a Pandas DataFrame
    df = pd.DataFrame([{
        "order_date": o.order_date,
        "quantity": o.quantity,
    } for o in orders])

    # Normalize to day-level (remove time info) and sum quantities per day
    df["order_date"] = pd.to_datetime(df["order_date"]).dt.normalize()
    daily = df.groupby("order_date")["quantity"].sum().reset_index()
    daily = daily.sort_values("order_date")

    if len(daily) < 2:
        return {"trend": "not enough data", "daily_counts": daily.to_dict(orient="records")}

    # x = day numbers (0, 1, 2, 3...), y = quantities sold on those days
    x = np.arange(len(daily))
    y = daily["quantity"].values.astype(float)

    # Run linear regression (SciPy) to find the trend line
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # Interpret the slope
    if slope > 0.1:
        trend_label = "Increasing"
    elif slope < -0.1:
        trend_label = "Decreasing"
    else:
        trend_label = "Stable"

    return {
        "trend": trend_label,
        "slope": round(slope, 4),               # how steep the trend line is
        "r_squared": round(r_value ** 2, 4),    # how reliable this trend is (0-1)
        "p_value": round(p_value, 4),           # statistical significance
        "daily_counts": [
            {"date": str(row["order_date"].date()), "quantity": int(row["quantity"])}
            for _, row in daily.iterrows()
        ],
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
    total_value = sum(p.unit_price * p.stock_quantity for p in parts)

    return {
        "total_parts": len(parts),
        "total_stock_value_nok": round(total_value, 2),         # total stock value in NOK
        "low_stock": sum(1 for p in parts if p.stock_quantity <= p.low_stock_threshold),
        "out_of_stock": sum(1 for p in parts if p.stock_quantity == 0),
        "total_on_loan": sum(p.loaned_quantity for p in parts),
    }
