"""
Profile Enrichment Service for the Customer Data Platform.

Provides data enrichment from external sources, computed traits calculation,
and customer segmentation capabilities.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from ...models.customer import Customer
from ...models.customer_event import CustomerEvent, EventType
from ...models.customer_segment import CustomerSegment, SegmentType, SegmentStatus
from ...models.segment_membership import SegmentMembership
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class ProfileEnricher:
    """
    Profile enrichment and segmentation service.

    Enriches customer profiles with external data and calculates
    computed traits for segmentation and personalization.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the profile enricher.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db
        self.settings = get_settings()

    # ============== External Data Enrichment ==============

    async def enrich_from_clearbit(self, email: str) -> Dict[str, Any]:
        """Enrich profile data from Clearbit.

        Args:
            email: Email address to enrich.

        Returns:
            Enrichment data from Clearbit.
        """
        if not self.settings.clearbit_api_key:
            logger.warning("Clearbit API key not configured")
            return {}

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://person.clearbit.com/v2/combined/find",
                    params={"email": email},
                    headers={"Authorization": f"Bearer {self.settings.clearbit_api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "person": data.get("person", {}),
                        "company": data.get("company", {}),
                        "enriched_at": datetime.utcnow().isoformat(),
                        "source": "clearbit"
                    }
                else:
                    logger.warning(f"Clearbit enrichment failed: {response.status_code}")
                    return {}

        except Exception as e:
            logger.error(f"Clearbit enrichment error: {e}")
            return {}

    async def enrich_from_zerobounce(self, email: str) -> Dict[str, Any]:
        """Enrich and validate email from ZeroBounce.

        Args:
            email: Email address to validate.

        Returns:
            Email validation and enrichment data.
        """
        if not self.settings.zerobounce_api_key:
            logger.warning("ZeroBounce API key not configured")
            return {}

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.zerobounce.net/v2/validate",
                    params={
                        "api_key": self.settings.zerobounce_api_key,
                        "email": email
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": data.get("status"),
                        "sub_status": data.get("sub_status"),
                        "domain": data.get("domain"),
                        "is_valid": data.get("status") == "valid",
                        "enriched_at": datetime.utcnow().isoformat(),
                        "source": "zerobounce"
                    }
                else:
                    logger.warning(f"ZeroBounce validation failed: {response.status_code}")
                    return {}

        except Exception as e:
            logger.error(f"ZeroBounce enrichment error: {e}")
            return {}

    async def enrich_firmographics(self, domain: str) -> Dict[str, Any]:
        """Enrich firmographic data from company domain.

        Args:
            domain: Company domain (e.g., 'example.com').

        Returns:
            Firmographic enrichment data.
        """
        # Try Clearbit first for company data
        if self.settings.clearbit_api_key:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://company.clearbit.com/v2/companies/find",
                        params={"domain": domain},
                        headers={"Authorization": f"Bearer {self.settings.clearbit_api_key}"},
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "name": data.get("name"),
                            "domain": data.get("domain"),
                            "industry": data.get("category", {}).get("industry"),
                            "sub_industry": data.get("category", {}).get("subIndustry"),
                            "employees": data.get("metrics", {}).get("employees"),
                            "annual_revenue": data.get("metrics", {}).get("annualRevenue"),
                            "raised": data.get("metrics", {}).get("raised"),
                            "location": {
                                "city": data.get("geo", {}).get("city"),
                                "state": data.get("geo", {}).get("state"),
                                "country": data.get("geo", {}).get("country"),
                            },
                            "tech_stack": data.get("tech", []),
                            "enriched_at": datetime.utcnow().isoformat(),
                            "source": "clearbit"
                        }

            except Exception as e:
                logger.error(f"Firmographic enrichment error: {e}")

        return {}

    # ============== Computed Traits ==============

    async def calculate_engagement_score(self, customer_id: str) -> float:
        """Calculate customer engagement score (0-100).

        Based on event frequency, recency, and diversity.

        Args:
            customer_id: Customer ID.

        Returns:
            Engagement score between 0 and 100.
        """
        # Get recent events (last 90 days)
        since = datetime.utcnow() - timedelta(days=90)

        result = await self.db.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.timestamp >= since
                )
            )
        )
        events = result.scalars().all()

        if not events:
            return 0.0

        # Calculate components
        event_count = len(events)
        unique_days = len(set(e.timestamp.date() for e in events))
        unique_event_types = len(set(e.event_type for e in events))

        # Recency score (higher for more recent activity)
        latest_event = max(e.timestamp for e in events)
        days_since_last = (datetime.utcnow() - latest_event).days
        recency_score = max(0, 30 - days_since_last) / 30  # 0-1

        # Frequency score
        frequency_score = min(event_count / 50, 1.0)  # Cap at 50 events

        # Diversity score
        diversity_score = min(unique_event_types / 10, 1.0)  # Cap at 10 types

        # Consistency score (active days / 30)
        consistency_score = min(unique_days / 30, 1.0)

        # Weighted combination
        score = (
            recency_score * 0.35 +
            frequency_score * 0.25 +
            diversity_score * 0.20 +
            consistency_score * 0.20
        ) * 100

        return round(score, 2)

    async def calculate_ltv(self, customer_id: str) -> float:
        """Calculate customer lifetime value.

        Args:
            customer_id: Customer ID.

        Returns:
            Estimated lifetime value.
        """
        # Get purchase events
        result = await self.db.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.event_type == EventType.PURCHASE
                )
            )
        )
        purchases = result.scalars().all()

        if not purchases:
            return 0.0

        total_value = sum(
            p.properties.get("total", p.properties.get("value", 0))
            for p in purchases
        )

        # Add predictive component based on engagement
        engagement = await self.calculate_engagement_score(customer_id)
        predicted_future = (engagement / 100) * total_value * 0.5

        return round(total_value + predicted_future, 2)

    async def calculate_churn_risk(self, customer_id: str) -> float:
        """Calculate churn risk score (0-1, higher = more likely to churn).

        Args:
            customer_id: Customer ID.

        Returns:
            Churn risk score between 0 and 1.
        """
        # Get customer
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return 1.0  # High risk if customer not found

        # Get recent events
        since = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.timestamp >= since
                )
            )
        )
        events = result.scalars().all()

        if not events:
            # No activity in 90 days = high churn risk
            return 0.9

        # Calculate risk factors
        latest_event = max(e.timestamp for e in events)
        days_since_last = (datetime.utcnow() - latest_event).days

        # Recency factor (exponential decay)
        recency_risk = min(days_since_last / 60, 1.0)  # Max at 60 days

        # Frequency factor
        event_count = len(events)
        frequency_risk = max(0, 1 - (event_count / 20))  # Low events = higher risk

        # Engagement trend
        engagement = await self.calculate_engagement_score(customer_id)
        engagement_risk = max(0, 1 - (engagement / 50))  # Below 50 engagement = risk

        # Combine factors (weighted)
        risk = (
            recency_risk * 0.5 +
            frequency_risk * 0.25 +
            engagement_risk * 0.25
        )

        return round(min(risk, 1.0), 2)

    async def calculate_recency(self, customer_id: str) -> int:
        """Calculate days since last activity.

        Args:
            customer_id: Customer ID.

        Returns:
            Days since last activity.
        """
        result = await self.db.execute(
            select(CustomerEvent.timestamp).where(
                CustomerEvent.customer_id == customer_id
            ).order_by(desc(CustomerEvent.timestamp)).limit(1)
        )
        last_event = result.scalar_one_or_none()

        if not last_event:
            return 999  # No activity

        return (datetime.utcnow() - last_event).days

    async def calculate_frequency(self, customer_id: str, days: int = 90) -> int:
        """Calculate event frequency over a period.

        Args:
            customer_id: Customer ID.
            days: Number of days to look back.

        Returns:
            Number of events in the period.
        """
        since = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(func.count(CustomerEvent.id)).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.timestamp >= since
                )
            )
        )
        return result.scalar() or 0

    async def calculate_monetary_value(self, customer_id: str) -> float:
        """Calculate total monetary value from purchases.

        Args:
            customer_id: Customer ID.

        Returns:
            Total purchase value.
        """
        result = await self.db.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.event_type == EventType.PURCHASE
                )
            )
        )
        purchases = result.scalars().all()

        total = sum(
            p.properties.get("total", p.properties.get("value", 0))
            for p in purchases
        )

        return round(total, 2)

    async def update_all_computed_traits(self, customer_id: str):
        """Update all computed traits for a customer.

        Args:
            customer_id: Customer ID.
        """
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            logger.warning(f"Customer {customer_id} not found for trait update")
            return

        # Calculate all traits
        computed_traits = customer.computed_traits or {}

        computed_traits.update({
            "engagement_score": await self.calculate_engagement_score(customer_id),
            "ltv": await self.calculate_ltv(customer_id),
            "churn_risk": await self.calculate_churn_risk(customer_id),
            "recency_days": await self.calculate_recency(customer_id),
            "frequency_90d": await self.calculate_frequency(customer_id, 90),
            "frequency_30d": await self.calculate_frequency(customer_id, 30),
            "monetary_value": await self.calculate_monetary_value(customer_id),
            "last_computed_at": datetime.utcnow().isoformat()
        })

        customer.computed_traits = computed_traits
        await self.db.commit()

        logger.info(f"Updated computed traits for customer {customer_id}")

    # ============== Segmentation ==============

    async def assign_segments(self, customer_id: str) -> List[str]:
        """Assign customer to segments based on criteria.

        Args:
            customer_id: Customer ID.

        Returns:
            List of segment IDs the customer belongs to.
        """
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return []

        # Get all active segments for organization
        segments_result = await self.db.execute(
            select(CustomerSegment).where(
                and_(
                    CustomerSegment.organization_id == customer.organization_id,
                    CustomerSegment.status == SegmentStatus.ACTIVE,
                    CustomerSegment.is_deleted == "N"
                )
            )
        )
        segments = segments_result.scalars().all()

        assigned_segments = []

        for segment in segments:
            if await self._evaluate_segment_criteria(customer, segment):
                await self._add_to_segment(customer_id, segment.id)
                assigned_segments.append(segment.id)

        return assigned_segments

    async def _evaluate_segment_criteria(
        self,
        customer: Customer,
        segment: CustomerSegment
    ) -> bool:
        """Evaluate if customer matches segment criteria."""
        criteria = segment.criteria or {}
        conditions = criteria.get("conditions", [])
        operator = criteria.get("operator", "and")

        if not conditions:
            return False

        results = []
        for condition in conditions:
            result = self._evaluate_condition(customer, condition)
            results.append(result)

        if operator == "and":
            return all(results)
        else:  # "or"
            return any(results)

    def _evaluate_condition(
        self,
        customer: Customer,
        condition: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition against customer data."""
        field = condition.get("field", "")
        op = condition.get("operator", "eq")
        value = condition.get("value")

        # Get field value from customer
        field_value = self._get_field_value(customer, field)

        # Evaluate based on operator
        operators = {
            "eq": lambda fv, v: fv == v,
            "ne": lambda fv, v: fv != v,
            "gt": lambda fv, v: fv is not None and v is not None and fv > v,
            "gte": lambda fv, v: fv is not None and v is not None and fv >= v,
            "lt": lambda fv, v: fv is not None and v is not None and fv < v,
            "lte": lambda fv, v: fv is not None and v is not None and fv <= v,
            "contains": lambda fv, v: fv is not None and v in fv if isinstance(fv, (str, list)) else False,
            "starts_with": lambda fv, v: fv is not None and fv.startswith(v) if isinstance(fv, str) else False,
            "ends_with": lambda fv, v: fv is not None and fv.endswith(v) if isinstance(fv, str) else False,
            "exists": lambda fv, v: (fv is not None) == v,
        }

        eval_fn = operators.get(op)
        if eval_fn:
            return eval_fn(field_value, value)

        return False

    def _get_field_value(self, customer: Customer, field: str) -> Any:
        """Get field value from customer using dot notation."""
        parts = field.split(".")

        if parts[0] == "traits":
            data = customer.traits or {}
            parts = parts[1:]
        elif parts[0] == "computed_traits":
            data = customer.computed_traits or {}
            parts = parts[1:]
        elif parts[0] == "external_ids":
            data = customer.external_ids or {}
            parts = parts[1:]
        else:
            data = customer

        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                data = getattr(data, part, None)
            if data is None:
                break

        return data

    async def _add_to_segment(self, customer_id: str, segment_id: str):
        """Add customer to segment."""
        # Check if already a member
        result = await self.db.execute(
            select(SegmentMembership).where(
                and_(
                    SegmentMembership.customer_id == customer_id,
                    SegmentMembership.segment_id == segment_id,
                    SegmentMembership.left_at.is_(None)
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return  # Already a member

        # Create membership
        membership = SegmentMembership(
            customer_id=customer_id,
            segment_id=segment_id,
            joined_reason="criteria_match"
        )
        self.db.add(membership)
        await self.db.commit()

    async def update_segment_membership(
        self,
        segment_id: str,
        customer_ids: List[str],
        operation: str = "add"  # "add", "remove", "replace"
    ):
        """Update segment membership for multiple customers.

        Args:
            segment_id: Segment ID.
            customer_ids: List of customer IDs.
            operation: Operation to perform (add, remove, replace).
        """
        if operation == "replace":
            # Remove all existing members
            result = await self.db.execute(
                select(SegmentMembership).where(
                    and_(
                        SegmentMembership.segment_id == segment_id,
                        SegmentMembership.left_at.is_(None)
                    )
                )
            )
            for membership in result.scalars().all():
                membership.leave("segment_replaced")

        for customer_id in customer_ids:
            if operation == "remove":
                # Remove from segment
                result = await self.db.execute(
                    select(SegmentMembership).where(
                        and_(
                            SegmentMembership.customer_id == customer_id,
                            SegmentMembership.segment_id == segment_id,
                            SegmentMembership.left_at.is_(None)
                        )
                    )
                )
                membership = result.scalar_one_or_none()
                if membership:
                    membership.leave("manual_remove")
            else:
                # Add to segment
                await self._add_to_segment(customer_id, segment_id)

        await self.db.commit()

    async def compute_segment(self, segment_id: str) -> Dict[str, Any]:
        """Compute segment membership based on criteria.

        Args:
            segment_id: Segment ID to compute.

        Returns:
            Computation results.
        """
        result = await self.db.execute(
            select(CustomerSegment).where(CustomerSegment.id == segment_id)
        )
        segment = result.scalar_one_or_none()

        if not segment:
            return {"success": False, "error": "Segment not found"}

        # Mark as computing
        segment.mark_computing()
        await self.db.commit()

        try:
            # Get all customers in organization
            customers_result = await self.db.execute(
                select(Customer).where(
                    and_(
                        Customer.organization_id == segment.organization_id,
                        Customer.is_deleted == "N"
                    )
                )
            )
            customers = customers_result.scalars().all()

            matched_count = 0
            for customer in customers:
                should_be_member = await self._evaluate_segment_criteria(customer, segment)

                # Check current membership
                membership_result = await self.db.execute(
                    select(SegmentMembership).where(
                        and_(
                            SegmentMembership.customer_id == customer.id,
                            SegmentMembership.segment_id == segment_id
                        )
                    )
                )
                membership = membership_result.scalar_one_or_none()

                if should_be_member and not membership:
                    # Add to segment
                    await self._add_to_segment(customer.id, segment_id)
                    matched_count += 1
                elif not should_be_member and membership and membership.is_active():
                    # Remove from segment
                    membership.leave("criteria_no_longer_match")
                elif should_be_member and membership and not membership.is_active():
                    # Rejoin segment
                    membership.rejoin("criteria_match")
                    matched_count += 1
                elif should_be_member:
                    matched_count += 1

            # Mark as computed
            segment.mark_computed(matched_count)
            await self.db.commit()

            return {
                "success": True,
                "segment_id": segment_id,
                "customer_count": matched_count,
                "computed_at": segment.computed_at.isoformat()
            }

        except Exception as e:
            segment.status = SegmentStatus.ACTIVE  # Reset status
            await self.db.commit()
            logger.error(f"Segment computation failed: {e}")
            return {"success": False, "error": str(e)}