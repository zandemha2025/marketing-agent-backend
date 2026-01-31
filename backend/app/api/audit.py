"""
Audit log API endpoints for compliance and security monitoring.

Provides endpoints for querying and exporting audit logs.
Requires admin or auditor role for access.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from io import StringIO
import csv
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..core.config import get_settings
from ..services.security.audit_logger import AuditLogger, get_audit_logger
from ..models.audit_log import AuditAction, ResourceType, AuditLog
from ..models.user import UserRole, User
from .auth import get_current_active_user

router = APIRouter()


# === Pydantic Models ===

class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    organization_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    resource_name: Optional[str]
    timestamp: datetime
    success: bool
    ip_address: Optional[str] = Field(None, description="Only included for admin users")
    user_agent: Optional[str] = Field(None, description="Only included for admin users")
    failure_reason: Optional[str]
    metadata: dict
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditLogFilterParams(BaseModel):
    """Filter parameters for audit log queries."""
    action: Optional[AuditAction] = None
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    success: Optional[bool] = None


class AuditStatsResponse(BaseModel):
    """Audit log statistics."""
    total_logs: int
    failed_actions: int
    unique_users: int
    actions_breakdown: dict
    period_start: datetime
    period_end: datetime


class ExportFormat(str, Enum):
    """Export formats for audit logs."""
    CSV = "csv"
    JSON = "json"


# === Authorization Helpers ===

def require_admin_or_auditor(current_user = Depends(get_current_active_user)):
    """Require admin or auditor role."""
    if current_user.role not in (UserRole.ADMIN,):
        # In the future, add UserRole.AUDITOR when available
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or auditor access required"
        )
    return current_user


def require_same_org_or_admin(
    organization_id: Optional[str],
    current_user = Depends(get_current_active_user)
):
    """Require same organization or admin role."""
    if current_user.role != UserRole.ADMIN:
        if organization_id and organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access logs from other organizations"
            )
    return current_user


# === API Endpoints ===

@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List audit logs with filtering.
    
    - Regular users can only see logs from their own organization
    - Admins can see logs from any organization
    - Supports pagination and various filters
    """
    audit_logger = get_audit_logger(session)
    
    # Determine organization filter based on user role
    if current_user.role != UserRole.ADMIN:
        # Non-admin users can only see their org's logs
        org_filter = current_user.organization_id
    else:
        # Admins can filter by any org or see all
        org_filter = organization_id or current_user.organization_id
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get logs
    logs = await audit_logger.get_logs(
        organization_id=org_filter,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        success=success,
        limit=page_size,
        offset=offset,
    )
    
    # Get total count
    total = await audit_logger.get_log_count(
        organization_id=org_filter,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Calculate pages
    pages = (total + page_size - 1) // page_size
    
    # Build response
    include_sensitive = current_user.role == UserRole.ADMIN
    items = [build_log_response(log, include_sensitive) for log in logs]
    
    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/logs/export")
async def export_audit_logs(
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format"),
    start_date: datetime = Query(..., description="Start date (ISO format, required)"),
    end_date: datetime = Query(..., description="End date (ISO format, required)"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    current_user: User = Depends(require_admin_or_auditor),
    session: AsyncSession = Depends(get_session),
):
    """
    Export audit logs for compliance purposes.
    
    - Requires admin or auditor role
    - Date range is required and limited to 90 days per export
    - Supports CSV and JSON formats
    """
    # Validate date range
    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )
    
    max_range = timedelta(days=90)
    if end_date - start_date > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days per export"
        )
    
    audit_logger = get_audit_logger(session)
    
    # Determine organization filter
    org_filter = organization_id if current_user.role == UserRole.ADMIN else current_user.organization_id
    
    # Get logs for export
    logs = await audit_logger.get_logs_for_export(
        organization_id=org_filter,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Log the export itself
    await audit_logger.log_export(
        resource_type=ResourceType.AUDIT_LOG,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=org_filter,
        export_format=format.value,
        record_count=len(logs),
    )
    
    # Generate export
    if format == ExportFormat.CSV:
        return await _export_csv(logs, start_date, end_date)
    else:
        return await _export_json(logs, start_date, end_date)


@router.get("/logs/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get audit log statistics for the specified period.
    
    Provides aggregated statistics about audit events.
    """
    from sqlalchemy import func, select, distinct
    
    # Determine organization filter
    if current_user.role != UserRole.ADMIN:
        org_filter = current_user.organization_id
    else:
        org_filter = organization_id or current_user.organization_id
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Build query
    query = select(AuditLog).where(
        AuditLog.organization_id == org_filter,
        AuditLog.timestamp >= start_date,
        AuditLog.timestamp <= end_date,
    )
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    # Calculate statistics
    total_logs = len(logs)
    failed_actions = sum(1 for log in logs if not log.success)
    unique_users = len(set(log.user_id for log in logs if log.user_id))
    
    # Actions breakdown
    actions_breakdown = {}
    for log in logs:
        actions_breakdown[log.action] = actions_breakdown.get(log.action, 0) + 1
    
    return AuditStatsResponse(
        total_logs=total_logs,
        failed_actions=failed_actions,
        unique_users=unique_users,
        actions_breakdown=actions_breakdown,
        period_start=start_date,
        period_end=end_date,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific audit log entry by ID.
    
    Users can only access logs from their own organization.
    """
    from sqlalchemy import select
    
    result = await session.execute(
        select(AuditLog).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    # Check permissions
    if current_user.role != UserRole.ADMIN:
        if log.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access logs from other organizations"
            )
    
    include_sensitive = current_user.role == UserRole.ADMIN
    return build_log_response(log, include_sensitive)


# === Helper Functions ===

def build_log_response(log: AuditLog, include_sensitive: bool = False) -> AuditLogResponse:
    """Build audit log response with appropriate field filtering."""
    data = {
        "id": log.id,
        "user_id": log.user_id,
        "user_email": log.user_email,
        "organization_id": log.organization_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "resource_name": log.resource_name,
        "timestamp": log.timestamp,
        "success": log.success,
        "failure_reason": log.failure_reason,
        "metadata": log.metadata or {},
    }
    
    if include_sensitive:
        data["ip_address"] = log.ip_address
        data["user_agent"] = log.user_agent
    
    return AuditLogResponse(**data)


async def _export_csv(logs: List[AuditLog], start_date: datetime, end_date: datetime) -> StreamingResponse:
    """Export logs as CSV."""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "id", "timestamp", "user_id", "user_email", "organization_id",
        "action", "resource_type", "resource_id", "resource_name",
        "success", "failure_reason", "ip_address", "user_agent",
        "metadata"
    ])
    
    # Write data
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.user_id or "",
            log.user_email or "",
            log.organization_id or "",
            log.action,
            log.resource_type,
            log.resource_id or "",
            log.resource_name or "",
            "true" if log.success else "false",
            log.failure_reason or "",
            log.ip_address or "",
            log.user_agent or "",
            json.dumps(log.metadata) if log.metadata else "{}",
        ])
    
    output.seek(0)
    
    filename = f"audit_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _export_json(logs: List[AuditLog], start_date: datetime, end_date: datetime) -> StreamingResponse:
    """Export logs as JSON."""
    import json
    
    data = {
        "export_metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "record_count": len(logs),
        },
        "logs": [log.to_dict(include_sensitive=True) for log in logs]
    }
    
    output = json.dumps(data, indent=2, default=str)
    
    filename = f"audit_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
    
    return StreamingResponse(
        iter([output]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )