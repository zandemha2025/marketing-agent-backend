"""
Identity Resolution Service for the Customer Data Platform.

Provides deterministic and probabilistic matching algorithms
to unify customer profiles across multiple touchpoints.
"""
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

from ...models.customer import Customer
from ...models.customer_identity import CustomerIdentity, IdentityType, IdentitySource

logger = logging.getLogger(__name__)


class MatchConfidence:
    """Confidence levels for identity matches."""
    EXACT = 1.0
    HIGH = 0.9
    MEDIUM = 0.7
    LOW = 0.5
    NONE = 0.0


@dataclass
class MatchResult:
    """Result of an identity match operation."""
    customer: Customer
    confidence: float
    match_type: str
    matched_fields: List[str]
    match_details: Dict[str, Any]


class IdentityResolver:
    """
    Service for resolving and merging customer identities.

    Implements both deterministic (exact) and probabilistic (fuzzy)
    matching algorithms to link customer profiles across devices
    and touchpoints.
    """

    # Thresholds for probabilistic matching
    FUZZY_MATCH_THRESHOLD = 0.85  # Minimum similarity for name matching
    EMAIL_MATCH_THRESHOLD = 0.95  # Near-exact for emails
    PHONE_MATCH_THRESHOLD = 0.90  # High for phones

    def __init__(self, db: AsyncSession):
        """Initialize the identity resolver.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db

    # ============== Deterministic Matching ==============

    async def match_by_email(
        self,
        email: str,
        organization_id: str,
        verified_only: bool = False
    ) -> Optional[Customer]:
        """Find customer by email address.

        Args:
            email: Email address to search for.
            organization_id: Organization to scope the search.
            verified_only: Only return verified email matches.

        Returns:
            Matching customer or None.
        """
        if not email:
            return None

        email = email.lower().strip()

        # Check customer identities table first
        query = select(CustomerIdentity).where(
            and_(
                CustomerIdentity.identity_type == IdentityType.EMAIL,
                CustomerIdentity.identity_value == email,
                CustomerIdentity.customer.has(organization_id=organization_id),
                CustomerIdentity.is_deleted == "N"
            )
        )

        if verified_only:
            query = query.where(CustomerIdentity.is_verified == True)

        result = await self.db.execute(query)
        identity = result.scalar_one_or_none()

        if identity:
            # Load customer with relationships
            await self.db.refresh(identity.customer, ['identities'])
            return identity.customer

        # Fallback: Check external_ids in customer table
        query = select(Customer).where(
            and_(
                Customer.organization_id == organization_id,
                Customer.external_ids.contains({"email": email}),
                Customer.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def match_by_phone(
        self,
        phone: str,
        organization_id: str,
        normalize: bool = True
    ) -> Optional[Customer]:
        """Find customer by phone number.

        Args:
            phone: Phone number to search for.
            organization_id: Organization to scope the search.
            normalize: Whether to normalize the phone number (remove non-digits).

        Returns:
            Matching customer or None.
        """
        if not phone:
            return None

        if normalize:
            phone = self._normalize_phone(phone)

        query = select(CustomerIdentity).where(
            and_(
                CustomerIdentity.identity_type == IdentityType.PHONE,
                CustomerIdentity.identity_value == phone,
                CustomerIdentity.customer.has(organization_id=organization_id),
                CustomerIdentity.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        identity = result.scalar_one_or_none()

        if identity:
            await self.db.refresh(identity.customer, ['identities'])
            return identity.customer

        # Fallback: Check external_ids
        query = select(Customer).where(
            and_(
                Customer.organization_id == organization_id,
                Customer.external_ids.contains({"phone": phone}),
                Customer.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def match_by_external_id(
        self,
        id_type: str,
        id_value: str,
        organization_id: str
    ) -> Optional[Customer]:
        """Find customer by external ID.

        Args:
            id_type: Type of external ID (e.g., 'crm_id', 'stripe_id').
            id_value: External identifier value.
            organization_id: Organization to scope the search.

        Returns:
            Matching customer or None.
        """
        if not id_type or not id_value:
            return None

        # Map common ID types to IdentityType enum
        identity_type = self._map_to_identity_type(id_type)

        if identity_type:
            query = select(CustomerIdentity).where(
                and_(
                    CustomerIdentity.identity_type == identity_type,
                    CustomerIdentity.identity_value == id_value,
                    CustomerIdentity.customer.has(organization_id=organization_id),
                    CustomerIdentity.is_deleted == "N"
                )
            )

            result = await self.db.execute(query)
            identity = result.scalar_one_or_none()

            if identity:
                await self.db.refresh(identity.customer, ['identities'])
                return identity.customer

        # Check external_ids JSON field
        query = select(Customer).where(
            and_(
                Customer.organization_id == organization_id,
                Customer.external_ids.contains({id_type: id_value}),
                Customer.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def match_by_anonymous_id(
        self,
        anonymous_id: str,
        organization_id: str
    ) -> Optional[Customer]:
        """Find customer by anonymous ID.

        Args:
            anonymous_id: Anonymous tracking ID.
            organization_id: Organization to scope the search.

        Returns:
            Matching customer or None.
        """
        if not anonymous_id:
            return None

        query = select(Customer).where(
            and_(
                Customer.organization_id == organization_id,
                Customer.anonymous_id == anonymous_id,
                Customer.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def match_by_device_id(
        self,
        device_id: str,
        organization_id: str
    ) -> Optional[Customer]:
        """Find customer by device ID.

        Args:
            device_id: Device identifier.
            organization_id: Organization to scope the search.

        Returns:
            Matching customer or None.
        """
        if not device_id:
            return None

        query = select(CustomerIdentity).where(
            and_(
                CustomerIdentity.identity_type == IdentityType.DEVICE_ID,
                CustomerIdentity.identity_value == device_id,
                CustomerIdentity.customer.has(organization_id=organization_id),
                CustomerIdentity.is_deleted == "N"
            )
        )

        result = await self.db.execute(query)
        identity = result.scalar_one_or_none()

        if identity:
            await self.db.refresh(identity.customer, ['identities'])
            return identity.customer

        return None

    # ============== Probabilistic Matching ==============

    async def fuzzy_match(
        self,
        traits: Dict[str, Any],
        organization_id: str,
        min_confidence: float = MatchConfidence.MEDIUM
    ) -> List[MatchResult]:
        """Find customers using fuzzy matching on traits.

        Args:
            traits: Dictionary of customer traits to match.
            organization_id: Organization to scope the search.
            min_confidence: Minimum confidence threshold for results.

        Returns:
            List of match results sorted by confidence.
        """
        results = []

        # Get candidates based on available identifiers
        candidates = await self._get_match_candidates(traits, organization_id)

        for customer in candidates:
            confidence, matched_fields, details = self._calculate_similarity(
                customer, traits
            )

            if confidence >= min_confidence:
                results.append(MatchResult(
                    customer=customer,
                    confidence=confidence,
                    match_type="fuzzy",
                    matched_fields=matched_fields,
                    match_details=details
                ))

        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def calculate_similarity(
        self,
        customer1: Customer,
        customer2: Customer
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """Calculate similarity between two customers.

        Args:
            customer1: First customer to compare.
            customer2: Second customer to compare.

        Returns:
            Tuple of (confidence_score, matched_fields, match_details).
        """
        traits1 = {
            **(customer1.traits or {}),
            **(customer1.external_ids or {})
        }
        traits2 = {
            **(customer2.traits or {}),
            **(customer2.external_ids or {})
        }

        return self._calculate_similarity_dict(traits1, traits2)

    def _calculate_similarity(
        self,
        customer: Customer,
        traits: Dict[str, Any]
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """Calculate similarity between customer and traits dict."""
        customer_traits = {
            **(customer.traits or {}),
            **(customer.external_ids or {})
        }
        return self._calculate_similarity_dict(customer_traits, traits)

    def _calculate_similarity_dict(
        self,
        traits1: Dict[str, Any],
        traits2: Dict[str, Any]
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """Calculate similarity between two trait dictionaries."""
        scores = []
        matched_fields = []
        details = {}

        # Check email (highest weight)
        email1 = traits1.get("email", "").lower().strip()
        email2 = traits2.get("email", "").lower().strip()
        if email1 and email2:
            email_sim = self._string_similarity(email1, email2)
            if email_sim >= self.EMAIL_MATCH_THRESHOLD:
                scores.append((email_sim, 0.4))  # 40% weight
                matched_fields.append("email")
                details["email_similarity"] = email_sim

        # Check phone
        phone1 = self._normalize_phone(traits1.get("phone", ""))
        phone2 = self._normalize_phone(traits2.get("phone", ""))
        if phone1 and phone2:
            phone_sim = self._string_similarity(phone1, phone2)
            if phone_sim >= self.PHONE_MATCH_THRESHOLD:
                scores.append((phone_sim, 0.3))  # 30% weight
                matched_fields.append("phone")
                details["phone_similarity"] = phone_sim

        # Check first name
        first1 = traits1.get("first_name", "").lower().strip()
        first2 = traits2.get("first_name", "").lower().strip()
        if first1 and first2:
            first_sim = self._string_similarity(first1, first2)
            if first_sim >= self.FUZZY_MATCH_THRESHOLD:
                scores.append((first_sim, 0.1))  # 10% weight
                matched_fields.append("first_name")
                details["first_name_similarity"] = first_sim

        # Check last name
        last1 = traits1.get("last_name", "").lower().strip()
        last2 = traits2.get("last_name", "").lower().strip()
        if last1 and last2:
            last_sim = self._string_similarity(last1, last2)
            if last_sim >= self.FUZZY_MATCH_THRESHOLD:
                scores.append((last_sim, 0.1))  # 10% weight
                matched_fields.append("last_name")
                details["last_name_similarity"] = last_sim

        # Check company
        company1 = traits1.get("company", "").lower().strip()
        company2 = traits2.get("company", "").lower().strip()
        if company1 and company2:
            company_sim = self._string_similarity(company1, company2)
            if company_sim >= self.FUZZY_MATCH_THRESHOLD:
                scores.append((company_sim, 0.1))  # 10% weight
                matched_fields.append("company")
                details["company_similarity"] = company_sim

        # Calculate weighted average
        if scores:
            total_weight = sum(weight for _, weight in scores)
            weighted_sum = sum(score * weight for score, weight in scores)
            confidence = weighted_sum / total_weight if total_weight > 0 else 0
        else:
            confidence = 0

        return confidence, matched_fields, details

    # ============== Profile Merging ==============

    async def merge_profiles(
        self,
        primary_id: str,
        secondary_id: str,
        merge_reason: str = "identity_resolution"
    ) -> Customer:
        """Merge two customer profiles.

        Args:
            primary_id: ID of the primary (surviving) profile.
            secondary_id: ID of the secondary (merged) profile.
            merge_reason: Reason for the merge.

        Returns:
            The merged primary customer profile.
        """
        # Load both customers
        primary_result = await self.db.execute(
            select(Customer).where(Customer.id == primary_id)
        )
        primary = primary_result.scalar_one()

        secondary_result = await self.db.execute(
            select(Customer).where(Customer.id == secondary_id)
        )
        secondary = secondary_result.scalar_one()

        # Merge traits (primary takes precedence)
        merged_traits = {**(secondary.traits or {})}
        merged_traits.update(primary.traits or {})
        primary.traits = merged_traits

        # Merge external IDs
        merged_external_ids = {**(secondary.external_ids or {})}
        merged_external_ids.update(primary.external_ids or {})
        primary.external_ids = merged_external_ids

        # Merge computed traits (take latest values)
        merged_computed = {**(secondary.computed_traits or {})}
        merged_computed.update(primary.computed_traits or {})
        primary.computed_traits = merged_computed

        # Merge identities
        await self._merge_identities(primary, secondary)

        # Aggregate metrics (take max or sum as appropriate)
        primary.engagement_score = max(
            primary.engagement_score or 0,
            secondary.engagement_score or 0
        )
        primary.lifetime_value = max(
            primary.lifetime_value or 0,
            secondary.lifetime_value or 0
        )
        primary.churn_risk = min(  # Lower churn risk is better
            primary.churn_risk or 1.0,
            secondary.churn_risk or 1.0
        )

        # Use earliest first seen
        if secondary.first_seen_at and (not primary.first_seen_at or
                                        secondary.first_seen_at < primary.first_seen_at):
            primary.first_seen_at = secondary.first_seen_at

        # Use latest last seen
        if secondary.last_seen_at and (not primary.last_seen_at or
                                       secondary.last_seen_at > primary.last_seen_at):
            primary.last_seen_at = secondary.last_seen_at

        # Record merge history
        primary.merge_profile(secondary_id)
        primary.computed_traits["merge_history"] = primary.computed_traits.get("merge_history", []) + [{
            "merged_customer_id": secondary_id,
            "merged_at": datetime.utcnow().isoformat(),
            "reason": merge_reason
        }]

        # Soft delete secondary profile
        secondary.soft_delete()

        await self.db.commit()
        await self.db.refresh(primary, ['identities'])

        logger.info(
            f"Merged customer {secondary_id} into {primary_id}. Reason: {merge_reason}"
        )

        return primary

    def resolve_conflicts(self, field: str, values: List[Any]) -> Any:
        """Resolve conflicting field values during merge.

        Args:
            field: Field name being resolved.
            values: List of conflicting values.

        Returns:
            The resolved value.
        """
        if not values:
            return None

        # Remove None values
        values = [v for v in values if v is not None]

        if not values:
            return None

        # For single value, return it
        if len(values) == 1:
            return values[0]

        # Field-specific resolution strategies
        resolution_strategies = {
            # Take the most recent timestamp
            "updated_at": lambda vs: max(vs),
            "created_at": lambda vs: min(vs),

            # Take the maximum for engagement metrics
            "engagement_score": lambda vs: max(vs),
            "lifetime_value": lambda vs: max(vs),
            "frequency_score": lambda vs: max(vs),
            "monetary_value": lambda vs: max(vs),

            # Take the minimum for risk scores
            "churn_risk": lambda vs: min(vs),
            "recency_days": lambda vs: min(vs),

            # Take the longest/most complete for names
            "first_name": lambda vs: max(vs, key=len),
            "last_name": lambda vs: max(vs, key=len),
            "company": lambda vs: max(vs, key=len),
        }

        if field in resolution_strategies:
            return resolution_strategies[field](values)

        # Default: take the first non-empty value
        for v in values:
            if v:
                return v

        return values[0]

    async def _merge_identities(self, primary: Customer, secondary: Customer):
        """Merge identities from secondary to primary customer."""
        # Load secondary identities
        identities_result = await self.db.execute(
            select(CustomerIdentity).where(
                and_(
                    CustomerIdentity.customer_id == secondary.id,
                    CustomerIdentity.is_deleted == "N"
                )
            )
        )
        secondary_identities = identities_result.scalars().all()

        for identity in secondary_identities:
            # Check if primary already has this identity
            existing_result = await self.db.execute(
                select(CustomerIdentity).where(
                    and_(
                        CustomerIdentity.customer_id == primary.id,
                        CustomerIdentity.identity_type == identity.identity_type,
                        CustomerIdentity.identity_value == identity.identity_value,
                        CustomerIdentity.is_deleted == "N"
                    )
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # Keep the one with higher confidence
                if identity.confidence_score > existing.confidence_score:
                    existing.confidence_score = identity.confidence_score
                    existing.is_verified = existing.is_verified or identity.is_verified
            else:
                # Transfer identity to primary
                identity.customer_id = primary.id

    # ============== Identity Linking ==============

    async def link_identity(
        self,
        customer_id: str,
        id_type: str,
        id_value: str,
        source: IdentitySource = IdentitySource.API,
        confidence: float = 1.0,
        verified: bool = False
    ) -> CustomerIdentity:
        """Link an identity to a customer profile.

        Args:
            customer_id: Customer ID to link to.
            id_type: Type of identity (email, phone, etc.).
            id_value: Identity value.
            source: Source of the identity.
            confidence: Confidence score (0.0 to 1.0).
            verified: Whether the identity is verified.

        Returns:
            The created or updated CustomerIdentity.
        """
        identity_type = self._map_to_identity_type(id_type)
        if not identity_type:
            identity_type = IdentityType.CUSTOM

        # Normalize value based on type
        if identity_type == IdentityType.EMAIL:
            id_value = id_value.lower().strip()
        elif identity_type == IdentityType.PHONE:
            id_value = self._normalize_phone(id_value)

        # Check if identity already exists
        existing_result = await self.db.execute(
            select(CustomerIdentity).where(
                and_(
                    CustomerIdentity.identity_type == identity_type,
                    CustomerIdentity.identity_value == id_value,
                    CustomerIdentity.is_deleted == "N"
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            if existing.customer_id == customer_id:
                # Update existing
                existing.confidence_score = max(existing.confidence_score, confidence)
                existing.is_verified = existing.is_verified or verified
                existing.source = source
            else:
                # Identity conflict - log warning
                logger.warning(
                    f"Identity {id_type}={id_value} already linked to customer "
                    f"{existing.customer_id}, not linking to {customer_id}"
                )
                raise ValueError(
                    f"Identity {id_type} already linked to another customer"
                )
            await self.db.commit()
            return existing

        # Create new identity
        identity = CustomerIdentity(
            customer_id=customer_id,
            identity_type=identity_type,
            identity_value=id_value,
            confidence_score=confidence,
            source=source,
            is_verified=verified
        )

        self.db.add(identity)
        await self.db.commit()
        await self.db.refresh(identity)

        logger.info(f"Linked {id_type}={id_value} to customer {customer_id}")
        return identity

    async def unlink_identity(
        self,
        customer_id: str,
        id_type: str,
        id_value: Optional[str] = None
    ) -> bool:
        """Unlink an identity from a customer profile.

        Args:
            customer_id: Customer ID to unlink from.
            id_type: Type of identity to unlink.
            id_value: Specific value to unlink (if None, unlinks all of type).

        Returns:
            True if any identities were unlinked.
        """
        identity_type = self._map_to_identity_type(id_type)

        query = select(CustomerIdentity).where(
            and_(
                CustomerIdentity.customer_id == customer_id,
                CustomerIdentity.identity_type == identity_type,
                CustomerIdentity.is_deleted == "N"
            )
        )

        if id_value:
            query = query.where(CustomerIdentity.identity_value == id_value)

        result = await self.db.execute(query)
        identities = result.scalars().all()

        for identity in identities:
            identity.soft_delete()

        await self.db.commit()

        if identities:
            logger.info(
                f"Unlinked {len(identities)} {id_type} identity(s) from customer {customer_id}"
            )

        return len(identities) > 0

    # ============== Helper Methods ==============

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number by removing non-digits."""
        if not phone:
            return ""
        return ''.join(c for c in phone if c.isdigit())

    def _map_to_identity_type(self, id_type: str) -> Optional[IdentityType]:
        """Map string ID type to IdentityType enum."""
        type_mapping = {
            "email": IdentityType.EMAIL,
            "phone": IdentityType.PHONE,
            "device_id": IdentityType.DEVICE_ID,
            "browser_id": IdentityType.BROWSER_ID,
            "crm_id": IdentityType.CRM_ID,
            "stripe_id": IdentityType.STRIPE_ID,
            "shopify_id": IdentityType.SHOPIFY_ID,
            "hubspot_id": IdentityType.HUBSPOT_ID,
            "salesforce_id": IdentityType.SALESFORCE_ID,
            "facebook_id": IdentityType.FACEBOOK_ID,
            "google_id": IdentityType.GOOGLE_ID,
            "apple_id": IdentityType.APPLE_ID,
            "linkedin_id": IdentityType.LINKEDIN_ID,
        }
        return type_mapping.get(id_type.lower())

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity between 0 and 1.

        Uses fuzzywuzzy if available, otherwise falls back to difflib.
        """
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        if FUZZYWUZZY_AVAILABLE:
            return fuzz.ratio(s1, s2) / 100.0
        else:
            return SequenceMatcher(None, s1, s2).ratio()

    async def _get_match_candidates(
        self,
        traits: Dict[str, Any],
        organization_id: str,
        limit: int = 100
    ) -> List[Customer]:
        """Get candidate customers for fuzzy matching.

        Uses available identifiers to narrow down candidates.
        """
        conditions = [Customer.organization_id == organization_id]

        # Add conditions based on available traits
        if traits.get("email"):
            email_domain = traits["email"].split("@")[-1] if "@" in traits["email"] else ""
            if email_domain:
                conditions.append(
                    or_(
                        Customer.traits.contains({"email": traits["email"]}),
                        Customer.external_ids.contains({"email": traits["email"]})
                    )
                )

        if traits.get("phone"):
            phone = self._normalize_phone(traits["phone"])
            conditions.append(
                or_(
                    Customer.traits.contains({"phone": phone}),
                    Customer.external_ids.contains({"phone": phone})
                )
            )

        if traits.get("company"):
            conditions.append(
                Customer.traits.contains({"company": traits["company"]})
            )

        query = select(Customer).where(and_(*conditions)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_identity_from_event(
        self,
        event_data: Dict[str, Any],
        organization_id: str
    ) -> Tuple[Optional[Customer], Optional[str]]:
        """Resolve customer identity from event data.

        Tries multiple resolution strategies in order of confidence.

        Args:
            event_data: Event data containing identifiers.
            organization_id: Organization to scope the search.

        Returns:
            Tuple of (customer, anonymous_id). Customer may be None.
        """
        # Priority 1: Customer ID directly
        if event_data.get("customer_id"):
            result = await self.db.execute(
                select(Customer).where(
                    and_(
                        Customer.id == event_data["customer_id"],
                        Customer.organization_id == organization_id,
                        Customer.is_deleted == "N"
                    )
                )
            )
            customer = result.scalar_one_or_none()
            if customer:
                return customer, None

        # Priority 2: External IDs
        if event_data.get("external_ids"):
            ext_ids = event_data["external_ids"]
            for id_type, id_value in ext_ids.items():
                customer = await self.match_by_external_id(
                    id_type, id_value, organization_id
                )
                if customer:
                    return customer, None

        # Priority 3: Email
        email = event_data.get("email") or event_data.get("traits", {}).get("email")
        if email:
            customer = await self.match_by_email(email, organization_id)
            if customer:
                return customer, None

        # Priority 4: Phone
        phone = event_data.get("phone") or event_data.get("traits", {}).get("phone")
        if phone:
            customer = await self.match_by_phone(phone, organization_id)
            if customer:
                return customer, None

        # Priority 5: Device ID
        device_id = event_data.get("context", {}).get("device", {}).get("id")
        if device_id:
            customer = await self.match_by_device_id(device_id, organization_id)
            if customer:
                return customer, None

        # No match found - use or create anonymous ID
        anonymous_id = event_data.get("anonymous_id")
        if anonymous_id:
            customer = await self.match_by_anonymous_id(anonymous_id, organization_id)
            if customer:
                return customer, None

        return None, anonymous_id or self._generate_anonymous_id()

    def _generate_anonymous_id(self) -> str:
        """Generate a new anonymous ID."""
        import uuid
        return f"anon_{uuid.uuid4().hex[:16]}"
