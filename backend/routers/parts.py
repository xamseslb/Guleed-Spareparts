"""
Router for reservedeler (Parts) – inkluderer CRUD, søk og bildeopplasting.
"""

import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from PIL import Image as PilImage
from backend.database import get_db
from backend.models.part import Part
from backend.models.order import Order
from backend.models.loan import Loan
from backend.schemas.part import PartCreate, PartUpdate, PartOut
from backend.services.auth_service import get_current_user
from backend.models.user import User, UserRole

router = APIRouter(prefix="/api/parts", tags=["Parts"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
MAX_IMAGES = 10
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 5


# ─── Hent alle varer (med søk og filter) ──────────────────────────────
@router.get("/", response_model=List[PartOut])
def get_parts(
    q: Optional[str] = Query(None, description="Search by name or part number"),
    category: Optional[str] = Query(None),
    car_make: Optional[str] = Query(None),
    car_model: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Part)

    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            Part.name.ilike(search_term) | Part.part_number.ilike(search_term)
        )
    if category:
        query = query.filter(Part.category.ilike(f"%{category}%"))
    if low_stock_only:
        query = query.filter(Part.stock_quantity <= Part.low_stock_threshold)

    parts = query.offset(skip).limit(limit).all()

    # Biltype-filter (JSON-felt kan ikke filtreres i SQL på tvers av backends)
    if car_make or car_model:
        filtered = []
        for p in parts:
            for car in (p.compatible_cars or []):
                make_match = not car_make or car_make.lower() in car.get("make", "").lower()
                model_match = not car_model or car_model.lower() in car.get("model", "").lower()
                if make_match and model_match:
                    filtered.append(p)
                    break
        parts = filtered

    return parts


# ─── Hent én vare ─────────────────────────────────────────────────────
@router.get("/{part_id}", response_model=PartOut)
def get_part(part_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part


# ─── Legg til vare ────────────────────────────────────────────────────
@router.post("/", response_model=PartOut, status_code=status.HTTP_201_CREATED)
def create_part(data: PartCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Part).filter(Part.part_number == data.part_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Part number '{data.part_number}' already exists")

    part = Part(**data.model_dump())
    part.compatible_cars = [c.model_dump() for c in data.compatible_cars]
    part.images = []
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


# ─── Oppdater vare ────────────────────────────────────────────────────
@router.put("/{part_id}", response_model=PartOut)
def update_part(
    part_id: int,
    data: PartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    update_data = data.model_dump(exclude_unset=True)
    if "compatible_cars" in update_data and update_data["compatible_cars"] is not None:
        update_data["compatible_cars"] = [c.model_dump() if hasattr(c, "model_dump") else c for c in update_data["compatible_cars"]]

    for field, value in update_data.items():
        setattr(part, field, value)

    db.commit()
    db.refresh(part)
    return part


# ─── Slett vare ───────────────────────────────────────────────────────
@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(part_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete parts")
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    # Don't orphan order/loan history – block deletion if the part is referenced
    order_count = db.query(Order).filter(Order.part_id == part_id).count()
    loan_count = db.query(Loan).filter(Loan.part_id == part_id).count()
    if order_count or loan_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete part: {order_count} order(s) and {loan_count} loan(s) reference it.",
        )

    # Slett alle tilhørende bilder
    for img_path in (part.images or []):
        full_path = os.path.join(UPLOAD_DIR, os.path.basename(img_path))
        if os.path.exists(full_path):
            os.remove(full_path)
    db.delete(part)
    db.commit()


# ─── Last opp bilde ───────────────────────────────────────────────────
@router.post("/{part_id}/images", response_model=PartOut)
async def upload_image(
    part_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    current_images = part.images or []
    if len(current_images) >= MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_IMAGES} images per part")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG and WebP are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_FILE_SIZE_MB} MB)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{part_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Lagre og resize med Pillow (maks 1200px bredde, behold ratio)
    import io
    img = PilImage.open(io.BytesIO(content))
    img = img.convert("RGB")
    if img.width > 1200:
        ratio = 1200 / img.width
        img = img.resize((1200, int(img.height * ratio)), PilImage.LANCZOS)
    img.save(filepath, optimize=True, quality=85)

    part.images = current_images + [f"/uploads/{filename}"]
    db.commit()
    db.refresh(part)
    return part


# ─── Slett ett bilde ──────────────────────────────────────────────────
@router.delete("/{part_id}/images/{image_index}", response_model=PartOut)
def delete_image(
    part_id: int,
    image_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    images = part.images or []
    if image_index < 0 or image_index >= len(images):
        raise HTTPException(status_code=404, detail="Image not found")

    img_to_delete = images[image_index]
    full_path = os.path.join(UPLOAD_DIR, os.path.basename(img_to_delete))
    if os.path.exists(full_path):
        os.remove(full_path)

    part.images = [img for i, img in enumerate(images) if i != image_index]
    db.commit()
    db.refresh(part)
    return part
