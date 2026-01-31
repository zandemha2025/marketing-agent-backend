"""
Tests for Attribution Models.
"""
import pytest
from datetime import datetime

from app.models.attribution import Attribution, AttributionModelType, AttributionStatus, AttributionModelConfig
from app.models.attribution_touchpoint import AttributionTouchpoint, TouchpointType, TouchpointStatus
from app.models.conversion_event import ConversionEvent, ConversionType, ConversionStatus
from app.models.marketing_mix_model import (
    MarketingMixModel, MMMChannel, MMMChannelDaily, MMMPrediction,
    MMMBudgetOptimizer, MMMModelStatus, MMMChannelType
)


class TestAttributionModel:
    """Tests for Attribution model."""

    def test_attribution_creation(self):
        """Test creating an Attribution instance."""
        attribution = Attribution(
            id="attr1",
            organization_id="org1",
            conversion_event_id="conv1",
            touchpoint_id="tp1",
            model_type=AttributionModelType.LINEAR,
            weight=0.33,
            attributed_value=33.0,
            status=AttributionStatus.CALCULATED
        )

        assert attribution.id == "attr1"
        assert attribution.weight == 0.33
        assert attribution.attributed_value == 33.0

    def test_attribution_get_roi(self):
        """Test calculating ROI for attribution."""
        attribution = Attribution(
            id="attr1",
            organization_id="org1",
            conversion_event_id="conv1",
            touchpoint_id="tp1",
            model_type=AttributionModelType.LINEAR,
            weight=0.5,
            attributed_value=100.0
        )

        # Create mock touchpoint with cost
        touchpoint = AttributionTouchpoint(
            id="tp1",
            organization_id="org1",
            cost=25.0
        )
        attribution.touchpoint = touchpoint

        roi = attribution.get_roi()
        assert roi == 3.0  # (100-25)/25

        roas = attribution.get_roas()
        assert roas == 4.0  # 100/25

    def test_attribution_model_type_checks(self):
        """Test model type classification methods."""
        single_touch = Attribution(
            model_type=AttributionModelType.FIRST_TOUCH
        )
        assert single_touch.is_single_touch() is True
        assert single_touch.is_multi_touch() is False

        multi_touch = Attribution(
            model_type=AttributionModelType.LINEAR
        )
        assert multi_touch.is_single_touch() is False
        assert multi_touch.is_multi_touch() is True

        algorithmic = Attribution(
            model_type=AttributionModelType.MARKOV_CHAIN
        )
        assert algorithmic.is_algorithmic() is True


class TestAttributionTouchpoint:
    """Tests for AttributionTouchpoint model."""

    def test_touchpoint_creation(self):
        """Test creating an AttributionTouchpoint."""
        touchpoint = AttributionTouchpoint(
            id="tp1",
            organization_id="org1",
            touchpoint_type=TouchpointType.PAID_SEARCH,
            channel="google",
            utm_source="google",
            utm_medium="cpc",
            cost=2.50
        )

        assert touchpoint.id == "tp1"
        assert touchpoint.channel == "google"
        assert touchpoint.cost == 2.50

    def test_is_paid_touchpoint(self):
        """Test identifying paid touchpoints."""
        paid = AttributionTouchpoint(
            touchpoint_type=TouchpointType.PAID_SEARCH
        )
        assert paid.is_paid_touchpoint() is True

        organic = AttributionTouchpoint(
            touchpoint_type=TouchpointType.ORGANIC_SEARCH
        )
        assert organic.is_paid_touchpoint() is False

    def test_get_journey_stage(self):
        """Test determining journey stage."""
        first = AttributionTouchpoint(
            position_in_journey=1
        )
        assert first.get_journey_stage() == "awareness"

        middle = AttributionTouchpoint(
            position_in_journey=3,
            time_to_conversion_hours=200  # > 7 days
        )
        assert middle.get_journey_stage() == "consideration"

        last = AttributionTouchpoint(
            position_in_journey=5,
            time_to_conversion_hours=12  # < 1 day
        )
        assert last.get_journey_stage() == "decision"

    def test_get_attributed_value(self):
        """Test getting total attributed value."""
        touchpoint = AttributionTouchpoint(id="tp1")

        # Create mock attributions
        attr1 = Attribution(
            model_type=AttributionModelType.FIRST_TOUCH,
            attributed_value=50.0
        )
        attr2 = Attribution(
            model_type=AttributionModelType.LAST_TOUCH,
            attributed_value=100.0
        )
        touchpoint.attributions = [attr1, attr2]

        total = touchpoint.get_attributed_value()
        assert total == 150.0

        first_only = touchpoint.get_attributed_value(model="first_touch")
        assert first_only == 50.0


