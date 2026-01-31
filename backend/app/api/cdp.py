"""
CDP API endpoints for the Customer Data Platform.

Provides REST API for customer profiles, events, segments,
and identity resolution operations.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from ..core.database import get_session
from ..core.config import get_settings
from .auth import get_current_active_user
from ..models.user import User
from ..models.customer import Customer
from ..models.customer_identity import CustomerIdentity, IdentityType, IdentitySource
from ..models.customer_event import CustomerEvent, EventType, EventSource
from ..models.customer_segment import CustomerSegment, SegmentType, SegmentStatus
from ..models.segment_membership import SegmentMembership
from ..services.cdp import (
    IdentityResolver, EventProcessor, EventIngestionService,
    ProfileEnricher, ClientSDK
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Pydantic Schemas ==============

class CustomerCreate(BaseModel):
    """Schema for creating a customer."""
    external_ids: Dict[str, str] = Field(default_factory=dict)
    anonymous_id: Optional[str] = None
    traits: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    external_ids: Optional[Dict[str, str]] = None
    traits: Optional[Dict[str, Any]] = None
    computed_traits: Optional[Dict[str, Any]] = None


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    id: str
    organization_id: str
    workspace_id: Optional[str]
    external_ids: Dict[str, str]
    anonymous_id: Optional[str]
    traits: Dict[str, Any]
    computed_traits: Dict[str, Any]
    engagement_score: float
    lifetime_value: float
    churn_risk: float
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    """Schema for creating an event."""
    event_name: str
    event_type: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None
    customer_id: Optional[str] = None
    anonymous_id: Optional[str] = None


class EventResponse(BaseModel):
    """Schema for event response."""
    id: str
    customer_id: Optional[str]
    anonymous_id: Optional[str]
    event_type: str
    event_name: str
    properties: Dict[str, Any]
    timestamp: datetime
    received_at: datetime

    class Config:
        from_attributes = True


class SegmentCreate(BaseModel):
    """Schema for creating a segment."""
    name: str
    description: Optional[str] = None
    segment_type: SegmentType = SegmentType.DYNAMIC
    criteria: Dict[str, Any] = Field(default_factory=dict)
    event_criteria: Optional[Dict[str, Any]] = None
    is_dynamic: bool = True
    refresh_interval_minutes: int = 60
    tags: List[str] = Field(default_factory=list)
    color: Optional[str] = None


class SegmentUpdate(BaseModel):
    """Schema for updating a segment."""
    name: Optional[str] = None
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    event_criteria: Optional[Dict[str, Any]] = None
    is_dynamic: Optional[bool] = None
    refresh_interval_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None


class SegmentResponse(BaseModel):
    """Schema for segment response."""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    segment_type: str
    status: str
    criteria: Dict[str, Any]
    customer_count: int
    is_dynamic: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IdentityCreate(BaseModel):
    """Schema for creating an identity."""
    identity_type: str
    identity_value: str
    source: str = "api"
    verified: bool = False
    confidence: float = 1.0


class IdentityResolveRequest(BaseModel):
    """Schema for identity resolution request."""
    email: Optional[str] = None
    phone: Optional[str] = None
    external_ids: Optional[Dict[str, str]] = None
    anonymous_id: Optional[str] = None
    traits: Optional[Dict[str, Any]] = None


class IdentityResolveResponse(BaseModel):
    """Schema for identity resolution response."""
    customer_id: Optional[str]
    anonymous_id: Optional[str]
    confidence: float
    match_type: str
    matched_fields: List[str]


class BatchEventRequest(BaseModel):
    """Schema for batch event ingestion."""
    events: List[EventCreate]
    context: Optional[Dict[str, Any]] = None


class BatchEventResponse(BaseModel):
    """Schema for batch event response."""
    sent: int
    success: int
    failed: int
    errors: List[Dict[str, Any]]


class MergeRequest(BaseModel):
    """Schema for merge request."""
    source_customer_id: str
    reason: Optional[str] = "api_merge"


# ============== Customer Endpoints ==============

@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    profile: CustomerCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new customer profile."""
    customer = Customer(
        organization_id=current_user.organization_id,
        workspace_id=profile.workspace_id,
        external_ids=profile.external_ids,
        anonymous_id=profile.anonymous_id,
        traits=profile.traits,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow()
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    # Create identities from external_ids
    resolver = IdentityResolver(db)
    for id_type, id_value in profile.external_ids.items():
        try:
            await resolver.link_identity(
                customer.id,
                id_type,
                id_value,
                source=IdentitySource.API
            )
        except ValueError:
            pass  # Identity may already exist

    return customer


@router.get("/customers", response_model=List[CustomerResponse])
async def list_customers(
    segment_id: Optional[str] = None,
    search: Optional[str] = None,
    traits: Optional[str] = None,  # JSON string
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List customers with optional filtering."""
    query = select(Customer).where(
        and_(
            Customer.organization_id == current_user.organization_id,
            Customer.is_deleted == "N"
        )
    )

    # Filter by segment
    if segment_id:
        query = query.join(
            SegmentMembership,
            and_(
                SegmentMembership.customer_id == Customer.id,
                SegmentMembership.segment_id == segment_id,
                SegmentMembership.left_at.is_(None)
            )
        )

    # Search by email or name
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            or_(
                Customer.traits.contains({"email": search_lower}),
                Customer.traits.contains({"first_name": search_lower}),
                Customer.traits.contains({"last_name": search_lower})
            )
        )

    # Filter by traits (simplified - exact match)
    if traits:
        import json
        try:
            trait_filters = json.loads(traits)
            for key, value in trait_filters.items():
                query = query.where(Customer.traits.contains({key: value}))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid traits JSON")

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return customers


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    include_events: bool = False,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a customer by ID."""
    result = await db.execute(
        select(Customer).where(
            and_(
                Customer.id == customer_id,
                Customer.is_deleted == "N"
            )
        )
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if include_events:
        await db.refresh(customer, ['events'])

    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    profile: CustomerUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a customer profile."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if profile.external_ids is not None:
        # Merge external IDs
        merged = {**(customer.external_ids or {}), **profile.external_ids}
        customer.external_ids = merged

    if profile.traits is not None:
        merged = {**(customer.traits or {}), **profile.traits}
        customer.traits = merged

    if profile.computed_traits is not None:
        merged = {**(customer.computed_traits or {}), **profile.computed_traits}
        customer.computed_traits = merged

    await db.commit()
    await db.refresh(customer)

    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete a customer (GDPR compliant)."""
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.soft_delete()
    await db.commit()

    return {"success": True, "message": "Customer deleted"}


@router.post("/customers/{customer_id}/merge")
async def merge_customer(
    customer_id: str,
    merge_request: MergeRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Merge another customer into this customer."""
    resolver = IdentityResolver(db)

    try:
        merged = await resolver.merge_profiles(
            customer_id,
            merge_request.source_customer_id,
            merge_request.reason
        )
        return {
            "success": True,
            "customer_id": merged.id,
            "merged_from": merge_request.source_customer_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/customers/{customer_id}/enrich")
async def enrich_customer(
    customer_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger profile enrichment for a customer."""
    enricher = ProfileEnricher(db)

    # Run in background
    async def do_enrichment():
        await enricher.update_all_computed_traits(customer_id)

    background_tasks.add_task(do_enrichment)

    return {"success": True, "message": "Enrichment started"}


# ============== Event Endpoints ==============

@router.post("/events", response_model=Dict[str, Any])
async def track_event(
    event: EventCreate,
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Track a new event."""
    event_data = event.model_dump()
    event_data["organization_id"] = organization_id

    processor = EventProcessor(db)

    try:
        processed_event, customer = await processor.ingest_event(event_data)
        return {
            "success": True,
            "event_id": processed_event.id,
            "customer_id": customer.id if customer else None,
            "anonymous_id": processed_event.anonymous_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events/batch", response_model=BatchEventResponse)
async def track_events_batch(
    request: BatchEventRequest,
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Track multiple events in a batch."""
    events_data = []
    for e in request.events:
        event_dict = e.model_dump()
        event_dict["organization_id"] = organization_id
        if request.context:
            event_dict["context"] = {**request.context, **event_dict.get("context", {})}
        events_data.append(event_dict)

    processor = EventProcessor(db)
    result = await processor.process_batch(events_data, organization_id)

    return BatchEventResponse(**result)


@router.get("/events", response_model=List[EventResponse])
async def query_events(
    organization_id: str,
    customer_id: Optional[str] = None,
    event_type: Optional[str] = None,
    event_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Query events with filters."""
    query = select(CustomerEvent).where(
        CustomerEvent.organization_id == organization_id
    )

    if customer_id:
        query = query.where(CustomerEvent.customer_id == customer_id)

    if event_type:
        try:
            etype = EventType(event_type)
            query = query.where(CustomerEvent.event_type == etype)
        except ValueError:
            pass

    if event_name:
        query = query.where(CustomerEvent.event_name == event_name)

    if start_date:
        query = query.where(CustomerEvent.timestamp >= start_date)

    if end_date:
        query = query.where(CustomerEvent.timestamp <= end_date)

    query = query.order_by(desc(CustomerEvent.timestamp))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return events


@router.get("/customers/{customer_id}/events", response_model=List[EventResponse])
async def get_customer_events(
    customer_id: str,
    event_types: Optional[List[str]] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get events for a specific customer."""
    query = select(CustomerEvent).where(
        CustomerEvent.customer_id == customer_id
    )

    if event_types:
        types = [EventType(et) for et in event_types if et in [t.value for t in EventType]]
        if types:
            query = query.where(CustomerEvent.event_type.in_(types))

    query = query.order_by(desc(CustomerEvent.timestamp)).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return events


# ============== Segment Endpoints ==============

@router.post("/segments", response_model=SegmentResponse)
async def create_segment(
    segment: SegmentCreate,
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new customer segment."""
    new_segment = CustomerSegment(
        organization_id=organization_id,
        name=segment.name,
        description=segment.description,
        segment_type=segment.segment_type,
        criteria=segment.criteria,
        event_criteria=segment.event_criteria,
        is_dynamic=segment.is_dynamic,
        refresh_interval_minutes=segment.refresh_interval_minutes,
        tags=segment.tags,
        color=segment.color
    )

    db.add(new_segment)
    await db.commit()
    await db.refresh(new_segment)

    return new_segment


@router.get("/segments", response_model=List[SegmentResponse])
async def list_segments(
    organization_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List segments for an organization."""
    query = select(CustomerSegment).where(
        and_(
            CustomerSegment.organization_id == organization_id,
            CustomerSegment.is_deleted == "N"
        )
    )

    if status:
        try:
            s = SegmentStatus(status)
            query = query.where(CustomerSegment.status == s)
        except ValueError:
            pass

    result = await db.execute(query)
    segments = result.scalars().all()

    return segments


@router.get("/segments/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a segment by ID."""
    result = await db.execute(
        select(CustomerSegment).where(
            and_(
                CustomerSegment.id == segment_id,
                CustomerSegment.is_deleted == "N"
            )
        )
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    return segment


@router.put("/segments/{segment_id}", response_model=SegmentResponse)
async def update_segment(
    segment_id: str,
    segment_update: SegmentUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a segment."""
    result = await db.execute(
        select(CustomerSegment).where(CustomerSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    update_data = segment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.commit()
    await db.refresh(segment)

    return segment


@router.delete("/segments/{segment_id}")
async def delete_segment(
    segment_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a segment."""
    result = await db.execute(
        select(CustomerSegment).where(CustomerSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    segment.soft_delete()
    await db.commit()

    return {"success": True, "message": "Segment deleted"}


@router.post("/segments/{segment_id}/compute")
async def compute_segment(
    segment_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Compute segment membership."""
    enricher = ProfileEnricher(db)

    # Run in background for large segments
    async def do_compute():
        await enricher.compute_segment(segment_id)

    background_tasks.add_task(do_compute)

    return {"success": True, "message": "Segment computation started"}


@router.get("/segments/{segment_id}/customers", response_model=List[CustomerResponse])
async def get_segment_customers(
    segment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get customers in a segment."""
    query = select(Customer).join(
        SegmentMembership,
        and_(
            SegmentMembership.customer_id == Customer.id,
            SegmentMembership.segment_id == segment_id,
            SegmentMembership.left_at.is_(None)
        )
    ).where(Customer.is_deleted == "N")

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()

    return customers


# ============== Identity Resolution Endpoints ==============

@router.post("/identity/resolve", response_model=IdentityResolveResponse)
async def resolve_identity(
    request: IdentityResolveRequest,
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Resolve identity from provided identifiers."""
    resolver = IdentityResolver(db)

    # Try email first
    if request.email:
        customer = await resolver.match_by_email(request.email, organization_id)
        if customer:
            return IdentityResolveResponse(
                customer_id=customer.id,
                anonymous_id=None,
                confidence=1.0,
                match_type="email",
                matched_fields=["email"]
            )

    # Try phone
    if request.phone:
        customer = await resolver.match_by_phone(request.phone, organization_id)
        if customer:
            return IdentityResolveResponse(
                customer_id=customer.id,
                anonymous_id=None,
                confidence=1.0,
                match_type="phone",
                matched_fields=["phone"]
            )

    # Try external IDs
    if request.external_ids:
        for id_type, id_value in request.external_ids.items():
            customer = await resolver.match_by_external_id(
                id_type, id_value, organization_id
            )
            if customer:
                return IdentityResolveResponse(
                    customer_id=customer.id,
                    anonymous_id=None,
                    confidence=1.0,
                    match_type=f"external_{id_type}",
                    matched_fields=[id_type]
                )

    # Try fuzzy matching with traits
    if request.traits:
        matches = await resolver.fuzzy_match(
            request.traits, organization_id, min_confidence=0.7
        )
        if matches:
            best_match = matches[0]
            return IdentityResolveResponse(
                customer_id=best_match.customer.id,
                anonymous_id=None,
                confidence=best_match.confidence,
                match_type=best_match.match_type,
                matched_fields=best_match.matched_fields
            )

    # Return anonymous ID if provided, otherwise generate new
    anonymous_id = request.anonymous_id or resolver._generate_anonymous_id()

    return IdentityResolveResponse(
        customer_id=None,
        anonymous_id=anonymous_id,
        confidence=0.0,
        match_type="none",
        matched_fields=[]
    )


@router.post("/customers/{customer_id}/identities")
async def add_identity(
    customer_id: str,
    identity: IdentityCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Add an identity to a customer."""
    resolver = IdentityResolver(db)

    try:
        source = IdentitySource(identity.source)
    except ValueError:
        source = IdentitySource.API

    try:
        new_identity = await resolver.link_identity(
            customer_id,
            identity.identity_type,
            identity.identity_value,
            source=source,
            confidence=identity.confidence,
            verified=identity.verified
        )
        return {
            "success": True,
            "identity_id": new_identity.id,
            "identity_type": new_identity.identity_type.value,
            "identity_value": new_identity.identity_value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/customers/{customer_id}/identities/{identity_type}")
async def remove_identity(
    customer_id: str,
    identity_type: str,
    identity_value: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Remove an identity from a customer."""
    resolver = IdentityResolver(db)

    success = await resolver.unlink_identity(
        customer_id, identity_type, identity_value
    )

    if not success:
        raise HTTPException(status_code=404, detail="Identity not found")

    return {"success": True, "message": "Identity removed"}


@router.get("/customers/{customer_id}/identities")
async def list_identities(
    customer_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List identities for a customer."""
    result = await db.execute(
        select(CustomerIdentity).where(
            and_(
                CustomerIdentity.customer_id == customer_id,
                CustomerIdentity.is_deleted == "N"
            )
        )
    )
    identities = result.scalars().all()

    return {
        "identities": [
            {
                "id": i.id,
                "type": i.identity_type.value,
                "value": i.identity_value,
                "verified": i.is_verified,
                "confidence": i.confidence_score,
                "source": i.source.value
            }
            for i in identities
        ]
    }


# ============== SDK Endpoints ==============

@router.get("/sdk/config")
async def get_sdk_config(
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get SDK configuration for organization."""
    sdk = ClientSDK(db)
    return sdk.get_sdk_settings(organization_id)


@router.get("/sdk/snippet")
async def get_sdk_snippet(
    organization_id: str,
    workspace_id: Optional[str] = None,
    api_host: str = "https://api.example.com"
):
    """Get JavaScript SDK snippet."""
    sdk = ClientSDK(None)  # No DB needed for snippet generation
    snippet = sdk.generate_snippet(
        organization_id=organization_id,
        workspace_id=workspace_id,
        api_host=api_host
    )
    return {"snippet": snippet}


@router.post("/sdk/alias")
async def alias_identity(
    anonymous_id: str,
    user_id: str,
    organization_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Alias anonymous ID to user ID."""
    sdk = ClientSDK(db)
    result = await sdk.alias_anonymous_id(anonymous_id, user_id, organization_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result