"""Add grantor forms assignment table

Revision ID: 003
Revises: 002

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('grantor_forms',
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('form_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('grantor_forms')