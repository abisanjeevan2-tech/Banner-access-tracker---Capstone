"""Add email to users and form_pdfs table

Revision ID: 002
Revises: 001

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email column to users
    op.add_column('users',
        sa.Column('email', sa.String(length=255), nullable=True)
    )

    # Create form_pdfs table
    op.create_table('form_pdfs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('file_data', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('form_id')
    )


def downgrade() -> None:
    op.drop_table('form_pdfs')
    op.drop_column('users', 'email')