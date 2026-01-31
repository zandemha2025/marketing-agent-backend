"""
Authentication API endpoints.

JWT-based authentication with register, login, and user management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.database import get_session
from ..repositories.user import UserRepository
from ..models.user import User, UserRole

router = APIRouter()
security = HTTPBearer()
# Use bcrypt directly to avoid passlib compatibility issues
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly."""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# === Pydantic Models ===

class UserRegisterRequest(BaseModel):
    """Request to register a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    organization_name: Optional[str] = Field(None, description="Optional organization name")


class UserLoginRequest(BaseModel):
    """Request to login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    name: str
    role: str
    organization_id: str
    is_active: bool
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# === Helper Functions ===

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return _verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return _hash_password(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Get the current authenticated user from JWT token."""
    import logging
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("JWT token missing 'sub' claim")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception

    repo = UserRepository(session)
    user = await repo.get(user_id)

    if user is None:
        logger.warning(f"User not found for id: {user_id}")
        raise credentials_exception

    logger.debug(f"Auth: User {user.id} (org: {user.organization_id}, active: {user.is_active}, provider: {user.identity_provider})")

    if not user.is_active:
        logger.warning(f"User {user.id} account is deactivated")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# === Auth Endpoints ===

@router.post("/register", response_model=TokenResponse)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_session)
):
    """Register a new user and organization."""
    settings = get_settings()
    user_repo = UserRepository(session)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization first
    from ..repositories.organization import OrganizationRepository
    org_repo = OrganizationRepository(session)

    org_name = request.organization_name or f"{request.name}'s Organization"
    org_slug = org_name.lower().replace(" ", "-").replace("'", "")[:50]

    # Ensure unique slug
    import uuid
    org_slug = f"{org_slug}-{uuid.uuid4().hex[:8]}"

    organization = await org_repo.create(
        name=org_name,
        slug=org_slug,
        domain=None
    )

    # Create user
    password_hash = get_password_hash(request.password)
    user = await user_repo.create_user(
        email=request.email,
        name=request.name,
        organization_id=organization.id,
        password_hash=password_hash,
        role=UserRole.ADMIN,  # First user is admin
    )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "org_id": organization.id},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "organization_id": user.organization_id,
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """Login and get access token."""
    settings = get_settings()
    user_repo = UserRepository(session)

    # Find user by email
    user = await user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user has a password (might be OAuth-only)
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "org_id": user.organization_id},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "organization_id": user.organization_id,
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Change user password."""
    user_repo = UserRepository(session)

    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash and update new password
    new_password_hash = get_password_hash(request.new_password)
    await user_repo.update_password(current_user.id, new_password_hash)

    return {"message": "Password updated successfully"}


@router.post("/logout")
async def logout():
    """Logout (client should discard token)."""
    return {"message": "Logged out successfully"}


# === SAML SSO Endpoints ===

class SAMLLoginRequest(BaseModel):
    """Request to initiate SAML login."""
    organization_id: Optional[str] = Field(None, description="Organization ID for SSO")


class SAMLLoginResponse(BaseModel):
    """SAML login initiation response."""
    sso_url: str
    saml_request: str
    relay_state: str


class SAMLACSRequest(BaseModel):
    """SAML Assertion Consumer Service request."""
    SAMLResponse: str = Field(..., description="Base64 encoded SAML Response")
    RelayState: Optional[str] = Field(None, description="Relay state from IdP")


class SAMLConfigureRequest(BaseModel):
    """Request to configure SAML for organization."""
    provider_type: str = Field(..., description="IdP type: okta, auth0, azure_ad")
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str] = None
    idp_x509_cert: str
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


