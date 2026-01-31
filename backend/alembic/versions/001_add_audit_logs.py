"""Add audit logs table

Revision ID: 001
Revises: 
Create Date: 2026-01-30 15:00:00.000000

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
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('resource_name', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('before_values', sa.JSON(), nullable=True),
        sa.Column('after_values', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('retention_until', sa.DateTime(), nullable=True),
        sa.Column('compliance_flags', sa.JSON(), server_default='[]'),
        sa.Column('encrypted', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for common query patterns
    op.create_index('idx_audit_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_org_id', 'audit_logs', ['organization_id'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('idx_audit_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_request_id', 'audit_logs', ['request_id'])
    
    # Composite indexes
    op.create_index('idx_audit_org_action_time', 'audit_logs', ['organization_id', 'action', 'timestamp'])
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id', 'timestamp'])
    op.create_index('idx_audit_retention', 'audit_logs', ['retention_until'])
    
    # For PostgreSQL, create partitioned table (optional optimization)
    # This would require more complex migration for production


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_audit_retention', table_name='audit_logs')
    op.drop_index('idx_audit_resource', table_name='audit_logs')
    op.drop_index('idx_audit_user_time', table_name='audit_logs')
    op.drop_index('idx_audit_org_action_time', table_name='audit_logs')
    op.drop_index('idx_audit_request_id', table_name='audit_logs')
    op.drop_index('idx_audit_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_resource_id', table_name='audit_logs')
    op.drop_index('idx_audit_resource_type', table_name='audit_logs')
    op.drop_index('idx_audit_action', table_name='audit_logs')
    op.drop_index('idx_audit_org_id', table_name='audit_logs')
    op.drop_index('idx_audit_user_id', table_name='audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')