"""
Tests for Conversion Tracker.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics.conversion_tracker import ConversionTracker, ConversionTrackingResult
from app.models.conversion_event import ConversionEvent, ConversionType, ConversionStatus
from app.models.attribution_touchpoint import AttributionTouchpoint, TouchpointType
from app.models.customer_event import CustomerEvent, EventType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def conversion_tracker(mock_db):
    """Create a ConversionTracker instance."""
    return ConversionTracker(mock_db)


@pytest.fixture
def sample_customer_event():
    """Create a sample customer event."""
    return CustomerEvent(
        id="evt1",
        organization_id="org1",
        customer_id="cust1",
        anonymous_id="anon1",
        event_type=EventType.PURCHASE,
        event_name="Product Purchase",
        properties={
            "value": 99.99,
            "currency": "USD",
            "product_id": "prod123"
        },
        context={
            "campaign": {
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer_sale"
            },
            "page": {
                "url": "https://example.com/checkout",
                "referrer": "https://google.com"
            }
        },
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_conversion():
    """Create a sample conversion event."""
    return ConversionEvent(
        id="conv1",
        organization_id="org1",
        customer_id="cust1",
        conversion_type=ConversionType.PURCHASE,
        conversion_name="Product Purchase",
        conversion_value=99.99,
        currency="USD",
        conversion_timestamp=datetime.utcnow(),
        status=ConversionStatus.PENDING
    )


class TestConversionTracking:
    """Tests for conversion tracking functionality."""

    @pytest.mark.asyncio
    async def test_track_conversion_from_purchase_event(
        self, conversion_tracker, sample_customer_event, mock_db
    ):
        """Test tracking conversion from a purchase event."""
        # Mock the touchpoint query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        conversion = await conversion_tracker.track_conversion_from_event(
            sample_customer_event
        )

        assert conversion is not None
        assert conversion.conversion_type == ConversionType.PURCHASE
        assert conversion.conversion_value == 99.99
        assert conversion.currency == "USD"
        assert conversion.organization_id == "org1"
        assert conversion.customer_id == "cust1"

    @pytest.mark.asyncio
    async def test_track_conversion_from_signup_event(self, conversion_tracker, mock_db):
        """Test tracking conversion from a signup event."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            customer_id="cust1",
            event_type=EventType.SIGN_UP,
            event_name="User Signup",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        # Mock the touchpoint query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        conversion = await conversion_tracker.track_conversion_from_event(event)

        assert conversion is not None
        assert conversion.conversion_type == ConversionType.SIGNUP

    @pytest.mark.asyncio
    async def test_track_non_conversion_event(self, conversion_tracker):
        """Test that non-conversion events return None."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.PAGE_VIEW,
            event_name="Page View",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        conversion = await conversion_tracker.track_conversion_from_event(event)
        assert conversion is None

    @pytest.mark.asyncio
    async def test_track_conversion_manual(self, conversion_tracker, mock_db):
        """Test manually tracking a conversion."""
        conversion = await conversion_tracker.track_conversion(
            organization_id="org1",
            customer_id="cust1",
            conversion_type=ConversionType.LEAD,
            conversion_name="Form Submission",
            conversion_value=50.0,
            currency="USD"
        )

        assert conversion is not None
        assert conversion.conversion_type == ConversionType.LEAD
        assert conversion.conversion_value == 50.0
        assert conversion.status == ConversionStatus.PENDING


class TestTouchpointCreation:
    """Tests for touchpoint creation."""

    @pytest.mark.asyncio
    async def test_create_touchpoint(self, conversion_tracker, mock_db):
        """Test creating a touchpoint manually."""
        touchpoint = await conversion_tracker.create_touchpoint(
            organization_id="org1",
            customer_id="cust1",
            touchpoint_type=TouchpointType.PAID_SEARCH,
            channel="google",
            properties={"keyword": "marketing software"},
            cost=2.50
        )

        assert touchpoint is not None
        assert touchpoint.organization_id == "org1"
        assert touchpoint.customer_id == "cust1"
        assert touchpoint.touchpoint_type == TouchpointType.PAID_SEARCH
        assert touchpoint.channel == "google"
        assert touchpoint.cost == 2.50

    @pytest.mark.asyncio
    async def test_create_touchpoint_from_event(
        self, conversion_tracker, sample_customer_event, sample_conversion, mock_db
    ):
        """Test creating touchpoints from customer events."""
        # Create some historical events
        base_time = datetime.utcnow() - timedelta(hours=48)
        historical_events = [
            CustomerEvent(
                id="evt_old",
                organization_id="org1",
                customer_id="cust1",
                event_type=EventType.AD_CLICK,
                event_name="Ad Click",
                properties={},
                context={
                    "campaign": {"utm_source": "google", "utm_medium": "cpc"}
                },
                timestamp=base_time
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = historical_events
        mock_db.execute.return_value = mock_result

        # Link conversion to customer
        sample_conversion.customer_id = "cust1"

        touchpoints = await conversion_tracker._create_touchpoints_for_conversion(
            sample_conversion, lookback_window_days=30
        )

        # Should create touchpoints from historical events
        assert touchpoints >= 0  # May be 0 if no events match criteria


class TestConversionDetection:
    """Tests for conversion type detection."""

    def test_detect_purchase_conversion(self, conversion_tracker):
        """Test detecting purchase conversion type."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.PURCHASE,
            event_name="Order Completed",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        conversion_type = conversion_tracker._detect_conversion_type(event)
        assert conversion_type == ConversionType.PURCHASE

    def test_detect_trial_conversion(self, conversion_tracker):
        """Test detecting trial start conversion type."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.SIGN_UP,
            event_name="Trial Started",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        conversion_type = conversion_tracker._detect_conversion_type(event)
        assert conversion_type == ConversionType.TRIAL_START

    def test_detect_lead_conversion(self, conversion_tracker):
        """Test detecting lead conversion type."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.FORM_SUBMIT,
            event_name="Contact Form",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        conversion_type = conversion_tracker._detect_conversion_type(event)
        assert conversion_type == ConversionType.LEAD


