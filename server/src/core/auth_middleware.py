"""认证和授权中间件"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User
from src.core.auth import AuthService
from src.core.database import get_db

security = HTTPBearer(auto_error=False)
optional_security = HTTPBearer(auto_error=False)
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前认证用户

    验证JWT令牌并从数据库获取用户对象
    """
    try:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # 验证令牌
        payload = auth_service.verify_token(credentials.credentials)

        # 检查令牌类型
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 获取用户ID
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 从数据库获取用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """可选的当前用户获取

    如果提供了有效的令牌则返回用户，否则返回None
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_authenticated():
    """要求用户必须认证"""
    return get_current_user


def require_role(required_role: str):
    """要求用户具有特定角色

    Args:
        required_role: 需要的角色名称（如 'admin', 'user'）
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required role: {required_role}",
            )
        return current_user

    return role_checker


def require_permission(required_permission: str):
    """要求用户具有特定权限

    Args:
        required_permission: 需要的权限名称
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not current_user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required permission: {required_permission}",
            )
        return current_user

    return permission_checker


def require_any_role(roles: List[str]):
    """要求用户具有任一角色

    Args:
        roles: 允许的角色列表
    """
    async def any_role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not any(current_user.has_role(role) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required one of: {', '.join(roles)}",
            )
        return current_user

    return any_role_checker


def require_all_permissions(permissions: List[str]):
    """要求用户具有所有权限

    Args:
        permissions: 需要的权限列表
    """
    async def all_permissions_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        missing_permissions = [
            perm for perm in permissions
            if not current_user.has_permission(perm)
        ]

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Missing permissions: {', '.join(missing_permissions)}",
            )
        return current_user

    return all_permissions_checker
