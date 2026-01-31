"""Add GDPR compliance tables

Revision ID: 003
Revises: 002
Create Date: 2026-01-30 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create consents table
    op.create_table(
        'consents',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('user_id', sa.String(12), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('consent_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='granted', nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('consent_version', sa.String(20), server_default='1.0', nullable=False),
        sa.Column('privacy_policy_version', sa.String(20), nullable=True),
        sa.Column('terms_of_service_version', sa.String(20), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('country_code', sa.String(2), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for consents
    op.create_index('idx_consent_user_id', 'consents', ['user_id'])
    op.create_index('idx_consent_org_id', 'consents', ['organization_id'])
    op.create_index('idx_consent_type', 'consents', ['consent_type'])
    op.create_index('idx_consent_status', 'consents', ['status'])
    op.create_index('idx_consent_user_type', 'consents', ['user_id', 'consent_type'])
    op.create_index('idx_consent_org_type', 'consents', ['organization_id', 'consent_type'])
    op.create_index('idx_consent_status_date', 'consents', ['status', 'granted_at'])
    
    # Create data_subject_requests table
    op.create_table(
        'data_subject_requests',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('request_number', sa.String(20), unique=True, nullable=False),
        sa.Column('user_id', sa.String(12), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('request_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('priority', sa.String(10), server_default='normal', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('specific_data', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('completion_deadline', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('verification_method', sa.String(20), nullable=True),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('verification_expires', sa.DateTime(), nullable=True),
        sa.Column('verified_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('result_details', sa.Text(), nullable=True),
        sa.Column('download_url', sa.String(500), nullable=True),
        sa.Column('download_expires', sa.DateTime(), nullable=True),
        sa.Column('records_affected', sa.String(50), server_default='0', nullable=False),
        sa.Column('extension_requested', sa.String(1), server_default='N', nullable=False),
        sa.Column('extension_reason', sa.Text(), nullable=True),
        sa.Column('extended_deadline', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejection_category', sa.String(50), nullable=True),
        sa.Column('jurisdiction', sa.String(10), server_default='GDPR', nullable=False),
        sa.Column('source', sa.String(50), server_default='web', nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for data_subject_requests
    op.create_index('idx_dsr_request_number', 'data_subject_requests', ['request_number'])
    op.create_index('idx_dsr_user_id', 'data_subject_requests', ['user_id'])
    op.create_index('idx_dsr_org_id', 'data_subject_requests', ['organization_id'])
    op.create_index('idx_dsr_type', 'data_subject_requests', ['request_type'])
    op.create_index('idx_dsr_status', 'data_subject_requests', ['status'])
    op.create_index('idx_dsr_priority', 'data_subject_requests', ['priority'])
    op.create_index('idx_dsr_org_status', 'data_subject_requests', ['organization_id', 'status'])
    op.create_index('idx_dsr_user_type', 'data_subject_requests', ['user_id', 'request_type'])
    op.create_index('idx_dsr_deadline', 'data_subject_requests', ['completion_deadline', 'status'])
    op.create_index('idx_dsr_priority_status', 'data_subject_requests', ['priority', 'status'])


def downgrade() -> None:
    # Drop data_subject_requests table and indexes
    op.drop_index('idx_dsr_priority_status', table_name='data_subject_requests')
    op.drop_index('idx_dsr_deadline', table_name='data_subject_requests')
    op.drop_index('idx_dsr_user_type', table_name='data_subject_requests')
    op.drop_index('idx_dsr_org_status', table_name='data_subject_requests')
    op.drop_index('idx_dsr_priority', table_name='data_subject_requests')
    op.drop_index('idx_dsr_status', table_name='data_subject_requests')
    op.drop_index('idx_dsr_type', table_name='data_subject_requests')
    op.drop_index('idx_dsr_org_id', table_name='data_subject_requests')
    op.drop_index('idx_dsr_user_id', table_name='data_subject_requests')
    op.drop_index('idx_dsr_request_number', table_name='data_subject_requests')
    op.drop_table('data_subject_requests')
    
    # Drop consents table and indexes
    op.drop_index('idx_consent_status_date', table_name='consents')
    op.drop_index('idx_consent_org_type', table_name='consents')
    op.drop_index('idx_consent_user_type', table_name='consents')
    op.drop_index('idx_consent_status', table_name='consents')
    op.drop_index('idx_consent_type', table_name='consents')
    op.drop_index('idx_consent_org_id', table_name='consents')
    op.drop_index('idx_consent_user_id', table_name='consents')
    op.drop_table('consents')