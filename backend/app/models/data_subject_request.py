"""
Data Subject Request (DSR) model for GDPR/CCPA compliance.

Handles requests from users to exercise their rights under privacy regulations:
- Right to access (GDPR Article 15)
- Right to erasure / Right to be forgotten (GDPR Article 17)
- Right to data portability (GDPR Article 20)
- Right to rectification (GDPR Article 16)
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class DSRType(str, Enum):
    """Types of Data Subject Requests."""
    ACCESS = "access"  # Right to access personal data
    DELETION = "deletion"  # Right to erasure / Right to be forgotten
    PORTABILITY = "portability"  # Right to data portability
    RECTIFICATION = "rectification"  # Right to rectification
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"  # Right to object to processing
    PROFILING = "profiling"  # Right not to be subject to automated decision-making


class DSRStatus(str, Enum):
    """Status of a Data Subject Request."""
    PENDING = "pending"  # Received, awaiting verification
    VERIFYING = "verifying"  # Identity verification in progress
    VERIFIED = "verified"  # Identity verified, processing
    PROCESSING = "processing"  # Actively processing the request
    COMPLETED = "completed"  # Request fulfilled
    PARTIAL = "partial"  # Partially fulfilled (some data couldn't be deleted)
    REJECTED = "rejected"  # Request rejected (e.g., identity not verified)
    FAILED = "failed"  # Processing failed
    CANCELLED = "cancelled"  # Cancelled by user


class DSRPriority(str, Enum):
    """Priority levels for DSRs."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"  # Near deadline
    URGENT = "urgent"  # Past deadline


class VerificationMethod(str, Enum):
    """Methods for verifying identity for DSRs."""
    EMAIL = "email"  # Email verification link
    MFA = "mfa"  # Multi-factor authentication
    DOCUMENT = "document"  # ID document upload
    PHONE = "phone"  # Phone verification
    ADMIN = "admin"  # Manual admin verification
    SSO = "sso"  # Verified via SSO provider


