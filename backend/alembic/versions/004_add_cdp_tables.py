"""Add CDP tables

Revision ID: 004
Revises: 003
Create Date: 2026-01-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('external_ids', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('anonymous_id', sa.String(64), nullable=True),
        sa.Column('traits', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('computed_traits', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('engagement_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('lifetime_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('churn_risk', sa.Float(), nullable=False, server_default='0'),
        sa.Column('recency_days', sa.Float(), nullable=True),
        sa.Column('frequency_score', sa.Float(), nullable=True),
        sa.Column('monetary_value', sa.Float(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('merged_from', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('consent_status', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.String(1), nullable=False, server_default='N'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for customers table
    op.create_index('ix_customers_org_external_ids', 'customers', ['organization_id', 'external_ids'])
    op.create_index('ix_customers_org_anonymous', 'customers', ['organization_id', 'anonymous_id'])
    op.create_index('ix_customers_org_engagement', 'customers', ['organization_id', 'engagement_score'])
    op.create_index('ix_customers_org_ltv', 'customers', ['organization_id', 'lifetime_value'])
    op.create_index('ix_customers_org_last_seen', 'customers', ['organization_id', 'last_seen_at'])
    op.create_index('ix_customers_is_deleted', 'customers', ['is_deleted'])
    op.create_index('ix_customers_anonymous_id', 'customers', ['anonymous_id'])

    # Create customer_identities table
    op.create_table(
        'customer_identities',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('customer_id', sa.String(12), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('identity_type', sa.String(50), nullable=False),
        sa.Column('identity_value', sa.String(500), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1'),
        sa.Column('source', sa.String(50), nullable=False, server_default='web'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', sa.String(1000), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.String(1), nullable=False, server_default='N'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for customer_identities table
    op.create_index('ix_customer_identities_type_value', 'customer_identities', ['identity_type', 'identity_value'], unique=True)
    op.create_index('ix_customer_identities_customer', 'customer_identities', ['customer_id'])
    op.create_index('ix_customer_identities_verified', 'customer_identities', ['is_verified'])
    op.create_index('ix_customer_identities_source', 'customer_identities', ['source'])
    op.create_index('ix_customer_identities_is_deleted', 'customer_identities', ['is_deleted'])

    # Create customer_events table
    op.create_table(
        'customer_events',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('customer_id', sa.String(12), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('anonymous_id', sa.String(64), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('properties', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('context', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('source', sa.String(50), nullable=False, server_default='web'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('integration_id', sa.String(12), nullable=True),
        sa.Column('api_key_id', sa.String(12), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('consent_context', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for customer_events table
    op.create_index('ix_customer_events_customer_id', 'customer_events', ['customer_id'])
    op.create_index('ix_customer_events_anonymous_id', 'customer_events', ['anonymous_id'])
    op.create_index('ix_customer_events_event_type', 'customer_events', ['event_type'])
    op.create_index('ix_customer_events_event_name', 'customer_events', ['event_name'])
    op.create_index('ix_customer_events_org_time', 'customer_events', ['organization_id', 'timestamp'])
    op.create_index('ix_customer_events_customer_time', 'customer_events', ['customer_id', 'timestamp'])
    op.create_index('ix_customer_events_anon_time', 'customer_events', ['anonymous_id', 'timestamp'])
    op.create_index('ix_customer_events_org_type', 'customer_events', ['organization_id', 'event_type'])
    op.create_index('ix_customer_events_org_name', 'customer_events', ['organization_id', 'event_name'])
    op.create_index('ix_customer_events_source', 'customer_events', ['source'])
    op.create_index('ix_customer_events_timestamp', 'customer_events', ['timestamp'])

    # Create customer_segments table
    op.create_table(
        'customer_segments',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('segment_type', sa.String(50), nullable=False, server_default='dynamic'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('criteria', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('event_criteria', sa.JSON(), nullable=True),
        sa.Column('customer_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.Column('is_dynamic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('refresh_interval_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('last_refreshed_at', sa.DateTime(), nullable=True),
        sa.Column('next_refresh_at', sa.DateTime(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.String(1), nullable=False, server_default='N'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for customer_segments table
    op.create_index('ix_customer_segments_org', 'customer_segments', ['organization_id'])
    op.create_index('ix_customer_segments_org_type', 'customer_segments', ['organization_id', 'segment_type'])
    op.create_index('ix_customer_segments_org_status', 'customer_segments', ['organization_id', 'status'])
    op.create_index('ix_customer_segments_dynamic', 'customer_segments', ['is_dynamic'])
    op.create_index('ix_customer_segments_next_refresh', 'customer_segments', ['next_refresh_at'])
    op.create_index('ix_customer_segments_is_deleted', 'customer_segments', ['is_deleted'])

    # Create segment_memberships table
    op.create_table(
        'segment_memberships',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('segment_id', sa.String(12), sa.ForeignKey('customer_segments.id'), nullable=False),
        sa.Column('customer_id', sa.String(12), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.Column('joined_reason', sa.String(50), nullable=True),
        sa.Column('left_reason', sa.String(50), nullable=True),
        sa.Column('matching_criteria_snapshot', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for segment_memberships table
    op.create_index('ix_segment_memberships_segment_customer', 'segment_memberships', ['segment_id', 'customer_id'], unique=True)
    op.create_index('ix_segment_memberships_customer', 'segment_memberships', ['customer_id'])
    op.create_index('ix_segment_memberships_active', 'segment_memberships', ['segment_id', 'left_at'])
    op.create_index('ix_segment_memberships_joined', 'segment_memberships', ['segment_id', 'joined_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('segment_memberships')
    op.drop_table('customer_segments')
    op.drop_table('customer_events')
    op.drop_table('customer_identities')
    op.drop_table('customers')