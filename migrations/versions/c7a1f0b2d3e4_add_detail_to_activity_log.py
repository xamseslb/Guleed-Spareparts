"""add detail to activity log

Revision ID: c7a1f0b2d3e4
Revises: 2a5461201fca
Create Date: 2026-06-28 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1f0b2d3e4'
down_revision: Union[str, Sequence[str], None] = '2a5461201fca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('activity_log', sa.Column('detail', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('activity_log', 'detail')