class DataSubjectRequest(Base):
    """
    Data Subject Request (DSR) record for GDPR/CCPA compliance.
    
    Tracks:
    - Type of request (access, deletion, etc.)
    - Current status and progress
    - Identity verification
    - Completion deadline (GDPR: 30 days, CCPA: 45 days)
    - Results and download URLs
    """
    
    # Request identification
    request_number = Column(String(20), unique=True, nullable=False, index=True)
    """Human-readable request number (e.g., DSR-2024-001234)"""
    
    # User reference
    user_id = Column(String(12), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Request details
    request_type = Column(String(20), nullable=False, index=True)
    """Type of DSR (access, deletion, portability, etc.)"""
    
    status = Column(String(20), default=DSRStatus.PENDING.value, nullable=False, index=True)
    """Current status of the request"""
    
    priority = Column(String(10), default=DSRPriority.NORMAL.value, nullable=False)
    """Priority based on deadline proximity"""
    
    # Description and details
    description = Column(Text, nullable=True)
    """User's description of the request"""
    
    specific_data = Column(Text, nullable=True)
    """Specific data the user is requesting (for access/rectification)"""
    
    # Timeline
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    """When the request was submitted"""
    
    completion_deadline = Column(DateTime, nullable=False)
    """Deadline for completing the request (GDPR: 30 days, CCPA: 45 days)"""
    
    verified_at = Column(DateTime, nullable=True)
    """When identity was verified"""
    
    started_at = Column(DateTime, nullable=True)
    """When processing started"""
    
    completed_at = Column(DateTime, nullable=True)
    """When request was completed"""
    
    # Identity verification
    verification_method = Column(String(20), nullable=True)
    """Method used to verify identity"""
    
    verification_token = Column(String(255), nullable=True)
    """Token for identity verification (hashed)"""
    
    verification_expires = Column(DateTime, nullable=True)
    """When verification token expires"""
    
    verified_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    """Admin who verified identity (if manual verification)"""
    
    # Results
    result_summary = Column(Text, nullable=True)
    """Summary of what was done to fulfill the request"""
    
    result_details = Column(Text, nullable=True)
    """Detailed results (JSON or text)"""
    
    download_url = Column(String(500), nullable=True)
    """URL to download exported data (for access/portability requests)"""
    
    download_expires = Column(DateTime, nullable=True)
    """When download URL expires"""
    
    records_affected = Column(String(50), default="0", nullable=False)
    """Number of records affected (as string for large numbers)"""
    
    # Extensions
    extension_requested = Column(String(1), default="N", nullable=False)
    """Whether extension was requested (Y/N)"""
    
    extension_reason = Column(Text, nullable=True)
    """Reason for extension (GDPR allows 2-month extension for complex requests)"""
    
    extended_deadline = Column(DateTime, nullable=True)
    """New deadline if extended"""
    
    # Rejection details
    rejection_reason = Column(Text, nullable=True)
    """Why request was rejected (if applicable)"""
    
    rejection_category = Column(String(50), nullable=True)
    """Category of rejection (e.g., 'unverifiable', 'excessive', 'manifestly_unfounded')"""
    
    # Metadata
    jurisdiction = Column(String(10), default="GDPR", nullable=False)
    """Applicable regulation: GDPR, CCPA, LGPD, etc."""
    
    source = Column(String(50), default="web", nullable=False)
    """How the request was submitted (web, email, api, etc.)"""
    
    ip_address = Column(String(45), nullable=True)
    """IP address of requester"""
    
    user_agent = Column(String(500), nullable=True)
    """User agent of requester"""
    
    extra_data = Column(Text, nullable=True)
    """Additional metadata as JSON"""
    
    # Relationships
    user = relationship("User", back_populates="data_subject_requests", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<DSR {self.request_number} ({self.request_type}) - {self.status}>"
    
    def calculate_deadline(self, days: int = 30) -> datetime:
        """Calculate completion deadline."""
        return self.submitted_at + timedelta(days=days)
    
    def update_priority(self):
        """Update priority based on deadline proximity."""
        now = datetime.utcnow()
        deadline = self.extended_deadline or self.completion_deadline
        
        days_remaining = (deadline - now).days
        
        if days_remaining < 0:
            self.priority = DSRPriority.URGENT.value
        elif days_remaining <= 3:
            self.priority = DSRPriority.HIGH.value
        elif days_remaining <= 10:
            self.priority = DSRPriority.NORMAL.value
        else:
            self.priority = DSRPriority.LOW.value
    
    def is_overdue(self) -> bool:
        """Check if request is past deadline."""
        deadline = self.extended_deadline or self.completion_deadline
        return datetime.utcnow() > deadline
    
    def days_remaining(self) -> int:
        """Calculate days remaining until deadline."""
        deadline = self.extended_deadline or self.completion_deadline
        return (deadline - datetime.utcnow()).days
    
    def can_extend(self) -> bool:
        """Check if request can be extended (GDPR allows one 2-month extension)."""
        return self.extension_requested == "N" and self.status in (
            DSRStatus.PENDING.value,
            DSRStatus.VERIFYING.value,
            DSRStatus.VERIFIED.value,
            DSRStatus.PROCESSING.value,
        )
    
    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert DSR to dictionary."""
        data = {
            "id": self.id,
            "request_number": self.request_number,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "request_type": self.request_type,
            "status": self.status,
            "priority": self.priority,
            "description": self.description,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completion_deadline": self.completion_deadline.isoformat() if self.completion_deadline else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "verification_method": self.verification_method,
            "result_summary": self.result_summary,
            "records_affected": self.records_affected,
            "extension_requested": self.extension_requested == "Y",
            "extended_deadline": self.extended_deadline.isoformat() if self.extended_deadline else None,
            "rejection_reason": self.rejection_reason,
            "jurisdiction": self.jurisdiction,
            "source": self.source,
            "is_overdue": self.is_overdue(),
            "days_remaining": self.days_remaining(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data["specific_data"] = self.specific_data
            data["result_details"] = self.result_details
            data["download_url"] = self.download_url
            data["download_expires"] = self.download_expires.isoformat() if self.download_expires else None
            data["ip_address"] = self.ip_address
            data["user_agent"] = self.user_agent
            data["metadata"] = self.metadata
        
        return data


# Create indexes for common queries
Index('idx_dsr_org_status', DataSubjectRequest.organization_id, DataSubjectRequest.status)
Index('idx_dsr_user_type', DataSubjectRequest.user_id, DataSubjectRequest.request_type)
Index('idx_dsr_deadline', DataSubjectRequest.completion_deadline, DataSubjectRequest.status)
Index('idx_dsr_priority', DataSubjectRequest.priority, DataSubjectRequest.status)