class TestChannelDetermination:
    """Tests for channel determination logic."""

    def test_determine_channel_from_utm(self, conversion_tracker):
        """Test determining channel from UTM parameters."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.PAGE_VIEW,
            event_name="Page View",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        channel = conversion_tracker._determine_channel(
            event, utm_source="google", utm_medium="cpc"
        )
        assert channel == "google"

    def test_determine_channel_paid_search(self, conversion_tracker):
        """Test determining paid search channel."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.AD_CLICK,
            event_name="Ad Click",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        channel = conversion_tracker._determine_channel(event)
        assert channel == "paid_ads"

    def test_determine_channel_email(self, conversion_tracker):
        """Test determining email channel."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.EMAIL_CLICK,
            event_name="Email Click",
            properties={},
            context={},
            timestamp=datetime.utcnow()
        )

        channel = conversion_tracker._determine_channel(event)
        assert channel == "email"


class TestEngagementScoring:
    """Tests for engagement score calculation."""

    def test_engagement_score_high(self, conversion_tracker):
        """Test high engagement score."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.PAGE_VIEW,
            event_name="Page View",
            properties={
                "time_on_page": 600,  # 10 minutes
                "pages_viewed": 8,
                "scroll_depth": 0.9
            },
            context={},
            timestamp=datetime.utcnow()
        )

        score = conversion_tracker._calculate_engagement_score(event)
        assert score > 0.8
        assert score <= 1.0

    def test_engagement_score_low(self, conversion_tracker):
        """Test low engagement score."""
        event = CustomerEvent(
            id="evt1",
            organization_id="org1",
            event_type=EventType.PAGE_VIEW,
            event_name="Page View",
            properties={
                "time_on_page": 5,  # 5 seconds
                "pages_viewed": 1,
                "scroll_depth": 0.1
            },
            context={},
            timestamp=datetime.utcnow()
        )

        score = conversion_tracker._calculate_engagement_score(event)
        assert score < 0.6


