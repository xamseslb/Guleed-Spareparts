from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.order import Order, OrderStatus
from backend.models.part import Part
from backend.schemas.order import OrderCreate, OrderUpdate, OrderOut
from backend.services.auth_service import get_current_user
from backend.models.user import User, UserRole

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def enrich(order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    if order.customer:
        out.customer_name = order.customer.name
    if order.part:
        out.part_name = order.part.name
        out.part_number = order.part.part_number
    return out


@router.get("/", response_model=List[OrderOut])
def get_orders(
    customer_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Order)
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    orders = query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()
    return [enrich(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return enrich(order)


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = db.query(Part).filter(Part.id == data.part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    order_data = data.model_dump()
    # Snapshot the part's current price if none was provided by the client
    if order_data.get("unit_price_at_order") is None:
        order_data["unit_price_at_order"] = part.unit_price

    order = Order(**order_data)

    # A delivered order consumes stock immediately
    if order.status == OrderStatus.LEVERT:
        available = part.stock_quantity - part.loaned_quantity
        if order.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock. Available: {available}, requested: {order.quantity}",
            )
        part.stock_quantity -= order.quantity

    db.add(order)
    db.commit()
    db.refresh(order)
    return enrich(order)


@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    part = db.query(Part).filter(Part.id == order.part_id).first()
    was_delivered = order.status == OrderStatus.LEVERT
    old_quantity = order.quantity

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    now_delivered = order.status == OrderStatus.LEVERT

    # Keep stock_quantity in sync as the order moves in/out of "Delivered"
    if part:
        if not was_delivered and now_delivered:
            available = part.stock_quantity - part.loaned_quantity
            if order.quantity > available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock. Available: {available}, requested: {order.quantity}",
                )
            part.stock_quantity -= order.quantity
        elif was_delivered and not now_delivered:
            part.stock_quantity += old_quantity
        elif was_delivered and now_delivered and order.quantity != old_quantity:
            diff = order.quantity - old_quantity  # >0 means delivering more
            if diff > 0:
                available = part.stock_quantity - part.loaned_quantity
                if diff > available:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Not enough stock. Available: {available}, requested additional: {diff}",
                    )
            part.stock_quantity -= diff

    db.commit()
    db.refresh(order)
    return enrich(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete orders")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    part = db.query(Part).filter(Part.id == order.part_id).first()
    request.scope["audit_detail"] = f"order #{order.id} ({part.part_number if part else 'part #' + str(order.part_id)} ×{order.quantity})"
    # Return stock to inventory if this order had consumed it
    if order.status == OrderStatus.LEVERT:
        part = db.query(Part).filter(Part.id == order.part_id).first()
        if part:
            part.stock_quantity += order.quantity
    db.delete(order)
    db.commit()
