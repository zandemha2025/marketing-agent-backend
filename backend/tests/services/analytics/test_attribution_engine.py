"""
Tests for Attribution Engine.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from app.services.analytics.attribution_engine import AttributionEngine, AttributionResult
from app.models.attribution import AttributionModelType
from app.models.attribution_touchpoint import AttributionTouchpoint, TouchpointType
from app.models.conversion_event import ConversionEvent, ConversionType, ConversionStatus


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def attribution_engine(mock_db):
    """Create an AttributionEngine instance."""
    return AttributionEngine(mock_db)


@pytest.fixture
def sample_touchpoints():
    """Create sample touchpoints for testing."""
    base_time = datetime.utcnow()
    return [
        AttributionTouchpoint(
            id="tp1",
            organization_id="org1",
            touchpoint_type=TouchpointType.PAID_SEARCH,
            channel="google",
            touchpoint_timestamp=base_time - timedelta(hours=72),
            conversion_event_id="conv1"
        ),
        AttributionTouchpoint(
            id="tp2",
            organization_id="org1",
            touchpoint_type=TouchpointType.EMAIL,
            channel="email",
            touchpoint_timestamp=base_time - timedelta(hours=48),
            conversion_event_id="conv1"
        ),
        AttributionTouchpoint(
            id="tp3",
            organization_id="org1",
            touchpoint_type=TouchpointType.PAID_SOCIAL,
            channel="facebook",
            touchpoint_timestamp=base_time - timedelta(hours=24),
            conversion_event_id="conv1"
        ),
    ]


class TestFirstTouchAttribution:
    """Tests for first-touch attribution model."""

    @pytest.mark.asyncio
    async def test_first_touch_single_touchpoint(self, attribution_engine):
        """Test first-touch with single touchpoint."""
        touchpoints = [
            AttributionTouchpoint(
                id="tp1",
                organization_id="org1",
                touchpoint_type=TouchpointType.PAID_SEARCH,
                channel="google",
                touchpoint_timestamp=datetime.utcnow()
            )
        ]

        results = await attribution_engine.calculate_first_touch_attribution(
            touchpoints, conversion_value=100.0
        )

        assert len(results) == 1
        assert results[0].weight == 1.0
        assert results[0].attributed_value == 100.0
        assert results[0].model_type == AttributionModelType.FIRST_TOUCH

    @pytest.mark.asyncio
    async def test_first_touch_multiple_touchpoints(self, attribution_engine, sample_touchpoints):
        """Test first-touch with multiple touchpoints."""
        results = await attribution_engine.calculate_first_touch_attribution(
            sample_touchpoints, conversion_value=100.0
        )

        assert len(results) == 3
        assert results[0].weight == 1.0  # First touchpoint gets 100%
        assert results[0].attributed_value == 100.0
        assert results[1].weight == 0.0
        assert results[2].weight == 0.0

    @pytest.mark.asyncio
    async def test_first_touch_empty_list(self, attribution_engine):
        """Test first-touch with empty touchpoint list."""
        results = await attribution_engine.calculate_first_touch_attribution([], 100.0)
        assert len(results) == 0


class TestLastTouchAttribution:
    """Tests for last-touch attribution model."""

    @pytest.mark.asyncio
    async def test_last_touch_multiple_touchpoints(self, attribution_engine, sample_touchpoints):
        """Test last-touch with multiple touchpoints."""
        results = await attribution_engine.calculate_last_touch_attribution(
            sample_touchpoints, conversion_value=100.0
        )

        assert len(results) == 3
        assert results[0].weight == 0.0
        assert results[1].weight == 0.0
        assert results[2].weight == 1.0  # Last touchpoint gets 100%
        assert results[2].attributed_value == 100.0


class TestLinearAttribution:
    """Tests for linear attribution model."""

    @pytest.mark.asyncio
    async def test_linear_three_touchpoints(self, attribution_engine, sample_touchpoints):
        """Test linear attribution with three touchpoints."""
        results = await attribution_engine.calculate_linear_attribution(
            sample_touchpoints, conversion_value=90.0
        )

        assert len(results) == 3
        expected_weight = 1.0 / 3.0
        for result in results:
            assert result.weight == pytest.approx(expected_weight)
            assert result.attributed_value == pytest.approx(30.0)

    @pytest.mark.asyncio
    async def test_linear_empty_list(self, attribution_engine):
        """Test linear attribution with empty list."""
        results = await attribution_engine.calculate_linear_attribution([], 100.0)
        assert len(results) == 0


class TestTimeDecayAttribution:
    """Tests for time-decay attribution model."""

    @pytest.mark.asyncio
    async def test_time_decay_weights(self, attribution_engine, sample_touchpoints):
        """Test that time-decay gives higher weight to recent touchpoints."""
        results = await attribution_engine.calculate_time_decay_attribution(
            sample_touchpoints, conversion_value=100.0, half_life_days=7.0
        )

        assert len(results) == 3
        # Recent touchpoints should have higher weights
        assert results[0].weight < results[1].weight < results[2].weight
        # Weights should sum to 1
        total_weight = sum(r.weight for r in results)
        assert total_weight == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_time_decay_single_touchpoint(self, attribution_engine):
        """Test time-decay with single touchpoint."""
        touchpoints = [
            AttributionTouchpoint(
                id="tp1",
                organization_id="org1",
                touchpoint_type=TouchpointType.PAID_SEARCH,
                channel="google",
                touchpoint_timestamp=datetime.utcnow()
            )
        ]

        results = await attribution_engine.calculate_time_decay_attribution(
            touchpoints, conversion_value=100.0
        )

        assert len(results) == 1
        assert results[0].weight == 1.0


class TestPositionBasedAttribution:
    """Tests for position-based (U-shaped) attribution model."""

    @pytest.mark.asyncio
    async def test_position_based_default_weights(self, attribution_engine, sample_touchpoints):
        """Test position-based attribution with default weights."""
        results = await attribution_engine.calculate_position_based_attribution(
            sample_touchpoints, conversion_value=100.0
        )

        assert len(results) == 3
        # First and last get 40%, middle gets 20%
        assert results[0].weight == pytest.approx(0.4)
        assert results[1].weight == pytest.approx(0.2)
        assert results[2].weight == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_position_based_custom_weights(self, attribution_engine, sample_touchpoints):
        """Test position-based attribution with custom weights."""
        results = await attribution_engine.calculate_position_based_attribution(
            sample_touchpoints, conversion_value=100.0,
            first_touch_weight=0.5, last_touch_weight=0.3
        )

        assert len(results) == 3
        assert results[0].weight == pytest.approx(0.5)
        assert results[1].weight == pytest.approx(0.2)  # Remaining 20%
        assert results[2].weight == pytest.approx(0.3)


class TestWShapedAttribution:
    """Tests for W-shaped attribution model."""

    @pytest.mark.asyncio
    async def test_w_shaped_multiple_touchpoints(self, attribution_engine, sample_touchpoints):
        """Test W-shaped attribution with multiple touchpoints."""
        results = await attribution_engine.calculate_w_shaped_attribution(
            sample_touchpoints, conversion_value=100.0
        )

        assert len(results) == 3
        # With 3 touchpoints, weights should be equal
        for result in results:
            assert result.weight == pytest.approx(1.0 / 3.0)


class TestAttributionEngineIntegration:
    """Integration tests for AttributionEngine."""

    @pytest.mark.asyncio
    async def test_process_conversion(self, attribution_engine, mock_db):
        """Test processing a conversion event."""
        # Setup mock
        conversion = ConversionEvent(
            id="conv1",
            organization_id="org1",
            customer_id="cust1",
            conversion_type=ConversionType.PURCHASE,
            conversion_name="Purchase",
            conversion_value=100.0,
            conversion_timestamp=datetime.utcnow(),
            status=ConversionStatus.PENDING
        )

        # Mock the touchpoint query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        results = await attribution_engine.process_conversion(conversion)

        # Should return empty dict since no touchpoints found
        assert results == {}
        assert conversion.status == ConversionStatus.EXCLUDED

    @pytest.mark.asyncio
    async def test_get_attribution_summary(self, attribution_engine, mock_db):
        """Test getting attribution summary."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                channel="google",
                total_attributed=500.0,
                touchpoint_count=10,
                avg_weight=0.5
            ),
            MagicMock(
                channel="facebook",
                total_attributed=300.0,
                touchpoint_count=5,
                avg_weight=0.3
            )
        ]
        mock_db.execute.return_value = mock_result

        summary = await attribution_engine.get_attribution_summary(
            organization_id="org1",
            model_type=AttributionModelType.LAST_TOUCH
        )

        assert summary["model_type"] == "last_touch"
        assert "google" in summary["channels"]
        assert "facebook" in summary["channels"]
        assert summary["total_attributed"] == 800.0
        assert summary["total_touchpoints"] == 15


class TestAttributionResult:
    """Tests for AttributionResult dataclass."""

    def test_attribution_result_creation(self):
        """Test creating an AttributionResult."""
        result = AttributionResult(
            touchpoint_id="tp1",
            conversion_event_id="conv1",
            model_type=AttributionModelType.LINEAR,
            weight=0.33,
            attributed_value=33.0,
            position=1,
            total_touchpoints=3,
            hours_to_conversion=24.0,
            confidence_score=0.95
        )

        assert result.touchpoint_id == "tp1"
        assert result.weight == 0.33
        assert result.attributed_value == 33.0
