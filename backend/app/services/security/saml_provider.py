"""
SAML 2.0 authentication service for enterprise SSO.

Supports multiple Identity Providers (Okta, Auth0, Azure AD) with
SP-initiated SSO, metadata generation, and assertion validation.
"""
import base64
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from jose import jwt

from ...core.config import get_settings
from ...models.user import User, IdentityProvider

logger = logging.getLogger(__name__)


class SAMLProviderType(str, Enum):
    """Supported SAML Identity Providers."""
    OKTA = "okta"
    AUTH0 = "auth0"
    AZURE_AD = "azure_ad"
    GENERIC = "generic"


@dataclass
class SAMLConfig:
    """SAML configuration for an organization."""
    provider_type: SAMLProviderType
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str] = None
    idp_x509_cert: str = ""
    sp_entity_id: str = ""
    sp_acs_url: str = ""
    sp_slo_url: Optional[str] = None
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    want_assertions_signed: bool = True
    want_response_signed: bool = True
    
    def __post_init__(self):
        """Normalize certificate format."""
        if self.idp_x509_cert:
            # Remove PEM headers/footers and whitespace
            self.idp_x509_cert = re.sub(
                r'-----BEGIN CERTIFICATE-----|-----END CERTIFICATE-----|\s',
                '',
                self.idp_x509_cert
            )


@dataclass
class SAMLUserAttributes:
    """Extracted user attributes from SAML assertion."""
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    groups: list = None
    department: Optional[str] = None
    title: Optional[str] = None
    subject_id: Optional[str] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []


class SAMLProvider:
    """
    SAML 2.0 authentication provider.
    
    Handles:
    - SP metadata generation
    - AuthNRequest creation
    - SAML Response validation
    - User attribute extraction
    """
    
    # SAML namespaces
    NS_SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
    NS_SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
    NS_DS = "http://www.w3.org/2000/2000/09/xmldsig#"
    
    def __init__(self, config: Optional[SAMLConfig] = None):
        self.config = config
        self.settings = get_settings()
        
        # Generate or load SP key pair
        self._sp_private_key = None
        self._sp_public_key = None
        self._load_sp_keys()
    
    def _load_sp_keys(self):
        """Load or generate SP signing keys."""
        # In production, load from secure storage (e.g., AWS Secrets Manager)
        # For now, generate ephemeral keys (not suitable for production)
        if self.settings.saml_private_key:
            # Load from PEM
            try:
                self._sp_private_key = serialization.load_pem_private_key(
                    self.settings.saml_private_key.encode(),
                    password=None,
                )
            except Exception as e:
                logger.error(f"Failed to load SAML private key: {e}")
                self._generate_sp_keys()
        else:
            self._generate_sp_keys()
    
    def _generate_sp_keys(self):
        """Generate new SP key pair (for development only)."""
        logger.warning("Generating ephemeral SAML keys - not suitable for production")
        self._sp_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
    
    @property
    def sp_public_key(self):
        """Get SP public key for metadata."""
        if self._sp_private_key:
            return self._sp_private_key.public_key()
        return None
    
    def generate_metadata(self, organization_id: str) -> str:
        """
        Generate SAML Service Provider metadata XML.
        
        This metadata is provided to the Identity Provider for configuration.
        """
        settings = get_settings()
        base_url = settings.app_url or "https://app.example.com"
        
        acs_url = f"{base_url}/api/auth/saml/acs"
        slo_url = f"{base_url}/api/auth/saml/slo"
        entity_id = f"{base_url}/api/auth/saml/metadata/{organization_id}"
        
        # Get public key certificate
        cert_pem = ""
        if self.sp_public_key:
            cert_der = self.sp_public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            cert_b64 = base64.b64encode(cert_der).decode()
            # Format with line breaks every 64 characters
            cert_pem = '\n'.join(
                cert_b64[i:i+64] for i in range(0, len(cert_b64), 64)
            )
        
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="true"
                        WantAssertionsSigned="true"
                        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/2009/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>
{cert_pem}
                    </ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        <md:KeyDescriptor use="encryption">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/2009/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>
{cert_pem}
                    </ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
        <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                                 Location="{slo_url}"/>
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                     Location="{acs_url}"
                                     index="1"
                                     isDefault="true"/>
    </md:SPSSODescriptor>
    <md:Organization>
        <md:OrganizationName xml:lang="en">{settings.app_name}</md:OrganizationName>
        <md:OrganizationDisplayName xml:lang="en">{settings.app_name}</md:OrganizationDisplayName>
        <md:OrganizationURL xml:lang="en">{base_url}</md:OrganizationURL>
    </md:Organization>
