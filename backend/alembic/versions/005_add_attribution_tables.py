"""Add attribution and analytics tables

Revision ID: 005
Revises: 004
Create Date: 2026-01-30 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversion_events table
    op.create_table(
        'conversion_events',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('customer_id', sa.String(12), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('anonymous_id', sa.String(64), nullable=True),
        sa.Column('conversion_type', sa.String(50), nullable=False),
        sa.Column('conversion_name', sa.String(100), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('conversion_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('context', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('attribution_model', sa.String(50), nullable=True),
        sa.Column('attributed_touchpoint_count', sa.Integer(), nullable=True),
        sa.Column('attribution_confidence', sa.Float(), nullable=True),
        sa.Column('lookback_window_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('conversion_timestamp', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('campaign_id', sa.String(12), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for conversion_events table
    op.create_index('ix_conversion_events_org_time', 'conversion_events', ['organization_id', 'conversion_timestamp'])
    op.create_index('ix_conversion_events_customer_time', 'conversion_events', ['customer_id', 'conversion_timestamp'])
    op.create_index('ix_conversion_events_campaign', 'conversion_events', ['campaign_id', 'conversion_timestamp'])
    op.create_index('ix_conversion_events_status', 'conversion_events', ['status', 'conversion_timestamp'])
    op.create_index('ix_conversion_events_org_type', 'conversion_events', ['organization_id', 'conversion_type'])
    op.create_index('ix_conversion_events_anonymous', 'conversion_events', ['anonymous_id'])

    # Create attribution_touchpoints table
    op.create_table(
        'attribution_touchpoints',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('customer_id', sa.String(12), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('anonymous_id', sa.String(64), nullable=True),
        sa.Column('conversion_event_id', sa.String(12), sa.ForeignKey('conversion_events.id'), nullable=True),
        sa.Column('touchpoint_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('sub_channel', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(12), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('campaign_name', sa.String(255), nullable=True),
        sa.Column('ad_group_id', sa.String(100), nullable=True),
        sa.Column('ad_id', sa.String(100), nullable=True),
        sa.Column('creative_id', sa.String(100), nullable=True),
        sa.Column('creative_name', sa.String(255), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(255), nullable=True),
        sa.Column('utm_content', sa.String(255), nullable=True),
        sa.Column('utm_term', sa.String(255), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('context', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('position_in_journey', sa.Integer(), nullable=True),
        sa.Column('time_to_conversion_hours', sa.Float(), nullable=True),
        sa.Column('engagement_score', sa.Float(), nullable=True),
        sa.Column('time_on_page_seconds', sa.Integer(), nullable=True),
        sa.Column('pages_viewed', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('cost_currency', sa.String(3), nullable=True),
        sa.Column('touchpoint_timestamp', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('source_event_id', sa.String(12), sa.ForeignKey('customer_events.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for attribution_touchpoints table
    op.create_index('ix_touchpoints_org_time', 'attribution_touchpoints', ['organization_id', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_customer_time', 'attribution_touchpoints', ['customer_id', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_conversion', 'attribution_touchpoints', ['conversion_event_id', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_campaign', 'attribution_touchpoints', ['campaign_id', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_org_channel', 'attribution_touchpoints', ['organization_id', 'channel', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_utm_campaign', 'attribution_touchpoints', ['utm_campaign', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_utm_source_medium', 'attribution_touchpoints', ['utm_source', 'utm_medium', 'touchpoint_timestamp'])
    op.create_index('ix_touchpoints_anonymous', 'attribution_touchpoints', ['anonymous_id'])

    # Create attributions table
    op.create_table(
        'attributions',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('conversion_event_id', sa.String(12), sa.ForeignKey('conversion_events.id'), nullable=False),
        sa.Column('touchpoint_id', sa.String(12), sa.ForeignKey('attribution_touchpoints.id'), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('model_version', sa.String(20), nullable=False, server_default='1.0'),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('attributed_value', sa.Float(), nullable=False),
        sa.Column('attributed_revenue', sa.Float(), nullable=True),
        sa.Column('model_parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('touchpoint_position', sa.Integer(), nullable=True),
        sa.Column('total_touchpoints', sa.Integer(), nullable=True),
        sa.Column('hours_to_conversion', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.Column('calculation_duration_ms', sa.Integer(), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('validated_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for attributions table
    op.create_index('ix_attributions_unique', 'attributions', ['conversion_event_id', 'touchpoint_id', 'model_type'], unique=True)
    op.create_index('ix_attributions_conversion', 'attributions', ['conversion_event_id', 'model_type'])
    op.create_index('ix_attributions_touchpoint', 'attributions', ['touchpoint_id', 'model_type'])
    op.create_index('ix_attributions_org_model', 'attributions', ['organization_id', 'model_type', 'calculated_at'])
    op.create_index('ix_attributions_value', 'attributions', ['attributed_value', 'calculated_at'])

    # Create attribution_model_configs table
    op.create_table(
        'attribution_model_configs',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.String(1), nullable=False, server_default='Y'),
        sa.Column('is_default', sa.String(1), nullable=False, server_default='N'),
        sa.Column('lookback_window_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('excluded_channels', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('excluded_touchpoint_types', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('min_confidence_threshold', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('require_validation', sa.String(1), nullable=False, server_default='N'),
        sa.Column('created_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for attribution_model_configs table
    op.create_index('ix_attribution_configs_default', 'attribution_model_configs', ['organization_id', 'model_type', 'is_default'], unique=True)
    op.create_index('ix_attribution_configs_org', 'attribution_model_configs', ['organization_id', 'model_type'])

    # Create marketing_mix_models table
    op.create_table(
        'marketing_mix_models',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('workspace_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('target_variable', sa.String(50), nullable=False),
        sa.Column('target_unit', sa.String(20), nullable=True),
        sa.Column('training_start_date', sa.Date(), nullable=True),
        sa.Column('training_end_date', sa.Date(), nullable=True),
        sa.Column('prediction_horizon_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('model_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('performance_metrics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('model_coefficients', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('adstock_params', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('saturation_params', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('feature_importance', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('diagnostics', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('trained_at', sa.DateTime(), nullable=True),
        sa.Column('trained_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('training_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('validated_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('parent_model_id', sa.String(12), sa.ForeignKey('marketing_mix_models.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for marketing_mix_models table
    op.create_index('ix_mmm_models_org_status', 'marketing_mix_models', ['organization_id', 'status'])
    op.create_index('ix_mmm_models_trained_at', 'marketing_mix_models', ['trained_at'])
    op.create_index('ix_mmm_models_target', 'marketing_mix_models', ['organization_id', 'target_variable'])

    # Create mmm_channels table
    op.create_table(
        'mmm_channels',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('model_id', sa.String(12), sa.ForeignKey('marketing_mix_models.id'), nullable=False),
        sa.Column('channel_type', sa.String(50), nullable=False),
        sa.Column('channel_name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('adstock_decay', sa.Float(), nullable=True),
        sa.Column('adstock_peak_delay', sa.Integer(), nullable=True),
        sa.Column('saturation_shape', sa.String(20), nullable=True),
        sa.Column('saturation_k', sa.Float(), nullable=True),
        sa.Column('saturation_half_spend', sa.Float(), nullable=True),
        sa.Column('total_spend', sa.Float(), nullable=True),
        sa.Column('total_impressions', sa.Float(), nullable=True),
        sa.Column('avg_daily_spend', sa.Float(), nullable=True),
        sa.Column('spend_currency', sa.String(3), nullable=True),
        sa.Column('coefficient', sa.Float(), nullable=True),
        sa.Column('standard_error', sa.Float(), nullable=True),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('marginal_roi', sa.Float(), nullable=True),
        sa.Column('contribution_pct', sa.Float(), nullable=True),
        sa.Column('elasticity', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for mmm_channels table
    op.create_index('ix_mmm_channels_model_type', 'mmm_channels', ['model_id', 'channel_type'])
    op.create_index('ix_mmm_channels_roi', 'mmm_channels', ['roi'])

    # Create mmm_channel_daily table
    op.create_table(
        'mmm_channel_daily',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('channel_id', sa.String(12), sa.ForeignKey('mmm_channels.id'), nullable=False),
        sa.Column('model_id', sa.String(12), sa.ForeignKey('marketing_mix_models.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('spend', sa.Float(), nullable=True),
        sa.Column('spend_currency', sa.String(3), nullable=True),
        sa.Column('impressions', sa.Float(), nullable=True),
        sa.Column('clicks', sa.Float(), nullable=True),
        sa.Column('conversions', sa.Float(), nullable=True),
        sa.Column('adstocked_spend', sa.Float(), nullable=True),
        sa.Column('saturated_spend', sa.Float(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for mmm_channel_daily table
    op.create_index('ix_mmm_daily_channel_date', 'mmm_channel_daily', ['channel_id', 'date'])
    op.create_index('ix_mmm_daily_model_date', 'mmm_channel_daily', ['model_id', 'date'])

    # Create mmm_predictions table
    op.create_table(
        'mmm_predictions',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('model_id', sa.String(12), sa.ForeignKey('marketing_mix_models.id'), nullable=False),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('prediction_type', sa.String(50), nullable=False, server_default='forecast'),
        sa.Column('scenario_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('predicted_total', sa.Float(), nullable=False),
        sa.Column('prediction_interval_lower', sa.Float(), nullable=True),
        sa.Column('prediction_interval_upper', sa.Float(), nullable=True),
        sa.Column('channel_predictions', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
    )

    # Create indexes for mmm_predictions table
    op.create_index('ix_mmm_predictions_model_date', 'mmm_predictions', ['model_id', 'start_date'])
    op.create_index('ix_mmm_predictions_org', 'mmm_predictions', ['organization_id', 'created_at'])

    # Create mmm_budget_optimizers table
    op.create_table(
        'mmm_budget_optimizers',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('model_id', sa.String(12), sa.ForeignKey('marketing_mix_models.id'), nullable=False),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('total_budget', sa.Float(), nullable=False),
        sa.Column('budget_currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('optimization_period_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('constraints', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('current_allocation', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('optimized_allocation', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('current_predicted_total', sa.Float(), nullable=False),
        sa.Column('optimized_predicted_total', sa.Float(), nullable=False),
        sa.Column('improvement_pct', sa.Float(), nullable=False),
        sa.Column('improvement_absolute', sa.Float(), nullable=False),
        sa.Column('optimization_algorithm', sa.String(50), nullable=False, server_default='gradient_descent'),
        sa.Column('iterations', sa.Integer(), nullable=True),
        sa.Column('convergence_tolerance', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
    )

    # Create indexes for mmm_budget_optimizers table
    op.create_index('ix_mmm_optimizer_model', 'mmm_budget_optimizers', ['model_id', 'created_at'])
    op.create_index('ix_mmm_optimizer_org', 'mmm_budget_optimizers', ['organization_id', 'created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('mmm_budget_optimizers')
    op.drop_table('mmm_predictions')
    op.drop_table('mmm_channel_daily')
    op.drop_table('mmm_channels')
    op.drop_table('marketing_mix_models')
    op.drop_table('attribution_model_configs')
    op.drop_table('attributions')
    op.drop_table('attribution_touchpoints')
    op.drop_table('conversion_events')
