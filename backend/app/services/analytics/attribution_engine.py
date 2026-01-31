"""
Attribution Engine for multi-touch attribution analysis.

Implements various attribution models including:
- First-touch attribution
- Last-touch attribution
- Linear attribution
- Time-decay attribution
- Position-based (U-shaped) attribution
- Data-driven attribution
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ...models.attribution import (
    Attribution, AttributionModelType, AttributionStatus, AttributionModelConfig
)
from ...models.attribution_touchpoint import AttributionTouchpoint, TouchpointType
from ...models.conversion_event import ConversionEvent, ConversionStatus

logger = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Result of an attribution calculation."""
    touchpoint_id: str
    conversion_event_id: str
    model_type: AttributionModelType
    weight: float
    attributed_value: float
    position: int
    total_touchpoints: int
    hours_to_conversion: float
    confidence_score: float


class AttributionEngine:
    """
    Attribution Engine for multi-touch attribution analysis.

    Calculates attribution weights for touchpoints based on various
    attribution models and stores the results for reporting.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the Attribution Engine.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db

    # ============== Attribution Model Calculations ==============

    async def calculate_first_touch_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float
    ) -> List[AttributionResult]:
        """
        Calculate first-touch attribution.

        100% of credit goes to the first touchpoint.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        results = []
        total = len(touchpoints)

        for i, tp in enumerate(touchpoints):
            weight = 1.0 if i == 0 else 0.0
            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp,
                touchpoints[-1].touchpoint_timestamp if touchpoints else None
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.FIRST_TOUCH,
                weight=weight,
                attributed_value=conversion_value * weight,
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    async def calculate_last_touch_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float
    ) -> List[AttributionResult]:
        """
        Calculate last-touch attribution.

        100% of credit goes to the last touchpoint.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        results = []
        total = len(touchpoints)

        for i, tp in enumerate(touchpoints):
            weight = 1.0 if i == total - 1 else 0.0
            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp,
                touchpoints[-1].touchpoint_timestamp
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.LAST_TOUCH,
                weight=weight,
                attributed_value=conversion_value * weight,
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    async def calculate_linear_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float
    ) -> List[AttributionResult]:
        """
        Calculate linear attribution.

        Equal credit is distributed among all touchpoints.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        results = []
        total = len(touchpoints)
        weight = 1.0 / total

        for i, tp in enumerate(touchpoints):
            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp,
                touchpoints[-1].touchpoint_timestamp
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.LINEAR,
                weight=weight,
                attributed_value=conversion_value * weight,
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    async def calculate_time_decay_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float,
        half_life_days: float = 7.0
    ) -> List[AttributionResult]:
        """
        Calculate time-decay attribution.

        Credit increases exponentially as touchpoints get closer to conversion.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.
            half_life_days: Number of days for weight to decay by half.

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        if len(touchpoints) == 1:
            return await self.calculate_linear_attribution(touchpoints, conversion_value)

        results = []
        total = len(touchpoints)
        conversion_time = touchpoints[-1].touchpoint_timestamp

        # Calculate decay weights
        weights = []
        for tp in touchpoints:
            hours_before = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp, conversion_time
            )
            days_before = hours_before / 24.0
            # Exponential decay: weight = 2^(-days/half_life)
            weight = 2 ** (-days_before / half_life_days)
            weights.append(weight)

        # Normalize weights to sum to 1
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        for i, (tp, weight) in enumerate(zip(touchpoints, normalized_weights)):
            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp, conversion_time
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.TIME_DECAY,
                weight=weight,
                attributed_value=conversion_value * weight,
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    async def calculate_position_based_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float,
        first_touch_weight: float = 0.4,
        last_touch_weight: float = 0.4
    ) -> List[AttributionResult]:
        """
        Calculate position-based (U-shaped) attribution.

        First and last touchpoints get specified weights,
        middle touchpoints share the remainder equally.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.
            first_touch_weight: Weight for first touchpoint (default 40%).
            last_touch_weight: Weight for last touchpoint (default 40%).

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        results = []
        total = len(touchpoints)
        conversion_time = touchpoints[-1].touchpoint_timestamp

        if total == 1:
            weight = 1.0
        elif total == 2:
            # Split evenly between first and last
            weight_first = 0.5
            weight_last = 0.5
        else:
            middle_weight = (1.0 - first_touch_weight - last_touch_weight) / (total - 2)

        for i, tp in enumerate(touchpoints):
            if total == 1:
                weight = 1.0
            elif total == 2:
                weight = weight_first if i == 0 else weight_last
            else:
                if i == 0:
                    weight = first_touch_weight
                elif i == total - 1:
                    weight = last_touch_weight
                else:
                    weight = middle_weight

            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp, conversion_time
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.POSITION_BASED,
                weight=weight,
                attributed_value=conversion_value * weight,
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    async def calculate_w_shaped_attribution(
        self,
        touchpoints: List[AttributionTouchpoint],
        conversion_value: float
    ) -> List[AttributionResult]:
        """
        Calculate W-shaped attribution.

        First touch, lead conversion, and last touch each get 30%,
        remaining 10% distributed among middle touchpoints.

        Args:
            touchpoints: List of touchpoints in chronological order.
            conversion_value: Total conversion value.

        Returns:
            List of attribution results.
        """
        if not touchpoints:
            return []

        results = []
        total = len(touchpoints)
        conversion_time = touchpoints[-1].touchpoint_timestamp

        if total == 1:
            weights = [1.0]
        elif total == 2:
            weights = [0.5, 0.5]
        elif total == 3:
            weights = [0.333, 0.333, 0.333]
        else:
            # W-shape: first, middle, last get 30% each
            middle_idx = total // 2
            weights = []
            remaining = 0.1 / (total - 3) if total > 3 else 0

            for i in range(total):
                if i == 0 or i == middle_idx or i == total - 1:
                    weights.append(0.3)
                else:
                    weights.append(remaining)

        for i, tp in enumerate(touchpoints):
            hours_to_conv = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp, conversion_time
            )

            results.append(AttributionResult(
                touchpoint_id=tp.id,
                conversion_event_id=tp.conversion_event_id,
                model_type=AttributionModelType.W_SHAPED,
                weight=weights[i],
                attributed_value=conversion_value * weights[i],
                position=i + 1,
                total_touchpoints=total,
                hours_to_conversion=hours_to_conv,
                confidence_score=1.0
            ))

        return results

    # ============== Main Attribution Processing ==============

    async def process_conversion(
        self,
        conversion_event: ConversionEvent,
        model_types: List[AttributionModelType] = None,
        config: AttributionModelConfig = None
    ) -> Dict[AttributionModelType, List[AttributionResult]]:
        """
        Process a conversion event and calculate attributions.

        Args:
            conversion_event: The conversion event to attribute.
            model_types: List of attribution models to apply.
            config: Optional model configuration.

        Returns:
            Dictionary mapping model types to attribution results.
        """
        if model_types is None:
            model_types = [
                AttributionModelType.FIRST_TOUCH,
                AttributionModelType.LAST_TOUCH,
                AttributionModelType.LINEAR,
                AttributionModelType.TIME_DECAY,
                AttributionModelType.POSITION_BASED,
            ]

        # Get touchpoints for this conversion
        touchpoints = await self._get_touchpoints_for_conversion(conversion_event)

        if not touchpoints:
            logger.warning(f"No touchpoints found for conversion {conversion_event.id}")
            conversion_event.status = ConversionStatus.EXCLUDED
            await self.db.commit()
            return {}

        # Update conversion event
        conversion_event.attributed_touchpoint_count = len(touchpoints)
        conversion_event.status = ConversionStatus.PROCESSING

        results = {}

        for model_type in model_types:
            try:
                model_results = await self._calculate_attribution_for_model(
                    model_type, touchpoints, conversion_event, config
                )
                results[model_type] = model_results

                # Store attributions in database
                await self._store_attributions(model_results, model_type, config)

            except Exception as e:
                logger.error(f"Error calculating {model_type} attribution: {e}")
                continue

        # Update conversion status
        conversion_event.status = ConversionStatus.ATTRIBUTED
        conversion_event.processed_at = datetime.utcnow()
        await self.db.commit()

        return results

    async def _calculate_attribution_for_model(
        self,
        model_type: AttributionModelType,
        touchpoints: List[AttributionTouchpoint],
        conversion_event: ConversionEvent,
        config: AttributionModelConfig = None
    ) -> List[AttributionResult]:
        """Calculate attribution for a specific model type."""
        conversion_value = conversion_event.conversion_value

        if model_type == AttributionModelType.FIRST_TOUCH:
            return await self.calculate_first_touch_attribution(touchpoints, conversion_value)

        elif model_type == AttributionModelType.LAST_TOUCH:
            return await self.calculate_last_touch_attribution(touchpoints, conversion_value)

        elif model_type == AttributionModelType.LINEAR:
            return await self.calculate_linear_attribution(touchpoints, conversion_value)

        elif model_type == AttributionModelType.TIME_DECAY:
            half_life = 7.0
            if config and config.parameters:
                half_life = config.parameters.get("time_decay_half_life_days", 7.0)
            return await self.calculate_time_decay_attribution(
                touchpoints, conversion_value, half_life
            )

        elif model_type == AttributionModelType.POSITION_BASED:
            first_weight = 0.4
            last_weight = 0.4
            if config and config.parameters:
                weights = config.parameters.get("position_weights", {})
                first_weight = weights.get("first", 0.4)
                last_weight = weights.get("last", 0.4)
            return await self.calculate_position_based_attribution(
                touchpoints, conversion_value, first_weight, last_weight
            )

        elif model_type == AttributionModelType.W_SHAPED:
            return await self.calculate_w_shaped_attribution(touchpoints, conversion_value)

        else:
            # Default to linear for unsupported models
            logger.warning(f"Model type {model_type} not fully implemented, using linear")
            return await self.calculate_linear_attribution(touchpoints, conversion_value)

    async def _get_touchpoints_for_conversion(
        self,
        conversion_event: ConversionEvent
    ) -> List[AttributionTouchpoint]:
        """Get touchpoints associated with a conversion event."""
        # Query touchpoints within lookback window
        lookback_start = conversion_event.conversion_timestamp - timedelta(
            days=conversion_event.lookback_window_days
        )

        query = select(AttributionTouchpoint).where(
            and_(
                AttributionTouchpoint.organization_id == conversion_event.organization_id,
                AttributionTouchpoint.customer_id == conversion_event.customer_id,
                AttributionTouchpoint.touchpoint_timestamp >= lookback_start,
                AttributionTouchpoint.touchpoint_timestamp <= conversion_event.conversion_timestamp,
                AttributionTouchpoint.status != "excluded"
            )
        ).order_by(AttributionTouchpoint.touchpoint_timestamp)

        result = await self.db.execute(query)
        touchpoints = result.scalars().all()

        # Update touchpoint positions and link to conversion
        for i, tp in enumerate(touchpoints):
            tp.position_in_journey = i + 1
            tp.time_to_conversion_hours = self._calculate_hours_to_conversion(
                tp.touchpoint_timestamp,
                conversion_event.conversion_timestamp
            )
            tp.conversion_event_id = conversion_event.id

        return list(touchpoints)

    async def _store_attributions(
        self,
        results: List[AttributionResult],
        model_type: AttributionModelType,
        config: AttributionModelConfig = None
    ) -> None:
        """Store attribution results in the database."""
        for result in results:
            # Check if attribution already exists
            query = select(Attribution).where(
                and_(
                    Attribution.conversion_event_id == result.conversion_event_id,
                    Attribution.touchpoint_id == result.touchpoint_id,
                    Attribution.model_type == model_type
                )
            )
            existing = await self.db.execute(query)
            existing_attribution = existing.scalar_one_or_none()

            if existing_attribution:
                # Update existing
                existing_attribution.weight = result.weight
                existing_attribution.attributed_value = result.attributed_value
                existing_attribution.touchpoint_position = result.position
                existing_attribution.total_touchpoints = result.total_touchpoints
                existing_attribution.hours_to_conversion = result.hours_to_conversion
                existing_attribution.confidence_score = result.confidence_score
                existing_attribution.status = AttributionStatus.RECALCULATED
                existing_attribution.calculated_at = datetime.utcnow()
            else:
                # Create new
                attribution = Attribution(
                    organization_id=result.conversion_event_id,  # Will be set properly below
                    conversion_event_id=result.conversion_event_id,
                    touchpoint_id=result.touchpoint_id,
                    model_type=model_type,
                    weight=result.weight,
                    attributed_value=result.attributed_value,
                    model_parameters=config.parameters if config else {},
                    touchpoint_position=result.position,
                    total_touchpoints=result.total_touchpoints,
                    hours_to_conversion=result.hours_to_conversion,
                    confidence_score=result.confidence_score,
                    status=AttributionStatus.CALCULATED,
                    calculated_at=datetime.utcnow()
                )
                self.db.add(attribution)

        await self.db.flush()

    def _calculate_hours_to_conversion(
        self,
        touchpoint_time: datetime,
        conversion_time: Optional[datetime]
    ) -> float:
        """Calculate hours between touchpoint and conversion."""
        if not touchpoint_time or not conversion_time:
            return 0.0
        delta = conversion_time - touchpoint_time
        return delta.total_seconds() / 3600.0

    # ============== Batch Processing ==============

    async def process_pending_conversions(
        self,
        organization_id: str,
        batch_size: int = 100
    ) -> int:
        """
        Process all pending conversions for an organization.

        Args:
            organization_id: Organization ID to process.
            batch_size: Number of conversions to process per batch.

        Returns:
            Number of conversions processed.
        """
        query = select(ConversionEvent).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.status == ConversionStatus.PENDING
            )
        ).limit(batch_size)

        result = await self.db.execute(query)
        conversions = result.scalars().all()

        processed = 0
        for conversion in conversions:
            try:
                await self.process_conversion(conversion)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing conversion {conversion.id}: {e}")
                conversion.status = ConversionStatus.FAILED
                conversion.error_message = str(e)
                await self.db.commit()

        return processed

    # ============== Reporting ==============

    async def get_attribution_summary(
        self,
        organization_id: str,
        model_type: AttributionModelType,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get attribution summary by channel.

        Args:
            organization_id: Organization ID.
            model_type: Attribution model type.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            Attribution summary by channel.
        """
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
                Attribution.model_type == model_type
            )
        ).group_by(AttributionTouchpoint.channel)

        if start_date:
            query = query.where(Attribution.calculated_at >= start_date)
        if end_date:
            query = query.where(Attribution.calculated_at <= end_date)

        result = await self.db.execute(query)
        rows = result.all()

        summary = {
            "model_type": model_type.value,
            "channels": {},
            "total_attributed": 0.0,
            "total_touchpoints": 0
        }

        for row in rows:
            channel = row.channel
            summary["channels"][channel] = {
                "total_attributed": float(row.total_attributed or 0),
                "touchpoint_count": row.touchpoint_count,
                "avg_weight": float(row.avg_weight or 0)
            }
            summary["total_attributed"] += float(row.total_attributed or 0)
            summary["total_touchpoints"] += row.touchpoint_count

        return summary
