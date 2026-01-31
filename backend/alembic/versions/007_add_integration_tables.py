"""Add integration tables for CRM, data warehouse, and CDP integrations.

Revision ID: 007
Revises: 006_add_optimization_tables
Create Date: 2026-01-30 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_integration_tables'
down_revision: Union[str, None] = '006_add_optimization_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create integration tables."""
    
    # Create enum types
    integration_type_enum = sa.Enum(
        'CRM', 'DATA_WAREHOUSE', 'CDP', 'EMAIL', 'ADS', 'ANALYTICS', 'CUSTOM',
        name='integrationtype'
    )
    integration_type_enum.create(op.get_bind(), checkfirst=True)
    
    integration_provider_enum = sa.Enum(
        'SALESFORCE', 'HUBSPOT', 'DYNAMICS', 'PIPEDRIVE', 'ZOHO',
        'SNOWFLAKE', 'BIGQUERY', 'DATABRICKS', 'REDSHIFT',
        'SEGMENT', 'MPARTICLE', 'TEALIUM',
        'SENDGRID', 'MAILGUN', 'MAILCHIMP',
        'GOOGLE_ADS', 'FACEBOOK_ADS', 'LINKEDIN_ADS',
        'GOOGLE_ANALYTICS', 'MIXPANEL', 'AMPLITUDE',
        name='integrationprovider'
    )
    integration_provider_enum.create(op.get_bind(), checkfirst=True)
    
    integration_status_enum = sa.Enum(
        'ACTIVE', 'INACTIVE', 'ERROR', 'SYNCING', 'PENDING', 'AUTH_REQUIRED',
        name='integrationstatus'
    )
    integration_status_enum.create(op.get_bind(), checkfirst=True)
    
    sync_type_enum = sa.Enum(
        'INITIAL', 'INCREMENTAL', 'FULL', 'REALTIME', 'MANUAL', 'SCHEDULED', 'BATCH',
        name='synctype'
    )
    sync_type_enum.create(op.get_bind(), checkfirst=True)
    
    sync_status_enum = sa.Enum(
        'PENDING', 'RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED', 'CANCELLED', 'TIMEOUT',
        name='syncstatus'
    )
    sync_status_enum.create(op.get_bind(), checkfirst=True)
    
    sync_direction_enum = sa.Enum(
        'INBOUND', 'OUTBOUND', 'BIDIRECTIONAL',
        name='syncdirection'
    )
    sync_direction_enum.create(op.get_bind(), checkfirst=True)
    
    mapping_direction_enum = sa.Enum(
        'INBOUND', 'OUTBOUND', 'BIDIRECTIONAL',
        name='mappingdirection'
    )
    mapping_direction_enum.create(op.get_bind(), checkfirst=True)
    
    conflict_strategy_enum = sa.Enum(
        'SOURCE_WINS', 'TARGET_WINS', 'TIMESTAMP_WINS', 'MERGE', 'MANUAL',
        name='conflictstrategy'
    )
    conflict_strategy_enum.create(op.get_bind(), checkfirst=True)
    
    # Create integrations table
    op.create_table(
        'integrations',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('integration_type', sa.Enum('CRM', 'DATA_WAREHOUSE', 'CDP', 'EMAIL', 'ADS', 'ANALYTICS', 'CUSTOM', name='integrationtype'), nullable=False),
        sa.Column('provider', sa.Enum('SALESFORCE', 'HUBSPOT', 'DYNAMICS', 'PIPEDRIVE', 'ZOHO', 'SNOWFLAKE', 'BIGQUERY', 'DATABRICKS', 'REDSHIFT', 'SEGMENT', 'MPARTICLE', 'TEALIUM', 'SENDGRID', 'MAILGUN', 'MAILCHIMP', 'GOOGLE_ADS', 'FACEBOOK_ADS', 'LINKEDIN_ADS', 'GOOGLE_ANALYTICS', 'MIXPANEL', 'AMPLITUDE', name='integrationprovider'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ERROR', 'SYNCING', 'PENDING', 'AUTH_REQUIRED', name='integrationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('auth_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('sync_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('webhook_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(50), nullable=True),
        sa.Column('last_sync_records', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_error_at', sa.DateTime(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('error_count', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('connected_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('provider_metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('rate_limit_remaining', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('rate_limit_reset_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for integrations
    op.create_index('idx_integration_org', 'integrations', ['organization_id'])
    op.create_index('idx_integration_org_type', 'integrations', ['organization_id', 'integration_type'])
    op.create_index('idx_integration_org_provider', 'integrations', ['organization_id', 'provider'])
    op.create_index('idx_integration_status', 'integrations', ['status'])
    op.create_index('idx_integration_provider', 'integrations', ['provider'])
    
    # Create integration_sync_logs table
    op.create_table(
        'integration_sync_logs',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('integration_id', sa.String(12), sa.ForeignKey('integrations.id'), nullable=False),
        sa.Column('sync_type', sa.Enum('INITIAL', 'INCREMENTAL', 'FULL', 'REALTIME', 'MANUAL', 'SCHEDULED', 'BATCH', name='synctype'), nullable=False),
        sa.Column('sync_direction', sa.Enum('INBOUND', 'OUTBOUND', 'BIDIRECTIONAL', name='syncdirection'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'SUCCESS', 'PARTIAL', 'FAILED', 'CANCELLED', 'TIMEOUT', name='syncstatus'), nullable=False, server_default='PENDING'),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('record_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('sync_config_snapshot', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('api_calls_made', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_calls_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bytes_transferred', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rate_limit_hits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rate_limit_wait_seconds', sa.Float(), nullable=False, server_default='0'),
        sa.Column('triggered_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for integration_sync_logs
    op.create_index('idx_sync_log_integration', 'integration_sync_logs', ['integration_id'])
    op.create_index('idx_sync_log_integration_started', 'integration_sync_logs', ['integration_id', 'started_at'])
    op.create_index('idx_sync_log_status', 'integration_sync_logs', ['status'])
    op.create_index('idx_sync_log_status_entity', 'integration_sync_logs', ['status', 'entity_type'])
    op.create_index('idx_sync_log_date_range', 'integration_sync_logs', ['started_at', 'completed_at'])
    op.create_index('idx_sync_log_celery_task', 'integration_sync_logs', ['celery_task_id'])
    
    # Create integration_mappings table
    op.create_table(
        'integration_mappings',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('integration_id', sa.String(12), sa.ForeignKey('integrations.id'), nullable=False),
        sa.Column('source_entity', sa.String(100), nullable=False),
        sa.Column('target_entity', sa.String(100), nullable=False),
        sa.Column('direction', sa.Enum('INBOUND', 'OUTBOUND', 'BIDIRECTIONAL', name='mappingdirection'), nullable=False, server_default='BIDIRECTIONAL'),
        sa.Column('field_mappings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('transformation_rules', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('default_values', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('required_fields', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('validation_rules', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('conflict_strategy', sa.Enum('SOURCE_WINS', 'TARGET_WINS', 'TIMESTAMP_WINS', 'MERGE', 'MANUAL', name='conflictstrategy'), nullable=False, server_default='TIMESTAMP_WINS'),
        sa.Column('conflict_resolution_script', sa.Text(), nullable=True),
        sa.Column('filter_conditions', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sync_on_create', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_on_update', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_on_delete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_version_id', sa.String(12), sa.ForeignKey('integration_mappings.id'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for integration_mappings
    op.create_index('idx_mapping_integration', 'integration_mappings', ['integration_id'])
    op.create_index('idx_mapping_integration_entity', 'integration_mappings', ['integration_id', 'source_entity', 'target_entity'])
    op.create_index('idx_mapping_direction', 'integration_mappings', ['direction'])
    op.create_index('idx_mapping_active', 'integration_mappings', ['is_active'])
    op.create_index('idx_mapping_priority', 'integration_mappings', ['priority'])


def downgrade() -> None:
    """Drop integration tables."""
    
    # Drop tables in reverse order
    op.drop_table('integration_mappings')
    op.drop_table('integration_sync_logs')
    op.drop_table('integrations')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS conflictstrategy')
    op.execute('DROP TYPE IF EXISTS mappingdirection')
    op.execute('DROP TYPE IF EXISTS syncdirection')
    op.execute('DROP TYPE IF EXISTS syncstatus')
    op.execute('DROP TYPE IF EXISTS synctype')
    op.execute('DROP TYPE IF EXISTS integrationstatus')
    op.execute('DROP TYPE IF EXISTS integrationprovider')
    op.execute('DROP TYPE IF EXISTS integrationtype')