class TestConversionEvent:
    """Tests for ConversionEvent model."""

    def test_conversion_creation(self):
        """Test creating a ConversionEvent."""
        conversion = ConversionEvent(
            id="conv1",
            organization_id="org1",
            customer_id="cust1",
            conversion_type=ConversionType.PURCHASE,
            conversion_name="Product Purchase",
            conversion_value=99.99,
            currency="USD",
            status=ConversionStatus.PENDING
        )

        assert conversion.id == "conv1"
        assert conversion.conversion_type == ConversionType.PURCHASE
        assert conversion.conversion_value == 99.99

    def test_get_attributed_value(self):
        """Test getting attributed value across models."""
        conversion = ConversionEvent(id="conv1")

        attr1 = Attribution(
            model_type=AttributionModelType.FIRST_TOUCH,
            attributed_value=50.0
        )
        attr2 = Attribution(
            model_type=AttributionModelType.LAST_TOUCH,
            attributed_value=100.0
        )
        conversion.attributions = [attr1, attr2]

        total = conversion.get_attributed_value()
        assert total == 150.0

        first_only = conversion.get_attributed_value(model="first_touch")
        assert first_only == 50.0

    def test_get_primary_attribution(self):
        """Test getting primary attribution."""
        conversion = ConversionEvent(id="conv1")

        attr1 = Attribution(attributed_value=50.0)
        attr2 = Attribution(attributed_value=100.0)
        conversion.attributions = [attr1, attr2]

        primary = conversion.get_primary_attribution()
        assert primary == attr2  # Highest value

    def test_get_touchpoint_summary(self):
        """Test getting touchpoint summary."""
        conversion = ConversionEvent(id="conv1")

        tp1 = AttributionTouchpoint(
            id="tp1",
            touchpoint_type=TouchpointType.PAID_SEARCH,
            channel="google",
            position_in_journey=1
        )
        tp2 = AttributionTouchpoint(
            id="tp2",
            touchpoint_type=TouchpointType.EMAIL,
            channel="email",
            position_in_journey=2
        )
        conversion.touchpoints = [tp1, tp2]

        summary = conversion.get_touchpoint_summary()
        assert len(summary) == 2
        assert summary[0]["id"] == "tp1"
        assert summary[1]["id"] == "tp2"


class TestAttributionModelConfig:
    """Tests for AttributionModelConfig model."""

    def test_config_creation(self):
        """Test creating model config."""
        config = AttributionModelConfig(
            id="cfg1",
            organization_id="org1",
            model_type=AttributionModelType.TIME_DECAY,
            name="7-Day Time Decay",
            lookback_window_days=30
        )

        assert config.model_type == AttributionModelType.TIME_DECAY
        assert config.lookback_window_days == 30

    def test_get_effective_parameters_time_decay(self):
        """Test getting effective parameters for time decay."""
        config = AttributionModelConfig(
            model_type=AttributionModelType.TIME_DECAY,
            parameters={"time_decay_half_life_days": 14}
        )

        params = config.get_effective_parameters()
        assert params["time_decay_half_life_days"] == 14
        assert params["lookback_window_days"] == 30  # Default

    def test_get_effective_parameters_position_based(self):
        """Test getting effective parameters for position-based."""
        config = AttributionModelConfig(
            model_type=AttributionModelType.POSITION_BASED,
            parameters={"position_weights": {"first": 0.5, "last": 0.3}}
        )

        params = config.get_effective_parameters()
        assert "position_weights" in params
        assert params["exclude_direct"] is False  # Default


class TestMarketingMixModel:
    """Tests for MarketingMixModel."""

    def test_model_creation(self):
        """Test creating a MarketingMixModel."""
        model = MarketingMixModel(
            id="model1",
            organization_id="org1",
            name="Q1 2024 MMM",
            target_variable="revenue",
            status=MMMModelStatus.DRAFT
        )

        assert model.id == "model1"
        assert model.target_variable == "revenue"

    def test_is_ready_for_prediction(self):
        """Test model readiness check."""
        trained = MarketingMixModel(status=MMMModelStatus.TRAINED)
        assert trained.is_ready_for_prediction() is True

        validated = MarketingMixModel(status=MMMModelStatus.VALIDATED)
        assert validated.is_ready_for_prediction() is True

        deployed = MarketingMixModel(status=MMMModelStatus.DEPLOYED)
        assert deployed.is_ready_for_prediction() is True

        draft = MarketingMixModel(status=MMMModelStatus.DRAFT)
        assert draft.is_ready_for_prediction() is False

    def test_get_channel_roi(self):
        """Test getting channel ROI."""
        model = MarketingMixModel(
            model_coefficients={
                "channels": {
                    "paid_search": {"roi": 3.5},
                    "paid_social": {"roi": 2.8}
                }
            }
        )

        roi = model.get_channel_roi("paid_search")
        assert roi == 3.5

        missing = model.get_channel_roi("tv")
        assert missing is None

    def test_get_total_contribution_pct(self):
        """Test getting total contribution percentages."""
        model = MarketingMixModel(
            model_coefficients={
                "channels": {
                    "paid_search": {"contribution_pct": 0.4},
                    "paid_social": {"contribution_pct": 0.3}
                },
                "baseline": {"contribution_pct": 0.3}
            }
        )

        contributions = model.get_total_contribution_pct()
        assert contributions["paid_search"] == 0.4
        assert contributions["paid_social"] == 0.3
        assert contributions["baseline"] == 0.3