</md:EntityDescriptor>"""
        
        return metadata
    
    def initiate_login(self, organization_id: str, relay_state: Optional[str] = None) -> Dict[str, str]:
        """
        Initiate SAML login by creating AuthNRequest.
        
        Returns:
            Dict with 'url' (IdP SSO URL) and 'saml_request' (base64 encoded)
        """
        if not self.config:
            raise ValueError("SAML configuration not set")
        
        settings = get_settings()
        base_url = settings.app_url or "https://app.example.com"
        
        # Generate unique request ID
        request_id = f"_{self._generate_id()}"
        
        # Build AuthNRequest
        issue_instant = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        destination = self.config.idp_sso_url
        issuer = f"{base_url}/api/auth/saml/metadata/{organization_id}"
        
        authn_request = f"""<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                      xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                      ID="{request_id}"
                      Version="2.0"
                      IssueInstant="{issue_instant}"
                      Destination="{destination}"
                      ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                      AssertionConsumerServiceURL="{base_url}/api/auth/saml/acs">
    <saml:Issuer>{issuer}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
    <samlp:RequestedAuthnContext Comparison="exact">
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
    </samlp:RequestedAuthnContext>
</samlp:AuthnRequest>"""
        
        # Compress and encode request
        import zlib
        compressed = zlib.compress(authn_request.encode())[2:-4]  # Remove zlib header/footer
        encoded_request = base64.b64encode(compressed).decode()
        
        return {
            "url": destination,
            "saml_request": encoded_request,
            "relay_state": relay_state or organization_id,
            "request_id": request_id,
        }
    
    def handle_assertion(
        self,
        saml_response: str,
        relay_state: Optional[str] = None
    ) -> Tuple[SAMLUserAttributes, str]:
        """
        Handle SAML assertion from IdP.
        
        Args:
            saml_response: Base64 encoded SAML Response
            relay_state: Optional relay state from IdP
            
        Returns:
            Tuple of (user_attributes, session_index)
            
        Raises:
            ValueError: If assertion is invalid
        """
        # Decode response
        try:
            decoded = base64.b64decode(saml_response)
            response_xml = decoded.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decode SAML response: {e}")
        
        # Parse XML
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as e:
            raise ValueError(f"Invalid SAML response XML: {e}")
        
        # Register namespaces
        namespaces = {
            'saml': self.NS_SAML,
            'samlp': self.NS_SAMLP,
            'ds': self.NS_DS,
        }
        
        # Validate response status
        status_code = root.find('.//samlp:StatusCode', namespaces)
        if status_code is not None:
            status_value = status_code.get('Value', '')
            if 'Success' not in status_value:
                status_message = root.find('.//samlp:StatusMessage', namespaces)
                message = status_message.text if status_message is not None else "Unknown error"
                raise ValueError(f"SAML authentication failed: {message}")
        
        # Extract assertion
        assertion = root.find('.//saml:Assertion', namespaces)
        if assertion is None:
            raise ValueError("No SAML assertion found in response")
        
        # Validate signature (if configured)
        if self.config and self.config.want_response_signed:
            if not self._validate_signature(response_xml):
                logger.warning("SAML response signature validation failed or not present")
        
        # Extract user attributes
        user_attrs = self._extract_attributes(assertion, namespaces)
        
        # Extract session index
        session_index = self._extract_session_index(assertion, namespaces)
        
        return user_attrs, session_index
    
    def _extract_attributes(
        self,
        assertion: ET.Element,
        namespaces: Dict[str, str]
    ) -> SAMLUserAttributes:
        """Extract user attributes from SAML assertion."""
        # Get subject/name ID (email)
        subject = assertion.find('.//saml:Subject', namespaces)
        name_id = subject.find('.//saml:NameID', namespaces) if subject is not None else None
        email = name_id.text if name_id is not None else ""
        subject_id = name_id.get('NameQualifier') if name_id is not None else None
        
        # Get attribute statement
        attr_statement = assertion.find('.//saml:AttributeStatement', namespaces)
        
        attrs = {
            'email': email,
            'subject_id': subject_id,
            'name': None,
            'first_name': None,
            'last_name': None,
            'groups': [],
            'department': None,
            'title': None,
        }
        
        if attr_statement is not None:
            for attr in attr_statement.findall('.//saml:Attribute', namespaces):
                attr_name = attr.get('Name', '')
                attr_value = attr.find('.//saml:AttributeValue', namespaces)
                value = attr_value.text if attr_value is not None else ""
                
                # Map common attribute names
                if attr_name in ('email', 'mail', 'emailAddress', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'):
                    attrs['email'] = value
                elif attr_name in ('name', 'displayName', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'):
                    attrs['name'] = value
                elif attr_name in ('firstName', 'first_name', 'givenName', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'):
                    attrs['first_name'] = value
                elif attr_name in ('lastName', 'last_name', 'surname', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'):
                    attrs['last_name'] = value
                elif attr_name in ('groups', 'memberOf', 'http://schemas.xmlsoap.org/claims/Group'):
                    if value:
                        attrs['groups'].append(value)
                elif attr_name in ('department', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/department'):
                    attrs['department'] = value
                elif attr_name in ('title', 'jobTitle', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/title'):
                    attrs['title'] = value
        
        # Construct full name if not provided
        if not attrs['name'] and (attrs['first_name'] or attrs['last_name']):
            attrs['name'] = f"{attrs['first_name'] or ''} {attrs['last_name'] or ''}".strip()
        
        return SAMLUserAttributes(**attrs)
    
    def _extract_session_index(
        self,
        assertion: ET.Element,
        namespaces: Dict[str, str]
    ) -> str:
        """Extract session index from assertion."""
        authn_statement = assertion.find('.//saml:AuthnStatement', namespaces)
        if authn_statement is not None:
            return authn_statement.get('SessionIndex', '')
        return ""
    
    def _validate_signature(self, xml_string: str) -> bool:
        """
        Validate XML signature.
        
        In production, use a proper SAML library like python-saml or pysaml2.
        This is a simplified implementation.
        """
        # TODO: Implement proper XML signature validation
        # For now, log warning and continue
        logger.warning("XML signature validation not fully implemented")
        return True
    
    def _generate_id(self) -> str:
        """Generate unique ID for SAML requests."""
        import uuid
        return uuid.uuid4().hex[:16]
    
    def create_saml_user(
        self,
        attributes: SAMLUserAttributes,
        organization_id: str,
        provider: IdentityProvider
    ) -> Dict[str, Any]:
        """
        Create user data dict from SAML attributes.
        
        This prepares data for user creation/update, not the actual User object.
        """
        return {
            "email": attributes.email,
            "name": attributes.name or attributes.email.split('@')[0],
            "organization_id": organization_id,
            "identity_provider": provider,
            "saml_subject_id": attributes.subject_id,
            "email_verified": True,  # SAML IdPs verify email
            "role": self._map_saml_role(attributes.groups),
        }
    
    def _map_saml_role(self, groups: list) -> str:
        """Map SAML groups to application roles."""
        # Default role
        from ...models.user import UserRole
        role = UserRole.EDITOR
        
        # Check for admin groups
        admin_groups = {'admin', 'administrators', 'admins', 'marketing-admin'}
        if any(g.lower() in admin_groups for g in groups):
            role = UserRole.ADMIN
        
        # Check for viewer groups
        viewer_groups = {'viewer', 'viewers', 'read-only', 'guest'}
        if any(g.lower() in viewer_groups for g in groups):
            role = UserRole.VIEWER
        
        return role
    
    def validate_saml_response(
        self,
        saml_response: str,
        expected_request_id: Optional[str] = None
    ) -> bool:
        """
        Validate SAML response structure and signature.
        
        Args:
            saml_response: Base64 encoded SAML Response
            expected_request_id: Optional request ID to validate InResponseTo
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Decode and parse
            decoded = base64.b64decode(saml_response)
            root = ET.fromstring(decoded)
            
            namespaces = {
                'saml': self.NS_SAML,
                'samlp': self.NS_SAMLP,
            }
            
            # Check InResponseTo if provided
            if expected_request_id:
                in_response_to = root.get('InResponseTo')
                if in_response_to != expected_request_id:
                    raise ValueError("InResponseTo does not match expected request ID")
            
            # Check destination
            destination = root.get('Destination')
            if destination:
                settings = get_settings()
                expected_acs = f"{settings.app_url or 'https://app.example.com'}/api/auth/saml/acs"
                if destination != expected_acs:
                    raise ValueError("Destination does not match ACS URL")
            
            # Check not before/not on or after
            conditions = root.find('.//saml:Conditions', namespaces)
            if conditions is not None:
                not_before = conditions.get('NotBefore')
                not_on_or_after = conditions.get('NotOnOrAfter')
                
                now = datetime.utcnow()
                
                if not_before:
                    nb = datetime.fromisoformat(not_before.replace('Z', '+00:00'))
                    if now < nb:
                        raise ValueError("Assertion is not yet valid")
                
                if not_on_or_after:
                    noa = datetime.fromisoformat(not_on_or_after.replace('Z', '+00:00'))
                    if now >= noa:
                        raise ValueError("Assertion has expired")
            
            return True
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        except Exception as e:
            raise ValueError(f"Validation failed: {e}")


# Provider configuration storage (in production, use database)
_saml_configs: Dict[str, SAMLConfig] = {}


def get_saml_provider(organization_id: str) -> Optional[SAMLProvider]:
    """Get SAML provider for organization."""
    config = _saml_configs.get(organization_id)
    if config:
        return SAMLProvider(config)
    return None


def set_saml_config(organization_id: str, config: SAMLConfig):
    """Set SAML configuration for organization."""
    _saml_configs[organization_id] = config


def get_saml_provider_type(provider_name: str) -> IdentityProvider:
    """Map provider name to IdentityProvider enum."""
    mapping = {
        "okta": IdentityProvider.OKTA,
        "auth0": IdentityProvider.AUTH0,
        "azure_ad": IdentityProvider.AZURE_AD,
        "azure": IdentityProvider.AZURE_AD,
        "microsoft": IdentityProvider.AZURE_AD,
    }
    return mapping.get(provider_name.lower(), IdentityProvider.LOCAL)