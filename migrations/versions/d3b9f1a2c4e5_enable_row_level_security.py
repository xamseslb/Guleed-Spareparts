"""enable row level security on all tables

Locks down the Supabase auto-generated public API (PostgREST): with RLS
enabled and no policies, the anon/authenticated roles can't read or write
these tables. Our FastAPI backend connects as the table owner (postgres),
which bypasses RLS, so the app keeps working normally.

Postgres only – SQLite (the local desktop app) has no public API to protect,
so this migration is a no-op there.

Revision ID: d3b9f1a2c4e5
Revises: c7a1f0b2d3e4
Create Date: 2026-06-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd3b9f1a2c4e5'
down_revision: Union[str, Sequence[str], None] = 'c7a1f0b2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ["parts", "orders", "customers", "loans", "users", "activity_log", "alembic_version"]


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for t in TABLES:
        op.execute(f'ALTER TABLE public."{t}" DISABLE ROW LEVEL SECURITY;')
