"""
User Management API endpoints.

Provides endpoints for:
- Listing users in an organization
- Inviting new users
- Updating user details
- Deactivating/activating users
- Role-based access control
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr, Field
import logging
import uuid

from ..core.database import get_session
from ..core.config import get_settings
from ..models.user import User, UserRole, Organization
from ..repositories.user import UserRepository
from ..repositories.organization import OrganizationRepository
from ..api.auth import get_current_user, get_password_hash

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


# --- Request/Response Models ---

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.EDITOR
    send_invite: bool = True


class UserCreateWithPassword(BaseModel):
    """For creating a user with a password (admin only)."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole = UserRole.EDITOR


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    preferences: Optional[dict] = None


class UserUpdateSelf(BaseModel):
    """Fields a user can update on their own profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    preferences: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    email_verified: bool
    avatar_url: Optional[str] = None
    organization_id: str
    preferences: dict
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.EDITOR
    message: Optional[str] = None


class InviteResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    invite_token: Optional[str] = None
    message: str


class RoleInfo(BaseModel):
    role: str
    name: str
    description: str
    permissions: List[str]


# --- Permission Helpers ---

def check_admin_access(current_user: User):
    """Check if user has admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def check_self_or_admin(current_user: User, target_user_id: str):
    """Check if user is admin or modifying their own account."""
    if current_user.role != UserRole.ADMIN and current_user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only modify your own profile or admin access required"
        )


# --- Endpoints ---

