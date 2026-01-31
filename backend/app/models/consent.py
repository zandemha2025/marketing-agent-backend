"""
Consent management model for GDPR/CCPA compliance.

Tracks user consent for various data processing activities including
marketing, analytics, and third-party sharing.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class ConsentType(str, Enum):
    """Types of consent that can be granted."""
    MARKETING = "marketing"  # Marketing emails and communications
    ANALYTICS = "analytics"  # Analytics and usage tracking
    PERSONALIZATION = "personalization"  # Personalized content/recommendations
    THIRD_PARTY_SHARING = "third_party_sharing"  # Sharing with third parties
    COOKIES = "cookies"  # Cookie usage
    LOCATION_TRACKING = "location_tracking"  # Geographic location data
    BIOMETRIC = "biometric"  # Biometric data processing
    AI_TRAINING = "ai_training"  # Using data for AI model training


class ConsentStatus(str, Enum):
    """Status of a consent record."""
    GRANTED = "granted"
    REVOKED = "revoked"
    PENDING = "pending"  # Awaiting user action
    EXPIRED = "expired"  # Consent period ended


class Consent(Base):
    """
    Consent management record for GDPR/CCPA compliance.
    
    Tracks:
    - What the user consented to (consent_type)
    - When they consented (granted_at)
    - Whether consent is still valid (status)
    - Which version of the privacy policy (privacy_policy_version)
    - IP address and user agent for verification
    """
    
    # User reference
    user_id = Column(String(12), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Consent details
    consent_type = Column(String(50), nullable=False, index=True)
    """Type of consent (marketing, analytics, etc.)"""
    
    status = Column(String(20), default=ConsentStatus.GRANTED.value, nullable=False)
    """Current status of the consent"""
    
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    """When consent was granted"""
    
    revoked_at = Column(DateTime, nullable=True)
    """When consent was revoked (if applicable)"""
    
    expires_at = Column(DateTime, nullable=True)
    """When consent expires (if applicable)"""
    
    # Version tracking
    consent_version = Column(String(20), default="1.0", nullable=False)
    """Version of the consent form/agreement"""
    
    privacy_policy_version = Column(String(20), nullable=True)
    """Version of privacy policy in effect when consent was given"""
    
    terms_of_service_version = Column(String(20), nullable=True)
    """Version of terms of service in effect when consent was given"""
    
    # Context
    ip_address = Column(String(45), nullable=True)
    """IP address when consent was given"""
    
    user_agent = Column(String(500), nullable=True)
    """User agent when consent was given"""
    
    country_code = Column(String(2), nullable=True)
    """ISO country code (for jurisdiction tracking)"""
    
    # Additional metadata (using 'extra_data' to avoid reserved word conflict)
    extra_data = Column(JSON, default=dict, nullable=False)
    """Additional context like:
    - browser_language
    - referral_source
    - consent_method (checkbox, toggle, etc.)
    - parent_consent_id (for related consents)
    """
    
    # Relationships
    user = relationship("User", back_populates="consents")
    
    def __repr__(self):
        return f"<Consent {self.consent_type}={self.status} for user {self.user_id}>"
    
    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.GRANTED.value:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
    
    def revoke(self, ip_address: str = None, user_agent: str = None):
        """Revoke this consent."""
        self.status = ConsentStatus.REVOKED.value
        self.revoked_at = datetime.utcnow()
        
        if ip_address:
            self.metadata["revoked_ip"] = ip_address
        if user_agent:
            self.metadata["revoked_user_agent"] = user_agent
    
    def to_dict(self, include_metadata: bool = False) -> dict[str, Any]:
        """Convert consent record to dictionary."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "consent_type": self.consent_type,
            "status": self.status,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "consent_version": self.consent_version,
            "privacy_policy_version": self.privacy_policy_version,
            "terms_of_service_version": self.terms_of_service_version,
            "is_valid": self.is_valid(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_metadata:
            data["ip_address"] = self.ip_address
            data["user_agent"] = self.user_agent
            data["country_code"] = self.country_code
            data["metadata"] = self.metadata
        
        return data


# Create indexes for common queries
Index('idx_consent_user_type', Consent.user_id, Consent.consent_type)
Index('idx_consent_org_type', Consent.organization_id, Consent.consent_type)
Index('idx_consent_status', Consent.status, Consent.granted_at)