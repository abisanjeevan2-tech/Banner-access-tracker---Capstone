"""Initial migration

Revision ID: 001
Revises: 

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create roles table
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cwid', sa.String(length=20), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cwid'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_cwid'), 'users', ['cwid'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create forms table
    op.create_table('forms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_forms_code'), 'forms', ['code'], unique=True)

    # Create permission_groups table
    op.create_table('permission_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_permission_groups_name'), 'permission_groups', ['name'], unique=True)

    # Create access_requests table
    op.create_table('access_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('applicant_user_id', sa.Integer(), nullable=False),
        sa.Column('submitted_by_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('secure_notes_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['applicant_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_access_requests_created_at'), 'access_requests', ['created_at'], unique=False)
    op.create_index(op.f('ix_access_requests_status'), 'access_requests', ['status'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # Create access_changes table
    op.create_table('access_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_access_request_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_user_id', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['original_access_request_id'], ['access_requests.id'], ),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create approvals table
    op.create_table('approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('access_request_id', sa.Integer(), nullable=False),
        sa.Column('grantor_user_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['access_request_id'], ['access_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grantor_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('access_request_id', 'grantor_user_id', name='unique_grantor_per_request')
    )

    # Create attachments table
    op.create_table('attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('access_request_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['access_request_id'], ['access_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create association tables
    op.create_table('access_request_forms',
        sa.Column('access_request_id', sa.Integer(), nullable=True),
        sa.Column('form_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['access_request_id'], ['access_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE')
    )

    op.create_table('access_request_permission_groups',
        sa.Column('access_request_id', sa.Integer(), nullable=True),
        sa.Column('permission_group_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['access_request_id'], ['access_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_group_id'], ['permission_groups.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('access_request_permission_groups')
    op.drop_table('access_request_forms')
    op.drop_table('attachments')
    op.drop_table('approvals')
    op.drop_table('access_changes')
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_table('system_settings')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_access_requests_status'), table_name='access_requests')
    op.drop_index(op.f('ix_access_requests_created_at'), table_name='access_requests')
    op.drop_table('access_requests')
    op.drop_index(op.f('ix_permission_groups_name'), table_name='permission_groups')
    op.drop_table('permission_groups')
    op.drop_index(op.f('ix_forms_code'), table_name='forms')
    op.drop_table('forms')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_cwid'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
