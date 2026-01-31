"""
Tests for Analytics Dashboard Service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analytics.analytics_dashboard import (
    AnalyticsDashboardService, DashboardMetric, TimeSeriesPoint
)
from app.models.attribution import AttributionModelType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def dashboard_service(mock_db):
    """Create an AnalyticsDashboardService instance."""
    return AnalyticsDashboardService(mock_db)


class TestOverviewMetrics:
    """Tests for overview metrics."""

    @pytest.mark.asyncio
    async def test_get_overview_metrics(self, dashboard_service, mock_db):
        """Test getting overview metrics."""
        # Mock revenue query
        mock_revenue_result = MagicMock()
        mock_revenue_result.scalar.side_effect = [10000.0, 8000.0]  # current, previous

        # Mock conversions query
        mock_conv_result = MagicMock()
        mock_conv_result.scalar.side_effect = [50, 40]  # current, previous

        # Mock attributed revenue query
        mock_attr_result = MagicMock()
        mock_attr_result.scalar.side_effect = [8000.0, 6000.0]

        # Mock top channels query
        mock_channels_result = MagicMock()
        mock_channels_result.all.return_value = [
            MagicMock(channel="google", total_attributed=5000.0, touchpoint_count=100, avg_weight=0.5),
            MagicMock(channel="facebook", total_attributed=3000.0, touchpoint_count=50, avg_weight=0.3)
        ]

        # Mock campaigns query
        mock_campaigns_result = MagicMock()
        mock_campaigns_result.scalar.return_value = 5

        mock_db.execute.side_effect = [
            mock_revenue_result,
            mock_revenue_result,
            mock_attr_result,
            mock_attr_result,
            mock_channels_result,
            mock_campaigns_result
        ]

        metrics = await dashboard_service.get_overview_metrics(
            organization_id="org1"
        )

        assert "total_revenue" in metrics
        assert metrics["total_revenue"].value == 10000.0
        assert "total_conversions" in metrics
        assert "attributed_revenue" in metrics
        assert "top_channels" in metrics
        assert len(metrics["top_channels"]) == 2

    @pytest.mark.asyncio
    async def test_get_total_revenue(self, dashboard_service, mock_db):
        """Test getting total revenue metric."""
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [10000.0, 8000.0]
        mock_db.execute.return_value = mock_result

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date

        metric = await dashboard_service._get_total_revenue(
            "org1", start_date, end_date, prev_start, prev_end
        )

        assert isinstance(metric, DashboardMetric)
        assert metric.value == 10000.0
        assert metric.previous_value == 8000.0
        assert metric.change_pct == 25.0  # (10000-8000)/8000 * 100


class TestAttributionReports:
    """Tests for attribution reports."""

    @pytest.mark.asyncio
    async def test_get_attribution_report(self, dashboard_service, mock_db):
        """Test getting attribution report."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                channel="google",
                total_attributed=5000.0,
                total_cost=2000.0,
                attribution_count=100,
                avg_weight=0.5,
                avg_time_to_conversion=48.0
            ),
            MagicMock(
                channel="facebook",
                total_attributed=3000.0,
                total_cost=1500.0,
                attribution_count=50,
                avg_weight=0.3,
                avg_time_to_conversion=72.0
            )
        ]
        mock_db.execute.return_value = mock_result

        report = await dashboard_service.get_attribution_report(
            organization_id="org1",
            model_type=AttributionModelType.LAST_TOUCH,
            group_by="channel"
        )

        assert report["model_type"] == "last_touch"
        assert report["group_by"] == "channel"
        assert len(report["data"]) == 2
        assert report["summary"]["total_attributed_revenue"] == 8000.0

    @pytest.mark.asyncio
    async def test_get_attribution_comparison(self, dashboard_service, mock_db):
        """Test comparing attribution models."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(channel="google", total_attributed=5000.0),
            MagicMock(channel="facebook", total_attributed=3000.0)
        ]
        mock_db.execute.return_value = mock_result

        comparison = await dashboard_service.get_attribution_comparison(
            organization_id="org1"
        )

        assert "models" in comparison
        assert "first_touch" in comparison["models"]
        assert "last_touch" in comparison["models"]
        assert "linear" in comparison["models"]


class TestROIReports:
    """Tests for ROI reports."""

    @pytest.mark.asyncio
    async def test_get_roi_report(self, dashboard_service, mock_db):
        """Test getting ROI report."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                dimension="google",
                total_cost=2000.0,
                total_attributed=5000.0,
                conversions=50
            ),
            MagicMock(
                dimension="facebook",
                total_cost=1500.0,
                total_attributed=3000.0,
                conversions=30
            )
        ]
        mock_db.execute.return_value = mock_result

        report = await dashboard_service.get_roi_report(
            organization_id="org1",
            group_by="channel"
        )

        assert "summary" in report
        assert "data" in report
        assert len(report["data"]) == 2

        # Check ROI calculation
        google_data = next(d for d in report["data"] if d["dimension"] == "google")
        assert google_data["roi"] == 1.5  # (5000-2000)/2000
        assert google_data["roas"] == 2.5  # 5000/2000
        assert google_data["cpa"] == 40.0  # 2000/50


