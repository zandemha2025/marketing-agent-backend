"""Add SSO/SAML fields to users table

Revision ID: 002
Revises: 001
Create Date: 2026-01-30 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SSO/SAML columns to users table
    op.add_column('users', sa.Column('identity_provider', sa.String(20), server_default='local', nullable=False))
    op.add_column('users', sa.Column('saml_subject_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('saml_metadata_xml', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_sso_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('sso_session_index', sa.String(255), nullable=True))
    
    # MFA columns
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('mfa_verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('mfa_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('mfa_backup_codes', sa.JSON(), nullable=True))
    
    # OAuth columns
    op.add_column('users', sa.Column('oauth_provider_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('oauth_access_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_token_expires_at', sa.DateTime(), nullable=True))
    
    # Security tracking columns
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login_ip', sa.String(45), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    
    # Create indexes for SSO queries
    op.create_index('idx_users_saml_subject', 'users', ['saml_subject_id'])
    op.create_index('idx_users_identity_provider', 'users', ['identity_provider'])
    op.create_index('idx_users_oauth_provider', 'users', ['oauth_provider_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_users_oauth_provider', table_name='users')
    op.drop_index('idx_users_identity_provider', table_name='users')
    op.drop_index('idx_users_saml_subject', table_name='users')
    
    # Drop columns (in reverse order)
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'oauth_token_expires_at')
    op.drop_column('users', 'oauth_refresh_token')
    op.drop_column('users', 'oauth_access_token')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'mfa_backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_verified_at')
    op.drop_column('users', 'mfa_enabled')
    op.drop_column('users', 'sso_session_index')
    op.drop_column('users', 'last_sso_login')
    op.drop_column('users', 'saml_metadata_xml')
    op.drop_column('users', 'saml_subject_id')
    op.drop_column('users', 'identity_provider')