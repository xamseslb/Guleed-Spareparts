from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from backend.models.order import OrderStatus


class OrderCreate(BaseModel):
    customer_id: int
    part_id: int
    quantity: int = Field(1, ge=1)
    # Optional: if omitted, the backend snapshots the part's current unit price.
    unit_price_at_order: Optional[float] = Field(None, gt=0)
    status: OrderStatus = OrderStatus.NY
    notes: Optional[str] = None
    group_ref: Optional[str] = None   # shared id when several parts are bought together


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    quantity: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    part_id: int
    quantity: int
    unit_price_at_order: float
    unit_price: float          # alias of unit_price_at_order (what the frontend reads)
    total_price: float         # computed: unit_price_at_order × quantity
    status: OrderStatus
    notes: Optional[str]
    group_ref: Optional[str] = None
    order_date: datetime
    updated_at: Optional[datetime]
    customer_name: Optional[str] = None
    part_name: Optional[str] = None
    part_number: Optional[str] = None
