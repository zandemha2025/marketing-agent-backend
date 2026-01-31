"""
GDPR/CCPA compliance service for data subject rights management.

Handles:
- Data Subject Requests (access, deletion, portability, rectification)
- Identity verification
- Data anonymization
- Consent management
- Right to be forgotten
"""
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ...models.user import User
from ...models.consent import Consent, ConsentType, ConsentStatus
from ...models.data_subject_request import (
    DataSubjectRequest, DSRType, DSRStatus, VerificationMethod
)
from ...models.audit_log import AuditAction, ResourceType
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class AnonymizationStrategy(Enum):
    """Strategies for anonymizing data."""
    HASH = "hash"  # One-way hash
    NULL = "null"  # Set to null
    PATTERN = "pattern"  # Replace with pattern (e.g., ***REDACTED***)
    RANDOM = "random"  # Replace with random data
    DELETE = "delete"  # Remove the record entirely


class GDPRManager:
    """
    Manager for GDPR/CCPA compliance operations.
    
    Provides methods for:
    - Handling Data Subject Requests
    - Verifying user identity
    - Anonymizing personal data
    - Managing consent
    - Data export for portability
    """
    
    def __init__(self, session: AsyncSession, audit_logger: Optional[AuditLogger] = None):
        self.session = session
        self.audit_logger = audit_logger
    
    # === Data Subject Request Handling ===
    
    async def submit_dsr(
        self,
        user: User,
        request_type: DSRType,
        description: Optional[str] = None,
        specific_data: Optional[str] = None,
        jurisdiction: str = "GDPR",
        source: str = "web",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DataSubjectRequest:
        """
        Submit a new Data Subject Request.
        
        Args:
            user: The user making the request
            request_type: Type of DSR (access, deletion, etc.)
            description: User's description of the request
            specific_data: Specific data being requested
            jurisdiction: Applicable regulation (GDPR, CCPA, etc.)
            source: How the request was submitted
            ip_address: Requester's IP address
            user_agent: Requester's user agent
            
        Returns:
            Created DataSubjectRequest
        """
        # Calculate deadline based on jurisdiction
        if jurisdiction == "GDPR":
            deadline_days = 30
        elif jurisdiction == "CCPA":
            deadline_days = 45
        else:
            deadline_days = 30
        
        submitted_at = datetime.utcnow()
        deadline = submitted_at + timedelta(days=deadline_days)
        
        # Generate request number
        request_number = self._generate_request_number()
        
        dsr = DataSubjectRequest(
            request_number=request_number,
            user_id=user.id,
            organization_id=user.organization_id,
            request_type=request_type.value,
            status=DSRStatus.PENDING.value,
            description=description,
            specific_data=specific_data,
            submitted_at=submitted_at,
            completion_deadline=deadline,
            jurisdiction=jurisdiction,
            source=source,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.session.add(dsr)
        await self.session.commit()
        
        # Log the submission
        if self.audit_logger:
            await self.audit_logger.log(
                action=AuditAction.DSR_SUBMITTED,
                resource_type=ResourceType.DATA_SUBJECT_REQUEST,
                resource_id=dsr.id,
                user_id=user.id,
                user_email=user.email,
                organization_id=user.organization_id,
                metadata={
                    "request_type": request_type.value,
                    "request_number": request_number,
                    "jurisdiction": jurisdiction,
                }
            )
        
        logger.info(f"DSR submitted: {request_number} by user {user.id}")
        return dsr
    
    async def initiate_verification(
        self,
        dsr: DataSubjectRequest,
        method: VerificationMethod = VerificationMethod.EMAIL,
    ) -> str:
        """
        Initiate identity verification for a DSR.
        
        Returns:
            Verification token (for email/SMS methods)
        """
        # Generate verification token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        dsr.verification_token = token_hash
        dsr.verification_expires = datetime.utcnow() + timedelta(hours=24)
        dsr.status = DSRStatus.VERIFYING.value
        dsr.verification_method = method.value
        
        await self.session.commit()
        
        logger.info(f"Verification initiated for DSR {dsr.request_number} using {method.value}")
        
        return token
    
    async def verify_identity(
        self,
        dsr: DataSubjectRequest,
        token: Optional[str] = None,
        verified_by: Optional[str] = None,
    ) -> bool:
        """
        Verify identity for a DSR.
        
        Args:
            dsr: The DSR to verify
            token: Verification token (for email/SMS methods)
            verified_by: Admin user ID (for manual verification)
            
        Returns:
            True if verification successful
        """
        # Check if token matches (if applicable)
        if token and dsr.verification_token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if token_hash != dsr.verification_token:
                logger.warning(f"Invalid verification token for DSR {dsr.request_number}")
                return False
            
            # Check if token expired
            if datetime.utcnow() > dsr.verification_expires:
                logger.warning(f"Expired verification token for DSR {dsr.request_number}")
                return False
        
        # Mark as verified
        dsr.status = DSRStatus.VERIFIED.value
        dsr.verified_at = datetime.utcnow()
        dsr.verified_by = verified_by
        
        await self.session.commit()
        
        # Log verification
        if self.audit_logger:
            await self.audit_logger.log(
                action=AuditAction.DSR_COMPLETED,  # Actually a status change
                resource_type=ResourceType.DATA_SUBJECT_REQUEST,
                resource_id=dsr.id,
                user_id=dsr.user_id,
                metadata={
                    "action": "identity_verified",
                    "verification_method": dsr.verification_method,
                }
            )
        
        logger.info(f"Identity verified for DSR {dsr.request_number}")
        return True
    
    async def handle_access_request(
        self,
        dsr: DataSubjectRequest,
    ) -> Dict[str, Any]:
        """
        Handle a data access request (GDPR Article 15).
        
        Exports all personal data for the user.
        
        Returns:
            Dictionary containing all user data
        """
        dsr.status = DSRStatus.PROCESSING.value
        dsr.started_at = datetime.utcnow()
        await self.session.commit()
        
        try:
            # Get user
            result = await self.session.execute(
                select(User).where(User.id == dsr.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {dsr.user_id} not found")
            
            # Collect all user data
            user_data = {
                "request_info": {
                    "request_number": dsr.request_number,
                    "submitted_at": dsr.submitted_at.isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                },
                "user_profile": user.to_dict(include_sensitive=True),
                "consents": await self._get_consent_data(dsr.user_id),
                "audit_logs": await self._get_audit_log_summary(dsr.user_id),
                "campaigns": await self._get_campaign_data(dsr.user_id),
                "assets": await self._get_asset_data(dsr.user_id),
                "conversations": await self._get_conversation_data(dsr.user_id),
            }
            
            # Mark as completed
            dsr.status = DSRStatus.COMPLETED.value
            dsr.completed_at = datetime.utcnow()
            dsr.result_summary = f"Exported {len(user_data)} data categories"
            dsr.result_details = json.dumps({
                "categories": list(user_data.keys()),
                "record_counts": {
                    "consents": len(user_data["consents"]),
                }
            })
            
            await self.session.commit()
            
            # Log completion
            if self.audit_logger:
                await self.audit_logger.log(
                    action=AuditAction.DSR_COMPLETED,
                    resource_type=ResourceType.DATA_SUBJECT_REQUEST,
                    resource_id=dsr.id,
                    user_id=dsr.user_id,
                    metadata={"request_type": "access"}
                )
            
            return user_data
            
        except Exception as e:
            dsr.status = DSRStatus.FAILED.value
            dsr.result_summary = f"Failed: {str(e)}"
            await self.session.commit()
            raise
    
    async def handle_deletion_request(
        self,
        dsr: DataSubjectRequest,
        anonymize: bool = True,
    ) -> Dict[str, Any]:
        """
        Handle a data deletion request / Right to be forgotten (GDPR Article 17).
        
        Args:
            dsr: The deletion request
            anonymize: If True, anonymize instead of hard delete where required
            
        Returns:
            Summary of deleted/anonymized data
        """
        dsr.status = DSRStatus.PROCESSING.value
        dsr.started_at = datetime.utcnow()
        await self.session.commit()
        
        results = {
            "deleted": [],
            "anonymized": [],
            "retained": [],
            "errors": [],
        }
        
        try:
            # Get user
            result = await self.session.execute(
                select(User).where(User.id == dsr.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {dsr.user_id} not found")
            
            # Anonymize user record (don't delete for audit trail)
            await self.anonymize_user(user, strategy=AnonymizationStrategy.HASH)
            results["anonymized"].append("user_profile")
            
            # Delete or anonymize related data
            # Consents - can delete
            await self._delete_consents(dsr.user_id)
            results["deleted"].append("consents")
            
            # Anonymize conversations
            await self._anonymize_conversations(dsr.user_id)
            results["anonymized"].append("conversations")
            
            # Retain audit logs (legal obligation)
            results["retained"].append("audit_logs (legal obligation)")
            
            # Mark as completed
            dsr.status = DSRStatus.COMPLETED.value
            dsr.completed_at = datetime.utcnow()
            dsr.records_affected = str(
                len(results["deleted"]) + len(results["anonymized"])
            )
            dsr.result_summary = f"Deleted: {len(results['deleted'])}, Anonymized: {len(results['anonymized'])}, Retained: {len(results['retained'])}"
            dsr.result_details = json.dumps(results)
            
            await self.session.commit()
            
            # Log completion
            if self.audit_logger:
                await self.audit_logger.log(
                    action=AuditAction.DATA_DELETION,
                    resource_type=ResourceType.USER,
                    resource_id=dsr.user_id,
                    user_id=dsr.user_id,
                    metadata={
                        "dsr_id": dsr.id,
                        "request_number": dsr.request_number,
                        "results": results,
                    }
                )
            
            return results
            
        except Exception as e:
            dsr.status = DSRStatus.FAILED.value
            dsr.result_summary = f"Failed: {str(e)}"
            await self.session.commit()
            raise
    
    async def handle_portability_request(
        self,
        dsr: DataSubjectRequest,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Handle a data portability request (GDPR Article 20).
        
        Exports data in a structured, machine-readable format.
        
        Returns:
            Data in portable format
        """
        # Similar to access request but formatted for portability
        data = await self.handle_access_request(dsr)
        
        # Format based on requested format
        if format.lower() == "csv":
            # Convert to CSV format
            data = self._convert_to_csv_format(data)
        elif format.lower() == "xml":
            # Convert to XML format
            data = self._convert_to_xml_format(data)
        
        return data
    
    # === Anonymization Methods ===
    
    async def anonymize_user(
        self,
        user: User,
        strategy: AnonymizationStrategy = AnonymizationStrategy.HASH,
    ) -> None:
        """
        Anonymize a user record.
        
        Replaces PII with anonymized values while preserving record for audit.
        """
        if strategy == AnonymizationStrategy.HASH:
            # Hash identifying fields
            user.email = self._hash_value(user.email)
            user.name = f"Anonymized User {user.id[:6]}"
            user.avatar_url = None
            user.password_hash = None
            user.saml_subject_id = self._hash_value(user.saml_subject_id) if user.saml_subject_id else None
            user.oauth_provider_id = None
            user.oauth_access_token = None
            user.oauth_refresh_token = None
            user.mfa_secret = None
            user.mfa_backup_codes = None
            user.last_login_ip = None
            
        elif strategy == AnonymizationStrategy.NULL:
            # Set to null
            user.email = None
            user.name = None
            user.avatar_url = None
            user.password_hash = None
            user.saml_subject_id = None
            
        elif strategy == AnonymizationStrategy.DELETE:
            # Hard delete (use with caution)
            await self.session.delete(user)
        
        user.is_active = False
        await self.session.commit()
        
        logger.info(f"User {user.id} anonymized using {strategy.value}")
    
    def _hash_value(self, value: str) -> str:
        """Create one-way hash of a value."""
        if not value:
            return None
        return hashlib.sha256(f"{value}_salt".encode()).hexdigest()[:16]
    
    # === Consent Management ===
    
    async def record_consent(
        self,
        user: User,
        consent_type: ConsentType,
        granted: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        privacy_policy_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Consent:
        """Record or update user consent."""
        # Check for existing consent
        result = await self.session.execute(
            select(Consent).where(
                and_(
                    Consent.user_id == user.id,
                    Consent.consent_type == consent_type.value
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing consent
            if granted:
                existing.status = ConsentStatus.GRANTED.value
                existing.granted_at = datetime.utcnow()
            else:
                existing.revoke(ip_address, user_agent)
            
            if privacy_policy_version:
                existing.privacy_policy_version = privacy_policy_version
            
            await self.session.commit()
            return existing
        else:
            # Create new consent
            consent = Consent(
                user_id=user.id,
                organization_id=user.organization_id,
                consent_type=consent_type.value,
                status=ConsentStatus.GRANTED.value if granted else ConsentStatus.REVOKED.value,
                granted_at=datetime.utcnow() if granted else None,
                privacy_policy_version=privacy_policy_version,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )
            
            self.session.add(consent)
            await self.session.commit()
            return consent
    
    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """Check if user has valid consent for a specific type."""
        result = await self.session.execute(
            select(Consent).where(
                and_(
                    Consent.user_id == user_id,
                    Consent.consent_type == consent_type.value,
                    Consent.status == ConsentStatus.GRANTED.value
                )
            )
        )
        consent = result.scalar_one_or_none()
        
        if not consent:
            return False
        
        return consent.is_valid()
    
    async def revoke_all_consents(self, user_id: str) -> int:
        """Revoke all consents for a user."""
        result = await self.session.execute(
            select(Consent).where(
                and_(
                    Consent.user_id == user_id,
                    Consent.status == ConsentStatus.GRANTED.value
                )
            )
        )
        consents = result.scalars().all()
        
        for consent in consents:
            consent.revoke()
        
        await self.session.commit()
        return len(consents)
    
    # === Helper Methods ===
    
    async def _get_consent_data(self, user_id: str) -> List[Dict]:
        """Get consent history for user."""
        result = await self.session.execute(
            select(Consent).where(Consent.user_id == user_id)
        )
        consents = result.scalars().all()
        return [c.to_dict() for c in consents]
    
    async def _get_audit_log_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of audit logs for user."""
        # Return summary only, not full logs (for privacy)
        from sqlalchemy import func
        from ...models.audit_log import AuditLog
        
        result = await self.session.execute(
            select(
                AuditLog.action,
                func.count(AuditLog.id).label("count")
            ).where(
                AuditLog.user_id == user_id
            ).group_by(AuditLog.action)
        )
        
        return {
            "action_summary": {row.action: row.count for row in result},
            "total_events": sum(row.count for row in result),
        }
    
    async def _get_campaign_data(self, user_id: str) -> List[Dict]:
        """Get campaign data created by user."""
        # Placeholder - implement based on your Campaign model
        return []
    
    async def _get_asset_data(self, user_id: str) -> List[Dict]:
        """Get asset data created by user."""
        # Placeholder - implement based on your Asset model
        return []
    
    async def _get_conversation_data(self, user_id: str) -> List[Dict]:
        """Get conversation data for user."""
        # Placeholder - implement based on your Conversation model
        return []
    
    async def _delete_consents(self, user_id: str) -> int:
        """Delete all consent records for user."""
        result = await self.session.execute(
            select(Consent).where(Consent.user_id == user_id)
        )
        consents = result.scalars().all()
        
        for consent in consents:
            await self.session.delete(consent)
        
        await self.session.commit()
        return len(consents)
    
    async def _anonymize_conversations(self, user_id: str) -> int:
        """Anonymize conversation data for user."""
        # Placeholder - implement based on your Conversation model
        return 0
    
    def _convert_to_csv_format(self, data: Dict) -> str:
        """Convert data to CSV format for portability."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Flatten nested data
        flat_data = self._flatten_dict(data)
        
        for key, value in flat_data.items():
            writer.writerow([key, value])
        
        return output.getvalue()
    
    def _convert_to_xml_format(self, data: Dict) -> str:
        """Convert data to XML format for portability."""
        # Simple XML conversion
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<data>"]
        
        def dict_to_xml(d, indent=2):
            for key, value in d.items():
                safe_key = str(key).replace(" ", "_").replace("<", "").replace(">", "")
                if isinstance(value, dict):
                    xml_parts.append(f"{' ' * indent}<{safe_key}>")
                    dict_to_xml(value, indent + 2)
                    xml_parts.append(f"{' ' * indent}</{safe_key}>")
                elif isinstance(value, list):
                    xml_parts.append(f"{' ' * indent}<{safe_key}>")
                    for item in value:
                        if isinstance(item, dict):
                            xml_parts.append(f"{' ' * (indent + 2)}<item>")
                            dict_to_xml(item, indent + 4)
                            xml_parts.append(f"{' ' * (indent + 2)}</item>")
                        else:
                            xml_parts.append(f"{' ' * (indent + 2)}<item>{item}</item>")
                    xml_parts.append(f"{' ' * indent}</{safe_key}>")
                else:
                    xml_parts.append(f"{' ' * indent}<{safe_key}>{value}</{safe_key}>")
        
        dict_to_xml(data)
        xml_parts.append("</data>")
        
        return "\n".join(xml_parts)
    
    def _flatten_dict(self, d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _generate_request_number(self) -> str:
        """Generate unique request number."""
        timestamp = datetime.utcnow()
        random_suffix = secrets.token_hex(4).upper()
        return f"DSR-{timestamp.year}-{timestamp.month:02d}-{random_suffix}"


# Singleton instance for dependency injection
_gdpr_manager: Optional[GDPRManager] = None


def get_gdpr_manager(session: AsyncSession, audit_logger: Optional[AuditLogger] = None) -> GDPRManager:
    """Get or create GDPR manager instance."""
    global _gdpr_manager
    if _gdpr_manager is None:
        _gdpr_manager = GDPRManager(session, audit_logger)
    else:
        _gdpr_manager.session = session
        _gdpr_manager.audit_logger = audit_logger
    return _gdpr_manager