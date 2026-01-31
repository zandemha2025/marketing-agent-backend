"""
Add optimization tables.

Revision ID: 006
Revises: 005_add_attribution_tables
Create Date: 2026-01-30 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_add_optimization_tables'
down_revision: Union[str, None] = '005_add_attribution_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create optimization tables."""
    
    # Create experiments table
    op.create_table(
        'experiments',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('experiment_type', sa.Enum('AB_TEST', 'MULTIVARIATE', 'BANDIT', name='experimenttype'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'RUNNING', 'PAUSED', 'COMPLETED', 'ARCHIVED', name='experimentstatus'), nullable=False),
        sa.Column('hypothesis', sa.Text, nullable=True),
        sa.Column('primary_metric', sa.String(100), nullable=False),
        sa.Column('secondary_metrics', sa.JSON, default=list),
        sa.Column('traffic_allocation', sa.Float, default=1.0, nullable=False),
        sa.Column('start_date', sa.DateTime, nullable=True),
        sa.Column('end_date', sa.DateTime, nullable=True),
        sa.Column('min_sample_size', sa.Integer, default=100, nullable=False),
        sa.Column('target_sample_size', sa.Integer, nullable=True),
        sa.Column('confidence_level', sa.Float, default=0.95, nullable=False),
        sa.Column('statistical_power', sa.Float, default=0.8, nullable=False),
        sa.Column('minimum_detectable_effect', sa.Float, default=0.05, nullable=False),
        sa.Column('campaign_id', sa.String(12), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('winner_variant_id', sa.String(12), nullable=True),
        sa.Column('winner_declared_at', sa.DateTime, nullable=True),
        sa.Column('winner_reason', sa.Text, nullable=True),
        sa.Column('auto_winner_selection', sa.Boolean, default=False, nullable=False),
        sa.Column('auto_winner_min_confidence', sa.Float, default=0.95, nullable=False),
        sa.Column('auto_winner_min_lift', sa.Float, default=0.05, nullable=False),
        sa.Column('created_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('stopped_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('stopped_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for experiments
    op.create_index('idx_experiments_org', 'experiments', ['organization_id'])
    op.create_index('idx_experiments_campaign', 'experiments', ['campaign_id'])
    op.create_index('idx_experiments_status', 'experiments', ['status'])
    
    # Create experiment_variants table
    op.create_table(
        'experiment_variants',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('experiment_id', sa.String(12), sa.ForeignKey('experiments.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('traffic_percentage', sa.Float, nullable=False),
        sa.Column('configuration', sa.JSON, default=dict),
        sa.Column('is_control', sa.Boolean, default=False, nullable=False),
        sa.Column('bandit_successes', sa.Integer, default=0, nullable=False),
        sa.Column('bandit_failures', sa.Integer, default=0, nullable=False),
        sa.Column('bandit_pulls', sa.Integer, default=0, nullable=False),
        sa.Column('total_assignments', sa.Integer, default=0, nullable=False),
        sa.Column('total_conversions', sa.Integer, default=0, nullable=False),
        sa.Column('conversion_rate', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for variants
    op.create_index('idx_variants_experiment', 'experiment_variants', ['experiment_id'])
    op.create_index('idx_variants_control', 'experiment_variants', ['experiment_id', 'is_control'])
    
    # Create experiment_assignments table
    op.create_table(
        'experiment_assignments',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('experiment_id', sa.String(12), sa.ForeignKey('experiments.id'), nullable=False),
        sa.Column('variant_id', sa.String(12), sa.ForeignKey('experiment_variants.id'), nullable=False),
        sa.Column('user_id', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('anonymous_id', sa.String(64), nullable=True),
        sa.Column('assigned_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('context', sa.JSON, default=dict),
        sa.Column('first_exposed_at', sa.DateTime, nullable=True),
        sa.Column('converted_at', sa.DateTime, nullable=True),
        sa.Column('conversion_value', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('experiment_id', 'user_id', name='uq_experiment_user'),
        sa.UniqueConstraint('experiment_id', 'anonymous_id', name='uq_experiment_anonymous'),
    )
    
    # Create indexes for assignments
    op.create_index('idx_assignments_experiment', 'experiment_assignments', ['experiment_id'])
    op.create_index('idx_assignments_variant', 'experiment_assignments', ['variant_id'])
    op.create_index('idx_assignments_user', 'experiment_assignments', ['user_id'])
    op.create_index('idx_assignments_anonymous', 'experiment_assignments', ['anonymous_id'])
    
    # Create experiment_results table
    op.create_table(
        'experiment_results',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('experiment_id', sa.String(12), sa.ForeignKey('experiments.id'), nullable=False),
        sa.Column('variant_id', sa.String(12), sa.ForeignKey('experiment_variants.id'), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('sample_size', sa.Integer, nullable=False),
        sa.Column('conversions', sa.Integer, default=0, nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_sum', sa.Float, nullable=True),
        sa.Column('metric_sum_squares', sa.Float, nullable=True),
        sa.Column('lift_percentage', sa.Float, nullable=True),
        sa.Column('lift_absolute', sa.Float, nullable=True),
        sa.Column('p_value', sa.Float, nullable=True),
        sa.Column('is_statistically_significant', sa.Boolean, default=False, nullable=False),
        sa.Column('confidence_level', sa.Float, default=0.95, nullable=False),
        sa.Column('confidence_interval_lower', sa.Float, nullable=True),
        sa.Column('confidence_interval_upper', sa.Float, nullable=True),
        sa.Column('cohens_d', sa.Float, nullable=True),
        sa.Column('statistical_test', sa.String(50), nullable=True),
        sa.Column('additional_metrics', sa.JSON, default=dict),
        sa.Column('calculated_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('calculation_method', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for results
    op.create_index('idx_results_experiment', 'experiment_results', ['experiment_id'])
    op.create_index('idx_results_variant', 'experiment_results', ['variant_id'])
    op.create_index('idx_results_metric', 'experiment_results', ['experiment_id', 'metric_name'])
    
    # Create predictive_models table
    op.create_table(
        'predictive_models',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('model_type', sa.Enum('CTR_PREDICTION', 'CONVERSION_PREDICTION', 'REVENUE_PREDICTION', 
                                        'ENGAGEMENT_PREDICTION', 'LTV_PREDICTION', 'CHURN_PREDICTION', 
                                        'MULTI_TARGET', name='predictivemodeltype'), nullable=False),
        sa.Column('status', sa.Enum('TRAINING', 'ACTIVE', 'DEPRECATED', 'FAILED', 'ARCHIVED', 
                                    name='predictivemodelstatus'), nullable=False),
        sa.Column('campaign_id', sa.String(12), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('feature_columns', sa.JSON, default=list),
        sa.Column('target_column', sa.String(100), nullable=False),
        sa.Column('model_parameters', sa.JSON, nullable=True),
        sa.Column('model_algorithm', sa.String(50), nullable=True),
        sa.Column('model_version', sa.String(20), default='1.0.0', nullable=False),
        sa.Column('training_metrics', sa.JSON, default=dict),
        sa.Column('validation_metrics', sa.JSON, default=dict),
        sa.Column('feature_importance', sa.JSON, default=dict),
        sa.Column('training_data_count', sa.Integer, default=0, nullable=False),
        sa.Column('last_trained_at', sa.DateTime, nullable=True),
        sa.Column('hyperparameters', sa.JSON, default=dict),
        sa.Column('accuracy_threshold', sa.Float, default=0.7, nullable=False),
        sa.Column('is_active', sa.Boolean, default=False, nullable=False),
        sa.Column('total_predictions', sa.Integer, default=0, nullable=False),
        sa.Column('last_prediction_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for predictive models
    op.create_index('idx_predictive_models_org', 'predictive_models', ['organization_id'])
    op.create_index('idx_predictive_models_campaign', 'predictive_models', ['campaign_id'])
    op.create_index('idx_predictive_models_type', 'predictive_models', ['model_type'])
    op.create_index('idx_predictive_models_active', 'predictive_models', ['organization_id', 'is_active'])
    
    # Create optimization_logs table
    op.create_table(
        'optimization_logs',
        sa.Column('id', sa.String(12), primary_key=True),
        sa.Column('organization_id', sa.String(12), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('campaign_id', sa.String(12), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('before_state', sa.JSON, default=dict),
        sa.Column('after_state', sa.JSON, default=dict),
        sa.Column('expected_impact', sa.Float, nullable=False),
        sa.Column('actual_impact', sa.Float, nullable=True),
        sa.Column('executed_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('executed_by', sa.String(12), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for optimization logs
    op.create_index('idx_optimization_logs_campaign', 'optimization_logs', ['campaign_id'])
    op.create_index('idx_optimization_logs_org', 'optimization_logs', ['organization_id'])
    op.create_index('idx_optimization_logs_time', 'optimization_logs', ['executed_at'])


def downgrade() -> None:
    """Drop optimization tables."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('optimization_logs')
    op.drop_table('predictive_models')
    op.drop_table('experiment_results')
    op.drop_table('experiment_assignments')
    op.drop_table('experiment_variants')
    op.drop_table('experiments')
    
    # Drop enum types (PostgreSQL specific)
    op.execute('DROP TYPE IF EXISTS experimenttype')
    op.execute('DROP TYPE IF EXISTS experimentstatus')
    op.execute('DROP TYPE IF EXISTS predictivemodeltype')
    op.execute('DROP TYPE IF EXISTS predictivemodelstatus')