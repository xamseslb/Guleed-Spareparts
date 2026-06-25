from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from backend.models.order import OrderStatus


class OrderCreate(BaseModel):
    customer_id: int
    part_id: int
    quantity: int = Field(1, ge=1)
    unit_price_at_order: float = Field(..., gt=0)
    notes: Optional[str] = None


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
    status: OrderStatus
    notes: Optional[str]
    order_date: datetime
    updated_at: Optional[datetime]
    customer_name: Optional[str] = None
    part_name: Optional[str] = None
    part_number: Optional[str] = None
