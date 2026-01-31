"""
Compliance API endpoints for GDPR/CCPA data subject rights.

Provides endpoints for:
- Submitting and managing Data Subject Requests (DSRs)
- Managing consent preferences
- Exporting personal data
- Identity verification
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..core.config import get_settings
from ..models.user import User
from ..models.consent import Consent, ConsentType, ConsentStatus
from ..models.data_subject_request import (
    DataSubjectRequest, DSRType, DSRStatus, VerificationMethod
)
from ..services.security.gdpr_manager import GDPRManager, get_gdpr_manager
from ..services.security.audit_logger import get_audit_logger, AuditAction, ResourceType
from .auth import get_current_active_user

router = APIRouter()


# === Pydantic Models ===

class ConsentPreference(BaseModel):
    """Individual consent preference."""
    consent_type: str
    granted: bool
    consent_version: str = "1.0"


class ConsentUpdateRequest(BaseModel):
    """Request to update consent preferences."""
    consents: List[ConsentPreference]
    privacy_policy_version: Optional[str] = None


class ConsentResponse(BaseModel):
    """Consent record response."""
    id: str
    consent_type: str
    status: str
    granted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    expires_at: Optional[datetime]
    consent_version: str
    privacy_policy_version: Optional[str]
    is_valid: bool


class DSRSubmitRequest(BaseModel):
    """Request to submit a Data Subject Request."""
    request_type: DSRType
    description: Optional[str] = Field(None, max_length=2000)
    specific_data: Optional[str] = Field(None, max_length=5000)
    jurisdiction: str = Field("GDPR", description="GDPR, CCPA, LGPD, etc.")


class DSRResponse(BaseModel):
    """Data Subject Request response."""
    id: str
    request_number: str
    request_type: str
    status: str
    priority: str
    description: Optional[str]
    submitted_at: datetime
    completion_deadline: datetime
    verified_at: Optional[datetime]
    completed_at: Optional[datetime]
    verification_method: Optional[str]
    result_summary: Optional[str]
    download_url: Optional[str]
    is_overdue: bool
    days_remaining: int


class DSRVerificationRequest(BaseModel):
    """Request to verify identity for a DSR."""
    token: str


class DSRListResponse(BaseModel):
    """Paginated list of DSRs."""
    items: List[DSRResponse]
    total: int
    page: int
    page_size: int


class DataExportResponse(BaseModel):
    """Response for data export request."""
    download_url: str
    expires_at: datetime
    format: str
    size_bytes: int


class PrivacySettingsResponse(BaseModel):
    """User privacy settings."""
    user_id: str
    marketing_consent: bool
    analytics_consent: bool
    personalization_consent: bool
    third_party_sharing_consent: bool
    cookie_consent: bool
    all_consents: List[ConsentResponse]


# === Consent Endpoints ===

@router.get("/consent", response_model=PrivacySettingsResponse)
async def get_consent_preferences(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get current user's consent preferences.
    
    Returns all consent types and their current status.
    """
    gdpr_manager = get_gdpr_manager(session)
    
    # Get all consent types
    consent_types = [
        ConsentType.MARKETING,
        ConsentType.ANALYTICS,
        ConsentType.PERSONALIZATION,
        ConsentType.THIRD_PARTY_SHARING,
        ConsentType.COOKIES,
    ]
    
    all_consents = []
    consent_status = {}
    
    for consent_type in consent_types:
        # Check if consent exists
        from sqlalchemy import select, and_
        result = await session.execute(
            select(Consent).where(
                and_(
                    Consent.user_id == current_user.id,
                    Consent.consent_type == consent_type.value
                )
            )
        )
        consent = result.scalar_one_or_none()
        
        if consent:
            all_consents.append(ConsentResponse(
                id=consent.id,
                consent_type=consent.consent_type,
                status=consent.status,
                granted_at=consent.granted_at,
                revoked_at=consent.revoked_at,
                expires_at=consent.expires_at,
                consent_version=consent.consent_version,
                privacy_policy_version=consent.privacy_policy_version,
                is_valid=consent.is_valid(),
            ))
            consent_status[consent_type.value] = consent.is_valid()
        else:
            # No consent record = not granted
            consent_status[consent_type.value] = False
    
    return PrivacySettingsResponse(
        user_id=current_user.id,
        marketing_consent=consent_status.get(ConsentType.MARKETING.value, False),
        analytics_consent=consent_status.get(ConsentType.ANALYTICS.value, False),
        personalization_consent=consent_status.get(ConsentType.PERSONALIZATION.value, False),
        third_party_sharing_consent=consent_status.get(ConsentType.THIRD_PARTY_SHARING.value, False),
        cookie_consent=consent_status.get(ConsentType.COOKIES.value, False),
        all_consents=all_consents,
    )


