from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


class OrderStatus(str, enum.Enum):
    NY = "New"
    BEHANDLES = "Processing"
    LEVERT = "Delivered"
    AVBRUTT = "Cancelled"


class Order(Base):
    """Ordre-modell – én kundebestilling."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_at_order = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.NY, nullable=False)
    notes = Column(String(500), nullable=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    customer = relationship("Customer", back_populates="orders")
    part = relationship("Part")

    @property
    def unit_price(self) -> float:
        """Alias for the price snapshotted at order time (what the frontend reads)."""
        return self.unit_price_at_order

    @property
    def total_price(self) -> float:
        """Line total = unit price at order × quantity."""
        return (self.unit_price_at_order or 0) * (self.quantity or 0)