class TestTimeSeries:
    """Tests for time-series analytics."""

    @pytest.mark.asyncio
    async def test_get_time_series_revenue(self, dashboard_service, mock_db):
        """Test getting revenue time series."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(timestamp=datetime.utcnow() - timedelta(days=2), value=1000.0),
            MagicMock(timestamp=datetime.utcnow() - timedelta(days=1), value=1200.0),
            MagicMock(timestamp=datetime.utcnow(), value=1100.0)
        ]
        mock_db.execute.return_value = mock_result

        series = await dashboard_service.get_time_series(
            organization_id="org1",
            metric="revenue",
            granularity="day"
        )

        assert len(series) == 3
        assert all(isinstance(point, TimeSeriesPoint) for point in series)
        assert series[0].value == 1000.0

    @pytest.mark.asyncio
    async def test_get_time_series_conversions(self, dashboard_service, mock_db):
        """Test getting conversions time series."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(timestamp=datetime.utcnow() - timedelta(days=1), value=10),
            MagicMock(timestamp=datetime.utcnow(), value=15)
        ]
        mock_db.execute.return_value = mock_result

        series = await dashboard_service.get_time_series(
            organization_id="org1",
            metric="conversions",
            granularity="day"
        )

        assert len(series) == 2

    @pytest.mark.asyncio
    async def test_get_time_series_invalid_metric(self, dashboard_service, mock_db):
        """Test getting time series with invalid metric."""
        series = await dashboard_service.get_time_series(
            organization_id="org1",
            metric="invalid_metric",
            granularity="day"
        )

        assert len(series) == 0


class TestConversionFunnel:
    """Tests for conversion funnel."""

    @pytest.mark.asyncio
    async def test_get_conversion_funnel(self, dashboard_service, mock_db):
        """Test getting conversion funnel."""
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [
            1000,  # impressions
            500,   # clicks
            400,   # landing page views
            200,   # add to carts
            100,   # checkouts
            50     # purchases
        ]
        mock_db.execute.return_value = mock_result

        funnel = await dashboard_service.get_conversion_funnel(
            organization_id="org1"
        )

        assert "stages" in funnel
        assert len(funnel["stages"]) == 6
        assert funnel["stages"][0]["stage"] == "impressions"
        assert funnel["stages"][0]["count"] == 1000
        assert funnel["stages"][-1]["stage"] == "purchases"
        assert funnel["stages"][-1]["count"] == 50
        assert funnel["overall_conversion_rate"] == 5.0  # 50/1000 * 100