@router.put("/consent", response_model=List[ConsentResponse])
async def update_consent_preferences(
    request: ConsentUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user's consent preferences.
    
    Allows granting or revoking consent for various data processing activities.
    Records the change with IP address and timestamp for compliance.
    """
    gdpr_manager = get_gdpr_manager(session)
    audit_logger = get_audit_logger(session)
    
    # Get client info
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("User-Agent")
    
    updated_consents = []
    
    for pref in request.consents:
        try:
            consent_type = ConsentType(pref.consent_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid consent type: {pref.consent_type}"
            )
        
        # Record consent change
        consent = await gdpr_manager.record_consent(
            user=current_user,
            consent_type=consent_type,
            granted=pref.granted,
            ip_address=client_ip,
            user_agent=user_agent,
            privacy_policy_version=request.privacy_policy_version,
            metadata={
                "updated_via": "api",
                "consent_version": pref.consent_version,
            }
        )
        
        updated_consents.append(ConsentResponse(
            id=consent.id,
            consent_type=consent.consent_type,
            status=consent.status,
            granted_at=consent.granted_at,
            revoked_at=consent.revoked_at,
            expires_at=consent.expires_at,
            consent_version=consent.consent_version,
            privacy_policy_version=consent.privacy_policy_version,
            is_valid=consent.is_valid(),
        ))
        
        # Log consent change
        action = AuditAction.CONSENT_GRANTED if pref.granted else AuditAction.CONSENT_REVOKED
        await audit_logger.log(
            action=action,
            resource_type=ResourceType.CONSENT,
            resource_id=consent.id,
            user_id=current_user.id,
            user_email=current_user.email,
            organization_id=current_user.organization_id,
            metadata={"consent_type": consent_type.value}
        )
    
    return updated_consents


@router.post("/consent/revoke-all")
async def revoke_all_consents(
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Revoke all consents for the current user.
    
    This is a convenience endpoint for users who want to opt out of all
    non-essential data processing at once.
    """
    gdpr_manager = get_gdpr_manager(session)
    audit_logger = get_audit_logger(session)
    
    count = await gdpr_manager.revoke_all_consents(current_user.id)
    
    # Log the action
    await audit_logger.log(
        action=AuditAction.CONSENT_REVOKED,
        resource_type=ResourceType.CONSENT,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=current_user.organization_id,
        metadata={"revoked_all": True, "count": count}
    )
    
    return {
        "message": f"Revoked {count} consent records",
        "revoked_count": count,
    }


# === Data Subject Request Endpoints ===

@router.post("/dsr", response_model=DSRResponse, status_code=status.HTTP_201_CREATED)
async def submit_dsr(
    request: DSRSubmitRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Submit a new Data Subject Request.
    
    Creates a request to exercise privacy rights (access, deletion, portability, etc.).
    The request will be processed within the legal timeframe (30 days for GDPR).
    """
    gdpr_manager = get_gdpr_manager(session)
    
    # Get client info
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("User-Agent")
    
    # Submit the request
    dsr = await gdpr_manager.submit_dsr(
        user=current_user,
        request_type=request.request_type,
        description=request.description,
        specific_data=request.specific_data,
        jurisdiction=request.jurisdiction,
        source="api",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    
    # Initiate verification
    verification_token = await gdpr_manager.initiate_verification(
        dsr=dsr,
        method=VerificationMethod.EMAIL,
    )
    
    # TODO: Send verification email with token
    
    return _dsr_to_response(dsr)


@router.get("/dsr", response_model=DSRListResponse)
async def list_dsrs(
    status: Optional[DSRStatus] = Query(None, description="Filter by status"),
    request_type: Optional[DSRType] = Query(None, description="Filter by type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List Data Subject Requests for the current user.
    
    Users can only see their own DSRs. Admins can see all DSRs for their organization.
    """
    from sqlalchemy import select, desc, func, and_
    
    # Build query
    query = select(DataSubjectRequest).where(
        DataSubjectRequest.user_id == current_user.id
    )
    
    if status:
        query = query.where(DataSubjectRequest.status == status.value)
    if request_type:
        query = query.where(DataSubjectRequest.request_type == request_type.value)
    
    # Get total count
    count_query = select(func.count(DataSubjectRequest.id)).where(
        DataSubjectRequest.user_id == current_user.id
    )
    count_result = await session.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(DataSubjectRequest.submitted_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    dsrs = result.scalars().all()
    
    return DSRListResponse(
        items=[_dsr_to_response(dsr) for dsr in dsrs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/dsr/{dsr_id}", response_model=DSRResponse)
async def get_dsr(
    dsr_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get details of a specific Data Subject Request.
    
    Users can only access their own DSRs.
    """
    from sqlalchemy import select
    
    result = await session.execute(
        select(DataSubjectRequest).where(DataSubjectRequest.id == dsr_id)
    )
    dsr = result.scalar_one_or_none()
    
    if not dsr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data Subject Request not found"
        )
    
    # Check ownership
    if dsr.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this request"
        )
    
    return _dsr_to_response(dsr)


@router.post("/dsr/{dsr_id}/verify")
async def verify_dsr_identity(
    dsr_id: str,
    request: DSRVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Verify identity for a Data Subject Request.
    
    Required before processing can begin. Uses the token sent via email.
    """
    gdpr_manager = get_gdpr_manager(session)
    
    # Get DSR
    from sqlalchemy import select
    result = await session.execute(
        select(DataSubjectRequest).where(DataSubjectRequest.id == dsr_id)
    )
    dsr = result.scalar_one_or_none()
    
    if not dsr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data Subject Request not found"
        )
    
    if dsr.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot verify this request"
        )
    
    # Verify identity
    success = await gdpr_manager.verify_identity(dsr, token=request.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {
        "message": "Identity verified successfully",
        "dsr_id": dsr_id,
        "status": dsr.status,
    }


@router.post("/dsr/{dsr_id}/cancel")
async def cancel_dsr(
    dsr_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Cancel a pending Data Subject Request.
    
    Can only cancel requests that haven't been completed yet.
    """
    from sqlalchemy import select
    
    result = await session.execute(
        select(DataSubjectRequest).where(DataSubjectRequest.id == dsr_id)
    )
    dsr = result.scalar_one_or_none()
    
    if not dsr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data Subject Request not found"
        )
    
    if dsr.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel this request"
        )
    
    # Can only cancel if not completed
    if dsr.status in (DSRStatus.COMPLETED.value, DSRStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed or failed request"
        )
    
    dsr.status = DSRStatus.CANCELLED.value
    await session.commit()
    
    return {
        "message": "Request cancelled successfully",
        "dsr_id": dsr_id,
    }


# === Data Export Endpoints ===

@router.get("/export")
async def export_personal_data(
    format: str = Query("json", description="Export format: json, csv, xml"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export all personal data for the current user.
    
    This is a convenience endpoint that creates and immediately processes
    an access request, returning the data directly.
    """
    gdpr_manager = get_gdpr_manager(session)
    audit_logger = get_audit_logger(session)
    
    # Create a DSR for tracking
    dsr = await gdpr_manager.submit_dsr(
        user=current_user,
        request_type=DSRType.ACCESS,
        description="User-initiated data export via API",
        jurisdiction="GDPR",
        source="api",
    )
    
    # Auto-verify (user is already authenticated)
    dsr.status = DSRStatus.VERIFIED.value
    dsr.verified_at = datetime.utcnow()
    
    # Process the request
    try:
        data = await gdpr_manager.handle_access_request(dsr)
        
        # Format based on request
        if format.lower() == "csv":
            content = gdpr_manager._convert_to_csv_format(data)
            media_type = "text/csv"
            filename = f"personal_data_{current_user.id}.csv"
        elif format.lower() == "xml":
            content = gdpr_manager._convert_to_xml_format(data)
            media_type = "application/xml"
            filename = f"personal_data_{current_user.id}.xml"
        else:
            import json
            content = json.dumps(data, indent=2, default=str)
            media_type = "application/json"
            filename = f"personal_data_{current_user.id}.json"
        
        # Log the export
        await audit_logger.log_export(
            resource_type=ResourceType.USER,
            user_id=current_user.id,
            user_email=current_user.email,
            organization_id=current_user.organization_id,
            export_format=format,
            record_count=1,
        )
        
        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        dsr.status = DSRStatus.FAILED.value
        dsr.result_summary = str(e)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export data: {str(e)}"
        )


@router.delete("/account", status_code=status.HTTP_202_ACCEPTED)
async def request_account_deletion(
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Request account deletion (Right to be forgotten).
    
    Creates a deletion request that will be processed within the legal timeframe.
    This is irreversible once completed.
    """
    gdpr_manager = get_gdpr_manager(session)
    
    # Get client info
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("User-Agent")
    
    # Submit deletion request
    dsr = await gdpr_manager.submit_dsr(
        user=current_user,
        request_type=DSRType.DELETION,
        description="User requested account deletion",
        jurisdiction="GDPR",
        source="api",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    
    return {
        "message": "Account deletion request submitted",
        "request_number": dsr.request_number,
        "completion_deadline": dsr.completion_deadline.isoformat(),
        "note": "Your account will be deleted within 30 days. You can cancel this request until processing begins.",
    }


# === Helper Functions ===

def _dsr_to_response(dsr: DataSubjectRequest) -> DSRResponse:
    """Convert DSR model to response."""
    return DSRResponse(
        id=dsr.id,
        request_number=dsr.request_number,
        request_type=dsr.request_type,
        status=dsr.status,
        priority=dsr.priority,
        description=dsr.description,
        submitted_at=dsr.submitted_at,
        completion_deadline=dsr.completion_deadline,
        verified_at=dsr.verified_at,
        completed_at=dsr.completed_at,
        verification_method=dsr.verification_method,
        result_summary=dsr.result_summary,
        download_url=dsr.download_url,
        is_overdue=dsr.is_overdue(),
        days_remaining=dsr.days_remaining(),
    )