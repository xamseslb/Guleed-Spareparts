"""
schemas/part.py – Data validation for spare parts using Pydantic.

A "schema" defines what data is ALLOWED in and out of the API.
Pydantic checks the data automatically – if something is wrong, it returns a clear error.

We have 3 schemas:
  - PartCreate  → what you send when ADDING a new part
  - PartUpdate  → what you send when EDITING a part (all fields optional)
  - PartOut     → what the API sends BACK to you (what you see in the response)
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
import math


# --- Car Compatibility Model ---
# Used inside PartCreate and PartOut to describe which cars a part fits
class CarCompatibility(BaseModel):
    make: str = Field(..., example="Toyota")        # Car brand, required
    model: str = Field(..., example="Corolla")       # Car model, required
    year_from: Optional[int] = Field(None, example=2010)  # Starting year (optional)
    year_to: Optional[int] = Field(None, example=2022)    # Ending year (optional)


# --- Schema for CREATING a new part (POST /api/parts/) ---
# All required fields must be provided, optional ones have defaults
class PartCreate(BaseModel):
    part_number: str = Field(..., min_length=1, max_length=50, example="BR-8690")
    # Only the part number is required. Name/category/price can be filled in
    # later – the backend supplies sensible defaults when they're left blank.
    name: Optional[str] = Field(None, max_length=200, example="Front Brake Pads (Set)")
    description: Optional[str] = Field(None, example="Fits Toyota Corolla 2010-2022")
    category: Optional[str] = Field(None, max_length=100, example="Brakes")
    compatible_cars: List[CarCompatibility] = Field(default_factory=list)  # starts as empty list
    stock_quantity: int = Field(0, ge=0)       # ge=0 means must be 0 or greater
    ordered_quantity: int = Field(0, ge=0)
    loaned_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(5, ge=0)
    unit_price: Optional[float] = Field(None, ge=0, example=899.0)  # blank → 0
    location: Optional[str] = Field(None, example="Shelf B, Row 04")


# --- Schema for UPDATING a part (PUT /api/parts/{id}) ---
# All fields are Optional – you only need to send what you want to change
class PartUpdate(BaseModel):
    part_number: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    compatible_cars: Optional[List[CarCompatibility]] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    ordered_quantity: Optional[int] = Field(None, ge=0)
    loaned_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)   # 0 allowed (price filled in later)
    location: Optional[str] = None


# --- Schema for RETURNING a part to the client (GET response) ---
# Contains extra computed fields like available_quantity and stock_status
class PartOut(BaseModel):
    # from_attributes=True means Pydantic can read data from SQLAlchemy model objects
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_number: str
    name: str
    description: Optional[str]
    category: str
    compatible_cars: List[CarCompatibility]
    stock_quantity: int
    ordered_quantity: int
    loaned_quantity: int
    available_quantity: int    # computed: stock - loaned (from the @property in Part model)
    low_stock_threshold: int
    unit_price: float
    location: Optional[str]
    images: List[str]          # list of image file paths
    stock_status: str          # "OK", "Low", or "Empty" (from the @property in Part model)
    created_at: datetime
    updated_at: Optional[datetime]

    # Older imports could store a blank price as NaN, which serialises to an
    # invalid/null JSON value and crashes the table. Treat it as 0 on the way out.
    @field_validator("unit_price", mode="before")
    @classmethod
    def _clean_price(cls, v):
        try:
            if v is None or math.isnan(float(v)):
                return 0.0
        except (ValueError, TypeError):
            return 0.0
        return v