class TestMMMChannel:
    """Tests for MMMChannel model."""

    def test_channel_creation(self):
        """Test creating an MMMChannel."""
        channel = MMMChannel(
            id="ch1",
            model_id="model1",
            channel_type=MMMChannelType.PAID_SEARCH,
            channel_name="paid_search",
            roi=3.5,
            marginal_roi=3.2
        )

        assert channel.channel_type == MMMChannelType.PAID_SEARCH
        assert channel.roi == 3.5


class TestMMMBudgetOptimizer:
    """Tests for MMMBudgetOptimizer model."""

    def test_optimizer_creation(self):
        """Test creating a budget optimizer result."""
        optimizer = MMMBudgetOptimizer(
            id="opt1",
            model_id="model1",
            organization_id="org1",
            total_budget=100000,
            improvement_pct=15.0,
            improvement_absolute=25000.0,
            current_predicted_total=150000,
            optimized_predicted_total=175000
        )

        assert optimizer.total_budget == 100000
        assert optimizer.improvement_pct == 15.0

    def test_get_reallocation_recommendations(self):
        """Test getting reallocation recommendations."""
        optimizer = MMMBudgetOptimizer(
            current_allocation={
                "paid_search": {"spend": 50000},
                "paid_social": {"spend": 30000},
                "display": {"spend": 20000}
            },
            optimized_allocation={
                "paid_search": {"spend": 60000, "predicted_return": 150000, "marginal_roi": 2.5},
                "paid_social": {"spend": 25000, "predicted_return": 55000, "marginal_roi": 2.2},
                "display": {"spend": 15000, "predicted_return": 28000, "marginal_roi": 1.9}
            }
        )

        recommendations = optimizer.get_reallocation_recommendations()

        assert len(recommendations) == 3

        # Find paid_search recommendation
        paid_search_rec = next(r for r in recommendations if r["channel"] == "paid_search")
        assert paid_search_rec["current_spend"] == 50000
        assert paid_search_rec["recommended_spend"] == 60000
        assert paid_search_rec["change_amount"] == 10000
        assert paid_search_rec["change_pct"] == 20.0


class TestModelEnums:
    """Tests for model enums."""

    def test_attribution_model_type_values(self):
        """Test AttributionModelType enum values."""
        assert AttributionModelType.FIRST_TOUCH.value == "first_touch"
        assert AttributionModelType.LAST_TOUCH.value == "last_touch"
        assert AttributionModelType.LINEAR.value == "linear"
        assert AttributionModelType.TIME_DECAY.value == "time_decay"
        assert AttributionModelType.POSITION_BASED.value == "position_based"
        assert AttributionModelType.DATA_DRIVEN.value == "data_driven"

    def test_conversion_type_values(self):
        """Test ConversionType enum values."""
        assert ConversionType.PURCHASE.value == "purchase"
        assert ConversionType.SIGNUP.value == "signup"
        assert ConversionType.LEAD.value == "lead"
        assert ConversionType.TRIAL_START.value == "trial_start"

    def test_touchpoint_type_values(self):
        """Test TouchpointType enum values."""
        assert TouchpointType.PAID_SEARCH.value == "paid_search"
        assert TouchpointType.EMAIL.value == "email"
        assert TouchpointType.ORGANIC_SEARCH.value == "organic_search"
        assert TouchpointType.DIRECT.value == "direct"

    def test_mmm_channel_type_values(self):
        """Test MMMChannelType enum values."""
        assert MMMChannelType.PAID_SEARCH.value == "paid_search"
        assert MMMChannelType.TV.value == "tv"
        assert MMMChannelType.EMAIL.value == "email"
        assert MMMChannelType.BASELINE.value == "baseline"
