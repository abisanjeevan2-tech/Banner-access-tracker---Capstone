"""Add form_id to approvals table

Revision ID: 005
Revises: 004
Create Date: 2026-04-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('approvals',
        sa.Column('form_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_approvals_form_id', 'approvals', 'forms',
        ['form_id'], ['id'], ondelete='SET NULL'
    )
    # Remove old unique constraint
    op.drop_constraint('unique_grantor_per_request', 'approvals', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint(
        'unique_grantor_per_request', 'approvals',
        ['access_request_id', 'grantor_user_id']
    )
    op.drop_constraint('fk_approvals_form_id', 'approvals', type_='foreignkey')
    op.drop_column('approvals', 'form_id')