@router.post("/saml/login", response_model=SAMLLoginResponse)
async def saml_login(
    request: SAMLLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Initiate SAML login flow.
    
    Returns SAML request data to be sent to the Identity Provider.
    The client should redirect to the IdP SSO URL with the SAMLRequest parameter.
    """
    from ..services.security.saml_provider import (
        SAMLProvider, SAMLConfig, get_saml_provider, set_saml_config
    )
    from ..repositories.organization import OrganizationRepository
    
    if not request.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required for SAML login"
        )
    
    # Get SAML provider for organization
    saml_provider = get_saml_provider(request.organization_id)
    
    if not saml_provider:
        # Check if organization exists
        org_repo = OrganizationRepository(session)
        org = await org_repo.get(request.organization_id)
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML SSO is not configured for this organization"
        )
    
    # Initiate login
    login_data = saml_provider.initiate_login(
        organization_id=request.organization_id
    )
    
    return SAMLLoginResponse(
        sso_url=login_data["url"],
        saml_request=login_data["saml_request"],
        relay_state=login_data["relay_state"],
    )


@router.post("/saml/acs", response_model=TokenResponse)
async def saml_acs(
    request: SAMLACSRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    SAML Assertion Consumer Service (ACS).
    
    Receives and validates the SAML response from the Identity Provider,
    creates or updates the user, and returns a JWT token.
    """
    from datetime import datetime
    from ..services.security.saml_provider import (
        get_saml_provider, SAMLProvider, get_saml_provider_type
    )
    from ..services.security.audit_logger import get_audit_logger, AuditAction, ResourceType
    from ..repositories.user import UserRepository
    from ..repositories.organization import OrganizationRepository
    
    settings = get_settings()
    user_repo = UserRepository(session)
    audit_logger = get_audit_logger(session)
    
    # Extract organization from relay state
    organization_id = request.RelayState
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RelayState (organization_id) is required"
        )
    
    # Get SAML provider
    saml_provider = get_saml_provider(organization_id)
    if not saml_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAML SSO is not configured for this organization"
        )
    
    try:
        # Handle SAML assertion
        user_attrs, session_index = saml_provider.handle_assertion(
            saml_response=request.SAMLResponse,
            relay_state=request.RelayState
        )
        
        if not user_attrs.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML assertion missing email attribute"
            )
        
        # Find or create user
        user = await user_repo.get_by_email(user_attrs.email)
        
        provider = get_saml_provider_type(saml_provider.config.provider_type.value)
        
        if user:
            # Update existing user
            user.saml_subject_id = user_attrs.subject_id
            user.identity_provider = provider
            user.last_sso_login = datetime.utcnow()
            user.sso_session_index = session_index
            user.email_verified = True
            
            # Update name if provided
            if user_attrs.name and not user.name:
                user.name = user_attrs.name
            
            await session.commit()
        else:
            # Create new user
            org_repo = OrganizationRepository(session)
            org = await org_repo.get(organization_id)
            
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )
            
            # Create user with SSO data
            user_data = saml_provider.create_saml_user(
                attributes=user_attrs,
                organization_id=organization_id,
                provider=provider
            )
            
            user = await user_repo.create_user(
                email=user_data["email"],
                name=user_data["name"],
                organization_id=user_data["organization_id"],
                role=user_data["role"],
                identity_provider=user_data["identity_provider"],
                saml_subject_id=user_data["saml_subject_id"],
                email_verified=True,
            )
            
            user.last_sso_login = datetime.utcnow()
            user.sso_session_index = session_index
            await session.commit()
        
        # Log successful SAML login
        await audit_logger.log_login(
            user_id=user.id,
            user_email=user.email,
            organization_id=user.organization_id,
            success=True,
            auth_method=f"saml_{provider.value}",
            saml_session_index=session_index,
        )
        
        # Create JWT token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "org_id": user.organization_id,
                "auth_method": "saml"
            },
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "organization_id": user.organization_id,
                "identity_provider": user.identity_provider.value,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log failed SAML login
        await audit_logger.log_login(
            user_id=None,
            user_email=user_attrs.email if 'user_attrs' in locals() else None,
            organization_id=organization_id,
            success=False,
            failure_reason=str(e),
            auth_method="saml",
        )
        
        logger.error(f"SAML ACS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SAML authentication failed: {str(e)}"
        )


@router.get("/saml/metadata/{organization_id}")
async def saml_metadata(
    organization_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get SAML Service Provider metadata for an organization.
    
    This metadata should be provided to the Identity Provider for configuration.
    """
    from ..services.security.saml_provider import SAMLProvider
    from ..repositories.organization import OrganizationRepository
    from fastapi.responses import Response
    
    # Verify organization exists
    org_repo = OrganizationRepository(session)
    org = await org_repo.get(organization_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Generate metadata
    provider = SAMLProvider()
    metadata = provider.generate_metadata(organization_id)
    
    return Response(
        content=metadata,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=saml-metadata-{organization_id}.xml"
        }
    )


@router.post("/saml/configure")
async def saml_configure(
    request: SAMLConfigureRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Configure SAML SSO for an organization.
    
    Requires admin role. Stores the IdP configuration for the user's organization.
    """
    from ..services.security.saml_provider import (
        SAMLConfig, SAMLProviderType, set_saml_config
    )
    from ..services.security.audit_logger import get_audit_logger, AuditAction, ResourceType
    
    # Only admins can configure SAML
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to configure SAML"
        )
    
    # Validate provider type
    try:
        provider_type = SAMLProviderType(request.provider_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider type. Must be one of: {[p.value for p in SAMLProviderType]}"
        )
    
    settings = get_settings()
    base_url = settings.app_url or "https://app.example.com"
    
    # Create SAML config
    config = SAMLConfig(
        provider_type=provider_type,
        idp_entity_id=request.idp_entity_id,
        idp_sso_url=request.idp_sso_url,
        idp_slo_url=request.idp_slo_url,
        idp_x509_cert=request.idp_x509_cert,
        sp_entity_id=f"{base_url}/api/auth/saml/metadata/{current_user.organization_id}",
        sp_acs_url=f"{base_url}/api/auth/saml/acs",
        sp_slo_url=f"{base_url}/api/auth/saml/slo",
        name_id_format=request.name_id_format,
    )
    
    # Store configuration
    set_saml_config(current_user.organization_id, config)
    
    # Log configuration change
    audit_logger = get_audit_logger(session)
    await audit_logger.log(
        action=AuditAction.SAML_METADATA_UPDATED,
        resource_type=ResourceType.ORGANIZATION,
        resource_id=current_user.organization_id,
        user_id=current_user.id,
        user_email=current_user.email,
        organization_id=current_user.organization_id,
        metadata={
            "provider_type": provider_type.value,
            "idp_entity_id": request.idp_entity_id,
        }
    )
    
    return {
        "message": "SAML configuration saved successfully",
        "organization_id": current_user.organization_id,
        "provider_type": provider_type.value,
        "metadata_url": f"/api/auth/saml/metadata/{current_user.organization_id}",
    }
