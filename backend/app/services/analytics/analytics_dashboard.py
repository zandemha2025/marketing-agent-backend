"""
Analytics Dashboard Service.

Provides comprehensive analytics and reporting capabilities for:
- Campaign performance metrics
- Attribution analysis
- ROI reporting
- Channel effectiveness
- Conversion funnels
- Time-series analytics
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from enum import Enum

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, case, text
from sqlalchemy.dialects import postgresql

from ...models.attribution import Attribution, AttributionModelType
from ...models.attribution_touchpoint import AttributionTouchpoint, TouchpointType
from ...models.conversion_event import ConversionEvent, ConversionType, ConversionStatus
from ...models.marketing_mix_model import MarketingMixModel, MMMChannel
from ...models.campaign import Campaign
from ...models.customer_event import CustomerEvent, EventType

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetric:
    """Single dashboard metric."""
    name: str
    value: float
    previous_value: Optional[float] = None
    change_pct: Optional[float] = None
    unit: str = ""


@dataclass
class TimeSeriesPoint:
    """Single time-series data point."""
    timestamp: datetime
    value: float
    dimensions: Optional[Dict[str, Any]] = None


class AnalyticsDashboardService:
    """
    Analytics Dashboard Service.

    Provides comprehensive analytics capabilities for marketing performance
    reporting, ROI analysis, and attribution insights.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the Analytics Dashboard Service.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db

    # ============== Overview Metrics ==============

    async def get_overview_metrics(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get high-level overview metrics for the dashboard.

        Args:
            organization_id: Organization ID.
            start_date: Start date for metrics.
            end_date: End date for metrics.

        Returns:
            Dictionary of overview metrics.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Previous period for comparison
        period_length = end_date - start_date
        prev_start = start_date - period_length
        prev_end = start_date

        metrics = {}

        # Revenue metrics
        metrics["total_revenue"] = await self._get_total_revenue(
            organization_id, start_date, end_date, prev_start, prev_end
        )

        # Conversion metrics
        metrics["total_conversions"] = await self._get_total_conversions(
            organization_id, start_date, end_date, prev_start, prev_end
        )

        # Attribution metrics
        metrics["attributed_revenue"] = await self._get_attributed_revenue(
            organization_id, start_date, end_date, prev_start, prev_end
        )

        # Channel performance
        metrics["top_channels"] = await self._get_top_channels(
            organization_id, start_date, end_date
        )

        # Campaign performance
        metrics["active_campaigns"] = await self._get_active_campaigns_count(
            organization_id, start_date, end_date
        )

        return metrics

    async def _get_total_revenue(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        prev_start: datetime,
        prev_end: datetime
    ) -> DashboardMetric:
        """Get total revenue with comparison."""
        # Current period
        query = select(func.sum(ConversionEvent.conversion_value)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date,
                ConversionEvent.status == ConversionStatus.ATTRIBUTED
            )
        )
        result = await self.db.execute(query)
        current = result.scalar() or 0

        # Previous period
        query = select(func.sum(ConversionEvent.conversion_value)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= prev_start,
                ConversionEvent.conversion_timestamp <= prev_end,
                ConversionEvent.status == ConversionStatus.ATTRIBUTED
            )
        )
        result = await self.db.execute(query)
        previous = result.scalar() or 0

        change_pct = ((current - previous) / previous * 100) if previous > 0 else 0

        return DashboardMetric(
            name="Total Revenue",
            value=float(current),
            previous_value=float(previous),
            change_pct=float(change_pct),
            unit="USD"
        )

    async def _get_total_conversions(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        prev_start: datetime,
        prev_end: datetime
    ) -> DashboardMetric:
        """Get total conversions with comparison."""
        # Current period
        query = select(func.count(ConversionEvent.id)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date,
                ConversionEvent.status == ConversionStatus.ATTRIBUTED
            )
        )
        result = await self.db.execute(query)
        current = result.scalar() or 0

        # Previous period
        query = select(func.count(ConversionEvent.id)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= prev_start,
                ConversionEvent.conversion_timestamp <= prev_end,
                ConversionEvent.status == ConversionStatus.ATTRIBUTED
            )
        )
        result = await self.db.execute(query)
        previous = result.scalar() or 0

        change_pct = ((current - previous) / previous * 100) if previous > 0 else 0

        return DashboardMetric(
            name="Total Conversions",
            value=float(current),
            previous_value=float(previous),
            change_pct=float(change_pct),
            unit="count"
        )

    async def _get_attributed_revenue(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        prev_start: datetime,
        prev_end: datetime
    ) -> DashboardMetric:
        """Get attributed revenue with comparison."""
        # Current period
        query = select(func.sum(Attribution.attributed_value)).where(
            and_(
                Attribution.organization_id == organization_id,
                Attribution.calculated_at >= start_date,
                Attribution.calculated_at <= end_date
            )
        )
        result = await self.db.execute(query)
        current = result.scalar() or 0

        # Previous period
        query = select(func.sum(Attribution.attributed_value)).where(
            and_(
                Attribution.organization_id == organization_id,
                Attribution.calculated_at >= prev_start,
                Attribution.calculated_at <= prev_end
            )
        )
        result = await self.db.execute(query)
        previous = result.scalar() or 0

        change_pct = ((current - previous) / previous * 100) if previous > 0 else 0

        return DashboardMetric(
            name="Attributed Revenue",
            value=float(current),
            previous_value=float(previous),
            change_pct=float(change_pct),
            unit="USD"
        )

    async def _get_top_channels(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top performing channels."""
        query = select(
            AttributionTouchpoint.channel,
            func.sum(Attribution.attributed_value).label("total_attributed"),
            func.count(Attribution.id).label("touchpoint_count"),
            func.avg(Attribution.weight).label("avg_weight")
        ).join(
            AttributionTouchpoint,
            Attribution.touchpoint_id == AttributionTouchpoint.id
        ).where(
            and_(
                Attribution.organization_id == organization_id,
                Attribution.calculated_at >= start_date,
                Attribution.calculated_at <= end_date
            )
        ).group_by(
            AttributionTouchpoint.channel
        ).order_by(
            desc("total_attributed")
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "channel": row.channel,
                "attributed_revenue": float(row.total_attributed or 0),
                "touchpoint_count": row.touchpoint_count,
                "avg_weight": float(row.avg_weight or 0)
            }
            for row in rows
        ]

    async def _get_active_campaigns_count(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> DashboardMetric:
        """Get count of active campaigns."""
        query = select(func.count(Campaign.id)).where(
            and_(
                Campaign.organization_id == organization_id,
                Campaign.status == "active"
            )
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0

        return DashboardMetric(
            name="Active Campaigns",
            value=float(count),
            unit="count"
        )

    # ============== Attribution Reports ==============

    async def get_attribution_report(
        self,
        organization_id: str,
        model_type: AttributionModelType,
        start_date: datetime = None,
        end_date: datetime = None,
        group_by: str = "channel"
    ) -> Dict[str, Any]:
        """
        Get detailed attribution report.

        Args:
            organization_id: Organization ID.
            model_type: Attribution model type.
            start_date: Start date filter.
            end_date: End date filter.
            group_by: Grouping dimension (channel, campaign, touchpoint_type).

        Returns:
            Attribution report data.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Base query
        if group_by == "channel":
            group_col = AttributionTouchpoint.channel
        elif group_by == "campaign":
            group_col = AttributionTouchpoint.campaign_name
        else:
            group_col = AttributionTouchpoint.touchpoint_type

        query = select(
            group_col,
            func.sum(Attribution.attributed_value).label("total_attributed"),
            func.sum(AttributionTouchpoint.cost).label("total_cost"),
            func.count(Attribution.id).label("attribution_count"),
            func.avg(Attribution.weight).label("avg_weight"),
            func.avg(Attribution.hours_to_conversion).label("avg_time_to_conversion")
        ).join(
            AttributionTouchpoint,
            Attribution.touchpoint_id == AttributionTouchpoint.id
        ).where(
            and_(
                Attribution.organization_id == organization_id,
                Attribution.model_type == model_type,
                Attribution.calculated_at >= start_date,
                Attribution.calculated_at <= end_date
            )
        ).group_by(group_col).order_by(desc("total_attributed"))

        result = await self.db.execute(query)
        rows = result.all()

        report_data = []
        total_attributed = 0
        total_cost = 0

        for row in rows:
            attributed = float(row.total_attributed or 0)
            cost = float(row.total_cost or 0)
            roi = ((attributed - cost) / cost * 100) if cost > 0 else 0
            roas = (attributed / cost) if cost > 0 else 0

            report_data.append({
                "dimension": row[0],
                "attributed_revenue": attributed,
                "cost": cost,
                "attribution_count": row.attribution_count,
                "avg_weight": float(row.avg_weight or 0),
                "avg_time_to_conversion_hours": float(row.avg_time_to_conversion or 0),
                "roi_pct": float(roi),
                "roas": float(roas)
            })

            total_attributed += attributed
            total_cost += cost

        return {
            "model_type": model_type.value,
            "group_by": group_by,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_attributed_revenue": total_attributed,
                "total_cost": total_cost,
                "overall_roi_pct": ((total_attributed - total_cost) / total_cost * 100) if total_cost > 0 else 0,
                "overall_roas": (total_attributed / total_cost) if total_cost > 0 else 0
            },
            "data": report_data
        }

    async def get_attribution_comparison(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Compare attribution across different models.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Comparison of attribution models.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        models = [
            AttributionModelType.FIRST_TOUCH,
            AttributionModelType.LAST_TOUCH,
            AttributionModelType.LINEAR,
            AttributionModelType.TIME_DECAY,
            AttributionModelType.POSITION_BASED
        ]

        comparison = {}

        for model_type in models:
            query = select(
                AttributionTouchpoint.channel,
                func.sum(Attribution.attributed_value).label("total_attributed")
            ).join(
                AttributionTouchpoint,
                Attribution.touchpoint_id == AttributionTouchpoint.id
            ).where(
                and_(
                    Attribution.organization_id == organization_id,
                    Attribution.model_type == model_type,
                    Attribution.calculated_at >= start_date,
                    Attribution.calculated_at <= end_date
                )
            ).group_by(AttributionTouchpoint.channel)

            result = await self.db.execute(query)
            rows = result.all()

            comparison[model_type.value] = {
                row.channel: float(row.total_attributed or 0)
                for row in rows
            }

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "models": comparison
        }

    # ============== ROI Reports ==============

    async def get_roi_report(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        group_by: str = "channel"
    ) -> Dict[str, Any]:
        """
        Get ROI report by channel or campaign.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.
            group_by: Grouping dimension.

        Returns:
            ROI report data.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Group by dimension
        if group_by == "channel":
            group_col = AttributionTouchpoint.channel
        elif group_by == "campaign":
            group_col = AttributionTouchpoint.campaign_name
        else:
            group_col = AttributionTouchpoint.touchpoint_type

        # Aggregate by dimension
        query = select(
            group_col,
            func.sum(AttributionTouchpoint.cost).label("total_cost"),
            func.sum(Attribution.attributed_value).label("total_attributed"),
            func.count(func.distinct(Attribution.conversion_event_id)).label("conversions")
        ).join(
            Attribution,
            AttributionTouchpoint.id == Attribution.touchpoint_id,
            isouter=True
        ).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.touchpoint_timestamp >= start_date,
                AttributionTouchpoint.touchpoint_timestamp <= end_date
            )
        ).group_by(group_col)

        result = await self.db.execute(query)
        rows = result.all()

        roi_data = []
        total_cost = 0
        total_attributed = 0
        total_conversions = 0

        for row in rows:
            cost = float(row.total_cost or 0)
            attributed = float(row.total_attributed or 0)
            conversions = row.conversions or 0

            roi = ((attributed - cost) / cost) if cost > 0 else 0
            roas = (attributed / cost) if cost > 0 else 0
            cpa = (cost / conversions) if conversions > 0 else 0

            roi_data.append({
                "dimension": row[0],
                "spend": cost,
                "attributed_revenue": attributed,
                "conversions": conversions,
                "roi": float(roi),
                "roas": float(roas),
                "cpa": float(cpa)
            })

            total_cost += cost
            total_attributed += attributed
            total_conversions += conversions

        # Sort by ROI
        roi_data.sort(key=lambda x: x["roi"], reverse=True)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_spend": total_cost,
                "total_attributed_revenue": total_attributed,
                "total_conversions": total_conversions,
                "overall_roi": ((total_attributed - total_cost) / total_cost) if total_cost > 0 else 0,
                "overall_roas": (total_attributed / total_cost) if total_cost > 0 else 0,
                "overall_cpa": (total_cost / total_conversions) if total_conversions > 0 else 0
            },
            "data": roi_data
        }

    # ============== Time-Series Analytics ==============

    async def get_time_series(
        self,
        organization_id: str,
        metric: str,
        granularity: str = "day",
        start_date: datetime = None,
        end_date: datetime = None,
        dimensions: List[str] = None
    ) -> List[TimeSeriesPoint]:
        """
        Get time-series data for a metric.

        Args:
            organization_id: Organization ID.
            metric: Metric name (revenue, conversions, etc.).
            granularity: Time granularity (hour, day, week, month).
            start_date: Start date.
            end_date: End date.
            dimensions: Optional dimensions to group by.

        Returns:
            List of time-series points.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Determine time truncation
        if granularity == "hour":
            trunc_func = func.date_trunc("hour", ConversionEvent.conversion_timestamp)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", ConversionEvent.conversion_timestamp)
        elif granularity == "month":
            trunc_func = func.date_trunc("month", ConversionEvent.conversion_timestamp)
        else:  # day
            trunc_func = func.date_trunc("day", ConversionEvent.conversion_timestamp)

        # Build query based on metric
        if metric == "revenue":
            query = select(
                trunc_func.label("timestamp"),
                func.sum(ConversionEvent.conversion_value).label("value")
            ).where(
                and_(
                    ConversionEvent.organization_id == organization_id,
                    ConversionEvent.conversion_timestamp >= start_date,
                    ConversionEvent.conversion_timestamp <= end_date,
                    ConversionEvent.status == ConversionStatus.ATTRIBUTED
                )
            ).group_by("timestamp").order_by("timestamp")

        elif metric == "conversions":
            query = select(
                trunc_func.label("timestamp"),
                func.count(ConversionEvent.id).label("value")
            ).where(
                and_(
                    ConversionEvent.organization_id == organization_id,
                    ConversionEvent.conversion_timestamp >= start_date,
                    ConversionEvent.conversion_timestamp <= end_date,
                    ConversionEvent.status == ConversionStatus.ATTRIBUTED
                )
            ).group_by("timestamp").order_by("timestamp")

        elif metric == "attributed_revenue":
            query = select(
                func.date_trunc(granularity, Attribution.calculated_at).label("timestamp"),
                func.sum(Attribution.attributed_value).label("value")
            ).where(
                and_(
                    Attribution.organization_id == organization_id,
                    Attribution.calculated_at >= start_date,
                    Attribution.calculated_at <= end_date
                )
            ).group_by("timestamp").order_by("timestamp")

        else:
            return []

        result = await self.db.execute(query)
        rows = result.all()

        return [
            TimeSeriesPoint(
                timestamp=row.timestamp,
                value=float(row.value or 0)
            )
            for row in rows
        ]

    # ============== Conversion Funnel ==============

    async def get_conversion_funnel(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get conversion funnel analysis.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Funnel stages with conversion rates.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Define funnel stages
        stages = [
            ("impressions", EventType.AD_VIEW),
            ("clicks", EventType.AD_CLICK),
            ("landing_page_views", EventType.PAGE_VIEW),
            ("add_to_carts", EventType.ADD_TO_CART),
            ("checkouts", EventType.BEGIN_CHECKOUT),
            ("purchases", EventType.PURCHASE)
        ]

        funnel_data = []
        previous_count = None

        for stage_name, event_type in stages:
            query = select(func.count(CustomerEvent.id)).where(
                and_(
                    CustomerEvent.organization_id == organization_id,
                    CustomerEvent.event_type == event_type,
                    CustomerEvent.timestamp >= start_date,
                    CustomerEvent.timestamp <= end_date
                )
            )
            result = await self.db.execute(query)
            count = result.scalar() or 0

            conversion_rate = None
            if previous_count and previous_count > 0:
                conversion_rate = (count / previous_count) * 100

            funnel_data.append({
                "stage": stage_name,
                "count": count,
                "conversion_rate_from_previous": float(conversion_rate) if conversion_rate else None
            })

            previous_count = count

        # Calculate overall conversion rate
        if funnel_data and funnel_data[0]["count"] > 0:
            overall_rate = (funnel_data[-1]["count"] / funnel_data[0]["count"]) * 100
        else:
            overall_rate = 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "stages": funnel_data,
            "overall_conversion_rate": float(overall_rate)
        }

    # ============== Customer Journey Analytics ==============

    async def get_customer_journey_metrics(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get customer journey analytics.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Customer journey metrics.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Average touchpoints per conversion
        query = select(
            func.avg(ConversionEvent.attributed_touchpoint_count)
        ).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date,
                ConversionEvent.status == ConversionStatus.ATTRIBUTED
            )
        )
        result = await self.db.execute(query)
        avg_touchpoints = result.scalar() or 0

        # Average time to conversion
        query = select(
            func.avg(Attribution.hours_to_conversion)
        ).where(
            and_(
                Attribution.organization_id == organization_id,
                Attribution.calculated_at >= start_date,
                Attribution.calculated_at <= end_date
            )
        )
        result = await self.db.execute(query)
        avg_time_to_conversion = result.scalar() or 0

        # Journey stage distribution
        query = select(
            AttributionTouchpoint.touchpoint_type,
            func.count(AttributionTouchpoint.id).label("count")
        ).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.touchpoint_timestamp >= start_date,
                AttributionTouchpoint.touchpoint_timestamp <= end_date
            )
        ).group_by(AttributionTouchpoint.touchpoint_type)

        result = await self.db.execute(query)
        rows = result.all()

        touchpoint_distribution = {
            row.touchpoint_type.value if row.touchpoint_type else "unknown": row.count
            for row in rows
        }

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "metrics": {
                "avg_touchpoints_per_conversion": float(avg_touchpoints),
                "avg_time_to_conversion_hours": float(avg_time_to_conversion),
                "avg_time_to_conversion_days": float(avg_time_to_conversion / 24) if avg_time_to_conversion else 0
            },
            "touchpoint_distribution": touchpoint_distribution
        }

    # ============== Export ==============

    async def export_report(
        self,
        organization_id: str,
        report_type: str,
        start_date: datetime = None,
        end_date: datetime = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export a report in various formats.

        Args:
            organization_id: Organization ID.
            report_type: Type of report to export.
            start_date: Start date filter.
            end_date: End date filter.
            format: Export format (json, csv).

        Returns:
            Report data in requested format.
        """
        if report_type == "attribution":
            data = await self.get_attribution_report(
                organization_id, AttributionModelType.LAST_TOUCH, start_date, end_date
            )
        elif report_type == "roi":
            data = await self.get_roi_report(organization_id, start_date, end_date)
        elif report_type == "overview":
            data = await self.get_overview_metrics(organization_id, start_date, end_date)
        else:
            data = {}

        if format == "csv":
            # Convert to CSV format
            # This is a simplified version - full implementation would use pandas
            return {
                "format": "csv",
                "data": data  # Would be converted to CSV string
            }

        return {
            "format": "json",
            "data": data
        }
