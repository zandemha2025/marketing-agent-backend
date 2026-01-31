"""
Audit log model with SOC 2 compliance fields.

This module provides comprehensive audit logging for all security-relevant events,
ensuring compliance with SOC 2, GDPR, and other regulatory requirements.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text, Index, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # Authentication events
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_VERIFIED = "mfa_verified"
    
    # SAML/SSO events
    SAML_LOGIN_INITIATED = "saml_login_initiated"
    SAML_LOGIN_SUCCESS = "saml_login_success"
    SAML_LOGIN_FAILED = "saml_login_failed"
    SAML_METADATA_UPDATED = "saml_metadata_updated"
    
    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    
    # Data access
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    
    # Administrative
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    USER_REACTIVATED = "user_reactivated"
    ROLE_CHANGED = "role_changed"
    ORG_SETTINGS_CHANGED = "org_settings_changed"
    
    # Compliance
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    DSR_SUBMITTED = "dsr_submitted"
    DSR_COMPLETED = "dsr_completed"
    
    # Security
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"


class ResourceType(str, Enum):
    """Types of resources that can be audited."""
    USER = "user"
    ORGANIZATION = "organization"
    CAMPAIGN = "campaign"
    ASSET = "asset"
    DELIVERABLE = "deliverable"
    KNOWLEDGE_BASE = "knowledge_base"
    CONVERSATION = "conversation"
    TASK = "task"
    SCHEDULED_POST = "scheduled_post"
    TREND = "trend"
    API_KEY = "api_key"
    SETTINGS = "settings"
    AUDIT_LOG = "audit_log"
    CONSENT = "consent"
    DATA_SUBJECT_REQUEST = "data_subject_request"


class AuditLog(Base):
    """
    Audit log entry for SOC 2 compliance.
    
    Records all security-relevant events with:
    - Who performed the action (user_id)
    - What organization (organization_id)
    - What action was taken
    - What resource was affected
    - When it occurred (timestamp)
    - Where it originated (IP, user agent)
    - Whether it succeeded
    - What changed (before/after values)
    """
    
    # Override default id generation to use UUID for audit logs
    id = Column(String(36), primary_key=True, default=lambda: generate_id() + generate_id() + generate_id())
    
    # Actor information
    user_id = Column(String(12), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Denormalized for retention
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Action details
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(36), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)  # Human-readable identifier
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True)
    
    # Geographic/Temporal context
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    timezone = Column(String(50), default="UTC")
    
    # Action result
    success = Column(Boolean, default=True, nullable=False)
    failure_reason = Column(Text, nullable=True)
    
    # Data changes (for updates)
    before_values = Column(JSON, nullable=True)  # Redacted/sanitized
    after_values = Column(JSON, nullable=True)   # Redacted/sanitized
    
    # Additional metadata (using 'extra_data' to avoid reserved word conflict)
    extra_data = Column(JSON, default=dict, nullable=False)
    # Can include:
    # - api_endpoint
    # - http_method
    # - request_duration_ms
    # - changes_summary
    # - approval_chain
    
    # Retention and compliance
    retention_until = Column(DateTime, nullable=True)  # When this log can be purged
    compliance_flags = Column(JSON, default=list, nullable=False)  # ["gdpr", "soc2", "hipaa"]
    encrypted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} on {self.resource_type} by {self.user_id}>"
    
    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert audit log to dictionary."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "organization_id": self.organization_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "timezone": self.timezone,
            "success": self.success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sensitive:
            data.update({
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
                "request_id": self.request_id,
                "session_id": self.session_id,
                "before_values": self.before_values,
                "after_values": self.after_values,
                "metadata": self.metadata,
                "failure_reason": self.failure_reason,
                "compliance_flags": self.compliance_flags,
            })
        
        return data


# Create composite indexes for common query patterns
Index('idx_audit_org_action_time', AuditLog.organization_id, AuditLog.action, AuditLog.timestamp)
Index('idx_audit_user_time', AuditLog.user_id, AuditLog.timestamp)
Index('idx_audit_resource', AuditLog.resource_type, AuditLog.resource_id, AuditLog.timestamp)
Index('idx_audit_retention', AuditLog.retention_until)