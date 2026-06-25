"""
models/part.py – The 'Part' database table (one spare part = one row).

SQLAlchemy reads this class and creates a table called 'parts' in the database.
Every Column() here becomes a column in that table.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from backend.database import Base


class Part(Base):
    """
    Represents one spare part in the inventory.
    Each instance of this class = one row in the 'parts' table.
    """

    # Tell SQLAlchemy what to call this table in the database
    __tablename__ = "parts"

    # --- Identity ---
    id = Column(Integer, primary_key=True, index=True)          # Auto-incrementing ID
    part_number = Column(String(50), unique=True, index=True, nullable=False)  # e.g. "BR-8690"
    name = Column(String(200), nullable=False)                  # Human-readable name
    description = Column(Text, nullable=True)                   # Optional longer description
    category = Column(String(100), nullable=False)              # e.g. "Brakes", "Oil"

    # --- Car compatibility ---
    # Stored as JSON list: [{"make": "Toyota", "model": "Corolla", "year_from": 2010, "year_to": 2022}]
    # This lets one part be compatible with many different cars
    compatible_cars = Column(JSON, default=list)

    # --- Stock numbers ---
    stock_quantity = Column(Integer, default=0, nullable=False)     # How many we have right now
    ordered_quantity = Column(Integer, default=0, nullable=False)   # How many are on order (coming in)
    loaned_quantity = Column(Integer, default=0, nullable=False)    # How many are currently on loan
    low_stock_threshold = Column(Integer, default=5, nullable=False)# When to show a low-stock warning

    # --- Price & location ---
    unit_price = Column(Float, nullable=False)          # Price per item in NOK
    location = Column(String(100), nullable=True)       # Physical shelf location, e.g. "Shelf B, Row 04"

    # --- Images ---
    # Stored as a JSON list of file paths, e.g. ["/uploads/part1_abc123.jpg"]
    # Maximum 10 images per part (enforced in the router)
    images = Column(JSON, default=list)

    # --- Timestamps (set automatically by the database) ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # --- Computed properties (calculated on-the-fly, not stored in DB) ---

    @property
    def available_quantity(self) -> int:
        """
        How many items can actually be sold right now.
        = stock_quantity minus items currently on loan
        """
        return max(0, self.stock_quantity - self.loaned_quantity)

    @property
    def stock_status(self) -> str:
        """
        Returns a label based on how much stock is left:
        - 'Empty'  → 0 items
        - 'Low'    → at or below the low-stock threshold
        - 'OK'     → enough stock
        """
        if self.stock_quantity == 0:
            return "Empty"
        elif self.stock_quantity <= self.low_stock_threshold:
            return "Low"
        return "OK"