@router.get("/", response_model=UserListResponse)
async def list_users(
    organization_id: str,
    page: int = 1,
    page_size: int = 20,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    List all users in an organization.
    
    Requires admin role.
    """
    check_admin_access(current_user)
    
    # Verify user belongs to this organization
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this organization"
        )
    
    # Build query
    query = select(User).where(User.organization_id == organization_id)
    
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Get total count
    count_result = await session.execute(
        select(func.count(User.id)).where(User.organization_id == organization_id)
    )
    total = count_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's information."""
    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific user's details.
    
    Users can view their own profile. Admins can view any user in their organization.
    """
    # Users can view themselves
    if current_user.id == user_id:
        return UserResponse.model_validate(current_user)
    
    # Otherwise need admin access
    check_admin_access(current_user)
    
    repo = UserRepository(session)
    user = await repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Can only view users in same organization
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return UserResponse.model_validate(user)


@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    invite: InviteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Invite a new user to the organization.
    
    Creates a user account and sends an invitation email.
    Requires admin role.
    """
    check_admin_access(current_user)
    
    repo = UserRepository(session)
    
    # Check if email already exists
    existing = await repo.get_by_email(invite.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate a temporary password/invite token
    invite_token = uuid.uuid4().hex[:32]
    temp_password_hash = get_password_hash(invite_token)
    
    # Create the user
    try:
        new_user = await repo.create_user(
            email=invite.email,
            name=invite.name,
            organization_id=current_user.organization_id,
            password_hash=temp_password_hash,
            role=invite.role,
            is_active=True
        )
        
        await session.commit()
        
        # FIXME: Email notification not implemented
        # Required: Integrate with email service (SendGrid, AWS SES, etc.)
        # The invite_token should be sent via email with a link like:
        # {frontend_url}/accept-invite?token={invite_token}
        # For now, the token is returned in the response (development only)
        logger.warning(
            f"EMAIL NOT SENT: Invitation for {invite.email} to organization "
            f"{current_user.organization_id}. Token: {invite_token[:8]}..."
        )
        
        return InviteResponse(
            success=True,
            user_id=new_user.id,
            invite_token=invite_token,  # In production, this would be sent via email only
            message=f"Invitation sent to {invite.email}"
        )
        
    except Exception as e:
        logger.error(f"Failed to invite user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreateWithPassword,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new user with a password (admin only).
    
    This is for admin-created accounts where the admin sets the initial password.
    """
    check_admin_access(current_user)
    
    repo = UserRepository(session)
    
    # Check if email already exists
    existing = await repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = get_password_hash(user_data.password)
    
    try:
        new_user = await repo.create_user(
            email=user_data.email,
            name=user_data.name,
            organization_id=current_user.organization_id,
            password_hash=password_hash,
            role=user_data.role,
            is_active=True
        )
        
        await session.commit()
        
        return UserResponse.model_validate(new_user)
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update a user's details.
    
    Users can update their own profile (except role).
    Admins can update any user in their organization.
    """
    # Check permissions
    check_self_or_admin(current_user, user_id)
    
    repo = UserRepository(session)
    user = await repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Can only update users in same organization
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        
        )
    
    # Non-admins cannot change role
    if update_data.role is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )
    
    # Non-admins cannot deactivate themselves or others
    if update_data.is_active is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can activate/deactivate users"
        )
    
    # Admins cannot remove their own admin role if they're the last admin
    if (update_data.role is not None and 
        update_data.role != UserRole.ADMIN and 
        user.id == current_user.id):
        # Check if there are other admins
        admins = await repo.get_admins(current_user.organization_id)
        if len(admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin role from the last admin"
            )
    
    # Build update dict
    update_dict = {}
    if update_data.name is not None:
        update_dict["name"] = update_data.name
    if update_data.role is not None:
        update_dict["role"] = update_data.role
    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active
    if update_data.preferences is not None:
        # Merge preferences
        merged = {**user.preferences, **update_data.preferences}
        update_dict["preferences"] = merged
    
    try:
        updated_user = await repo.update(user_id, **update_dict)
        await session.commit()
        
        return UserResponse.model_validate(updated_user)
        
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.put("/me/profile", response_model=UserResponse)
async def update_own_profile(
    update_data: UserUpdateSelf,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update current user's own profile."""
    repo = UserRepository(session)
    
    update_dict = {}
    if update_data.name is not None:
        update_dict["name"] = update_data.name
    if update_data.preferences is not None:
        merged = {**current_user.preferences, **update_data.preferences}
        update_dict["preferences"] = merged
    
    try:
        updated_user = await repo.update(current_user.id, **update_dict)
        await session.commit()
        
        return UserResponse.model_validate(updated_user)
        
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/me/change-password")
async def change_own_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Change current user's password."""
    from ..api.auth import verify_password
    
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_hash = get_password_hash(request.new_password)
    
    repo = UserRepository(session)
    await repo.update_password(current_user.id, new_hash)
    await session.commit()
    
    return {"success": True, "message": "Password changed successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Deactivate a user account.
    
    Requires admin role. Cannot deactivate yourself.
    """
    check_admin_access(current_user)
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    repo = UserRepository(session)
    user = await repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        await repo.deactivate(user_id)
        await session.commit()
        
        return {"success": True, "message": f"User {user.email} deactivated"}
        
    except Exception as e:
        logger.error(f"Failed to deactivate user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Activate a deactivated user account.
    
    Requires admin role.
    """
    check_admin_access(current_user)
    
    repo = UserRepository(session)
    user = await repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        await repo.activate(user_id)
        await session.commit()
        
        return {"success": True, "message": f"User {user.email} activated"}
        
    except Exception as e:
        logger.error(f"Failed to activate user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Permanently delete a user account.
    
    Requires admin role. Cannot delete yourself.
    """
    check_admin_access(current_user)
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    repo = UserRepository(session)
    user = await repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        await repo.delete(user_id)
        await session.commit()
        
        return {"success": True, "message": f"User {user.email} deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get("/roles/list", response_model=List[RoleInfo])
async def list_roles(
    current_user: User = Depends(get_current_user)
):
    """List available user roles and their permissions."""
    return [
        RoleInfo(
            role=UserRole.ADMIN.value,
            name="Administrator",
            description="Full access to all features and user management",
            permissions=[
                "manage_users",
                "manage_organization",
                "create_campaigns",
                "edit_campaigns",
                "delete_campaigns",
                "create_assets",
                "edit_assets",
                "delete_assets",
                "publish_posts",
                "view_analytics",
                "manage_integrations"
            ]
        ),
        RoleInfo(
            role=UserRole.EDITOR.value,
            name="Editor",
            description="Can create and edit campaigns and assets",
            permissions=[
                "create_campaigns",
                "edit_campaigns",
                "create_assets",
                "edit_assets",
                "publish_posts",
                "view_analytics"
            ]
        ),
        RoleInfo(
            role=UserRole.VIEWER.value,
            name="Viewer",
            description="Read-only access to view campaigns and assets",
            permissions=[
                "view_campaigns",
                "view_assets",
                "view_analytics"
            ]
        )
    ]


@router.get("/stats/overview")
async def get_user_stats(
    organization_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get user statistics for an organization."""
    check_admin_access(current_user)
    
    # Total users
    total_result = await session.execute(
        select(func.count(User.id))
        .where(User.organization_id == organization_id)
    )
    total = total_result.scalar() or 0
    
    # By role
    role_result = await session.execute(
        select(User.role, func.count(User.id))
        .where(User.organization_id == organization_id)
        .group_by(User.role)
    )
    by_role = {
        role.value if hasattr(role, 'value') else str(role): count
        for role, count in role_result.all()
    }
    
    # By status
    active_result = await session.execute(
        select(func.count(User.id))
        .where(User.organization_id == organization_id)
        .where(User.is_active == True)
    )
    active_count = active_result.scalar() or 0
    
    # Recently joined (last 30 days)
    from datetime import timedelta
    month_ago = datetime.utcnow() - timedelta(days=30)
    recent_result = await session.execute(
        select(func.count(User.id))
        .where(User.organization_id == organization_id)
        .where(User.created_at >= month_ago)
    )
    recent_count = recent_result.scalar() or 0
    
    return {
        "total": total,
        "active": active_count,
        "inactive": total - active_count,
        "by_role": by_role,
        "recently_joined": recent_count
    }