class TestCustomerJourney:
    """Tests for customer journey analytics."""

    @pytest.mark.asyncio
    async def test_get_customer_journey_metrics(self, dashboard_service, mock_db):
        """Test getting customer journey metrics."""
        # Mock avg touchpoints query
        mock_touchpoints_result = MagicMock()
        mock_touchpoints_result.scalar.return_value = 3.5

        # Mock avg time to conversion query
        mock_time_result = MagicMock()
        mock_time_result.scalar.return_value = 72.0

        # Mock touchpoint distribution query
        mock_dist_result = MagicMock()
        mock_dist_result.all.return_value = [
            MagicMock(touchpoint_type="paid_search", count=100),
            MagicMock(touchpoint_type="email", count=50),
            MagicMock(touchpoint_type="organic_search", count=75)
        ]

        mock_db.execute.side_effect = [
            mock_touchpoints_result,
            mock_time_result,
            mock_dist_result
        ]

        metrics = await dashboard_service.get_customer_journey_metrics(
            organization_id="org1"
        )

        assert "metrics" in metrics
        assert metrics["metrics"]["avg_touchpoints_per_conversion"] == 3.5
        assert metrics["metrics"]["avg_time_to_conversion_hours"] == 72.0
        assert metrics["metrics"]["avg_time_to_conversion_days"] == 3.0
        assert "touchpoint_distribution" in metrics


class TestExport:
    """Tests for report export."""

    @pytest.mark.asyncio
    async def test_export_attribution_report(self, dashboard_service, mock_db):
        """Test exporting attribution report."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                channel="google",
                total_attributed=5000.0,
                total_cost=2000.0,
                attribution_count=100,
                avg_weight=0.5,
                avg_time_to_conversion=48.0
            )
        ]
        mock_db.execute.return_value = mock_result

        export = await dashboard_service.export_report(
            organization_id="org1",
            report_type="attribution",
            format="json"
        )

        assert export["format"] == "json"
        assert "data" in export

    @pytest.mark.asyncio
    async def test_export_roi_report(self, dashboard_service, mock_db):
        """Test exporting ROI report."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(
                dimension="google",
                total_cost=2000.0,
                total_attributed=5000.0,
                conversions=50
            )
        ]
        mock_db.execute.return_value = mock_result

        export = await dashboard_service.export_report(
            organization_id="org1",
            report_type="roi",
            format="json"
        )

        assert export["format"] == "json"
        assert "data" in export

    @pytest.mark.asyncio
    async def test_export_invalid_report_type(self, dashboard_service, mock_db):
        """Test exporting invalid report type."""
        export = await dashboard_service.export_report(
            organization_id="org1",
            report_type="invalid",
            format="json"
        )

        assert export["data"] == {}


class TestDashboardMetric:
    """Tests for DashboardMetric dataclass."""

    def test_metric_creation(self):
        """Test creating a dashboard metric."""
        metric = DashboardMetric(
            name="Total Revenue",
            value=10000.0,
            previous_value=8000.0,
            change_pct=25.0,
            unit="USD"
        )

        assert metric.name == "Total Revenue"
        assert metric.value == 10000.0
        assert metric.previous_value == 8000.0
        assert metric.change_pct == 25.0
        assert metric.unit == "USD"

    def test_metric_without_comparison(self):
        """Test creating a metric without comparison."""
        metric = DashboardMetric(
            name="Active Campaigns",
            value=5,
            unit="count"
        )

        assert metric.value == 5
        assert metric.previous_value is None
        assert metric.change_pct is None


class TestTimeSeriesPoint:
    """Tests for TimeSeriesPoint dataclass."""

    def test_point_creation(self):
        """Test creating a time series point."""
        timestamp = datetime.utcnow()
        point = TimeSeriesPoint(
            timestamp=timestamp,
            value=1000.0,
            dimensions={"channel": "google"}
        )

        assert point.timestamp == timestamp
        assert point.value == 1000.0
        assert point.dimensions == {"channel": "google"}

    def test_point_without_dimensions(self):
        """Test creating a point without dimensions."""
        timestamp = datetime.utcnow()
        point = TimeSeriesPoint(
            timestamp=timestamp,
            value=500.0
        )

        assert point.dimensions is None
