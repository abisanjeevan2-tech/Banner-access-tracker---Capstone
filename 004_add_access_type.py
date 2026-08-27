"""Add access_type to access_requests

Revision ID: 004
Revises: 003

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('access_requests',
        sa.Column('access_type', sa.String(length=20), nullable=False, server_default='Read')
    )


def downgrade() -> None:
    op.drop_column('access_requests', 'access_type')