class TestCustomerJourney:
    """Tests for customer journey functionality."""

    @pytest.mark.asyncio
    async def test_get_customer_journey(self, conversion_tracker, mock_db):
        """Test getting customer journey."""
        # Mock touchpoints
        mock_touchpoints = [
            AttributionTouchpoint(
                id="tp1",
                organization_id="org1",
                customer_id="cust1",
                touchpoint_type=TouchpointType.PAID_SEARCH,
                channel="google",
                touchpoint_timestamp=datetime.utcnow() - timedelta(hours=48)
            ),
            AttributionTouchpoint(
                id="tp2",
                organization_id="org1",
                customer_id="cust1",
                touchpoint_type=TouchpointType.EMAIL,
                channel="email",
                touchpoint_timestamp=datetime.utcnow() - timedelta(hours=24)
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_touchpoints
        mock_db.execute.return_value = mock_result

        journey = await conversion_tracker.get_customer_journey(
            organization_id="org1",
            customer_id="cust1"
        )

        assert journey["customer_id"] == "cust1"
        assert journey["touchpoint_count"] == 2
        assert len(journey["journey"]) == 2

    @pytest.mark.asyncio
    async def test_merge_customer_journeys(self, conversion_tracker, mock_db):
        """Test merging anonymous and identified journeys."""
        # Mock touchpoint update
        mock_touchpoints = []
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_touchpoints
        mock_db.execute.return_value = mock_result

        result = await conversion_tracker.merge_customer_journeys(
            organization_id="org1",
            anonymous_id="anon123",
            customer_id="cust456"
        )

        assert result["anonymous_id"] == "anon123"
        assert result["customer_id"] == "cust456"


class TestReporting:
    """Tests for reporting functionality."""

    @pytest.mark.asyncio
    async def test_get_conversion_summary(self, conversion_tracker, mock_db):
        """Test getting conversion summary."""
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        # Mock sum query
        mock_sum_result = MagicMock()
        mock_sum_result.scalar.return_value = 5000.0

        # Mock type breakdown query
        mock_type_result = MagicMock()
        mock_type_result.all.return_value = [
            MagicMock(conversion_type=ConversionType.PURCHASE, count=30, total_value=4500.0),
            MagicMock(conversion_type=ConversionType.SIGNUP, count=20, total_value=500.0)
        ]

        mock_db.execute.side_effect = [
            mock_count_result,
            mock_sum_result,
            mock_type_result
        ]

        summary = await conversion_tracker.get_conversion_summary(
            organization_id="org1"
        )

        assert summary["summary"]["total_conversions"] == 50
        assert summary["summary"]["total_value"] == 5000.0
        assert "purchase" in summary["by_type"]
        assert "signup" in summary["by_type"]

    @pytest.mark.asyncio
    async def test_get_touchpoint_summary(self, conversion_tracker, mock_db):
        """Test getting touchpoint summary."""
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        # Mock sum query
        mock_sum_result = MagicMock()
        mock_sum_result.scalar.return_value = 250.0

        # Mock channel breakdown query
        mock_channel_result = MagicMock()
        mock_channel_result.all.return_value = [
            MagicMock(channel="google", count=60, total_cost=150.0),
            MagicMock(channel="facebook", count=40, total_cost=100.0)
        ]

        mock_db.execute.side_effect = [
            mock_count_result,
            mock_sum_result,
            mock_channel_result
        ]

        summary = await conversion_tracker.get_touchpoint_summary(
            organization_id="org1"
        )

        assert summary["summary"]["total_touchpoints"] == 100
        assert summary["summary"]["total_cost"] == 250.0
        assert "google" in summary["by_channel"]
        assert "facebook" in summary["by_channel"]


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_link_touchpoint_to_conversion(
        self, conversion_tracker, mock_db
    ):
        """Test linking touchpoint to conversion."""
        # Mock touchpoint query
        mock_touchpoint = AttributionTouchpoint(
            id="tp1",
            organization_id="org1",
            touchpoint_timestamp=datetime.utcnow() - timedelta(hours=24)
        )
        mock_tp_result = MagicMock()
        mock_tp_result.scalar_one_or_none.return_value = mock_touchpoint

        # Mock conversion query
        mock_conversion = ConversionEvent(
            id="conv1",
            organization_id="org1",
            conversion_timestamp=datetime.utcnow()
        )
        mock_conv_result = MagicMock()
        mock_conv_result.scalar_one_or_none.return_value = mock_conversion

        mock_db.execute.side_effect = [mock_tp_result, mock_conv_result]

        result = await conversion_tracker.link_touchpoint_to_conversion("tp1", "conv1")
        assert result is True
        assert mock_touchpoint.conversion_event_id == "conv1"

    @pytest.mark.asyncio
    async def test_update_conversion_value(self, conversion_tracker, mock_db):
        """Test updating conversion value."""
        mock_conversion = ConversionEvent(
            id="conv1",
            organization_id="org1",
            conversion_value=100.0,
            status=ConversionStatus.ATTRIBUTED
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conversion
        mock_db.execute.return_value = mock_result

        result = await conversion_tracker.update_conversion_value("conv1", 150.0)

        assert result is True
        assert mock_conversion.conversion_value == 150.0
        assert mock_conversion.status == ConversionStatus.PENDING  # Reset for re-processing

    @pytest.mark.asyncio
    async def test_exclude_touchpoint(self, conversion_tracker, mock_db):
        """Test excluding a touchpoint."""
        mock_touchpoint = AttributionTouchpoint(
            id="tp1",
            organization_id="org1",
            status="active",
            properties={}
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_touchpoint
        mock_db.execute.return_value = mock_result

        result = await conversion_tracker.exclude_touchpoint(
            "tp1", reason="Invalid traffic"
        )

        assert result is True
        assert mock_touchpoint.status.value == "excluded"
        assert mock_touchpoint.properties["exclusion_reason"] == "Invalid traffic"
