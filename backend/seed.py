"""
Seed-data: oppretter testdata for utvikling og demonstrasjon.
Kjør: python -m backend.seed
"""

from backend.database import SessionLocal, engine
from backend.models import Part, Order, Customer, User
from backend.database import Base
from backend.services.auth_service import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if data already exists
    if db.query(User).count() > 0:
        print("[OK] Seed data already exists - skipping.")
        db.close()
        return

    # ─── Users ──────────────────────────────────────────────────────
    admin = User(
        username="admin",
        full_name="Admin User",
        email="admin@guleed.no",
        hashed_password=hash_password("admin123"),
        role="admin",
    )
    ansatt = User(
        username="ansatt1",
        full_name="Guleed Hassan",
        email="ansatt@guleed.no",
        hashed_password=hash_password("ansatt123"),
        role="ansatt",
    )
    db.add_all([admin, ansatt])

    # ─── Customers ───────────────────────────────────────────────────────
    kunder = [
        Customer(name="Ahmed Ali", phone="47412345", email="ahmed@example.com"),
        Customer(name="Lars Nilsen", phone="93412345", email="lars@example.com"),
        Customer(name="Sara Johansen", phone="91234567", email="sara@example.com"),
    ]
    db.add_all(kunder)

    # ─── Spare Parts ─────────────────────────────────────────────────
    varer = [
        Part(
            part_number="BR-8690",
            name="Front Brake Pads (Set)",
            description="Fits Toyota Corolla and Honda Civic",
            category="Bremser",
            compatible_cars=[
                {"make": "Toyota", "model": "Corolla", "year_from": 2010, "year_to": 2022},
                {"make": "Honda", "model": "Civic", "year_from": 2012, "year_to": 2020},
            ],
            stock_quantity=42,
            ordered_quantity=10,
            loaned_quantity=0,
            unit_price=899.0,
            location="Reol B, Hylle 04",
            low_stock_threshold=5,
            images=[],
        ),
        Part(
            part_number="OL-5W40",
            name="Synthetic Engine Oil 5L",
            description="Fully synthetic 5W-40 engine oil",
            category="Olje",
            compatible_cars=[],
            stock_quantity=2,
            ordered_quantity=20,
            loaned_quantity=0,
            unit_price=549.0,
            location="Reol A, Gulv",
            low_stock_threshold=5,
            images=[],
        ),
        Part(
            part_number="TF-1024",
            name="Standard Spark Plug",
            description="Standard spark plug, fits most petrol engines",
            category="Motor",
            compatible_cars=[
                {"make": "BMW", "model": "3-serie", "year_from": 2005, "year_to": 2018},
            ],
            stock_quantity=156,
            ordered_quantity=0,
            loaned_quantity=3,
            unit_price=129.0,
            location="Reol D, Skuff 12",
            low_stock_threshold=10,
            images=[],
        ),
        Part(
            part_number="LF-3301",
            name="Universal Air Filter",
            description="Universal air filter for passenger cars",
            category="Filtre",
            compatible_cars=[],
            stock_quantity=0,
            ordered_quantity=15,
            loaned_quantity=0,
            unit_price=249.0,
            location="Reol C, Hylle 02",
            low_stock_threshold=5,
            images=[],
        ),
        Part(
            part_number="SK-7710",
            name="Rear Shock Absorber",
            description="Hydraulic shock absorber for rear axle",
            category="Fjæring",
            compatible_cars=[
                {"make": "Volkswagen", "model": "Golf", "year_from": 2013, "year_to": 2021},
            ],
            stock_quantity=8,
            ordered_quantity=4,
            loaned_quantity=1,
            unit_price=1499.0,
            location="Reol E, Hylle 01",
            low_stock_threshold=3,
            images=[],
        ),
    ]
    db.add_all(varer)
    db.flush()

    # ─── Ordrer ───────────────────────────────────────────────────────
    ordrer = [
        Order(customer_id=kunder[0].id, part_id=varer[0].id, quantity=2, unit_price_at_order=899.0, status="Levert"),
        Order(customer_id=kunder[1].id, part_id=varer[2].id, quantity=4, unit_price_at_order=129.0, status="Ny"),
        Order(customer_id=kunder[2].id, part_id=varer[1].id, quantity=1, unit_price_at_order=549.0, status="Behandles"),
    ]
    db.add_all(ordrer)
    db.commit()
    print("[OK] Seed data added:")
    print(f"   Users:       {db.query(User).count()}")
    print(f"   Customers:   {db.query(Customer).count()}")
    print(f"   Spare parts: {db.query(Part).count()}")
    print(f"   Orders:      {db.query(Order).count()}")
    db.close()


if __name__ == "__main__":
    seed()
