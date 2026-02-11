"""认证相关 API - 邮箱验证等"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.database import get_db
from src.models.user import User, EmailVerificationToken, PasswordResetToken, RefreshToken
from src.core.auth_service import AuthService
from src.core.exceptions import AuthenticationError, ValidationError
from src.schemas.auth import (
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    UserResponse
)
from src.core.deps import get_settings


router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
revoked_access_tokens: set[str] = set()


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    settings = Depends(get_settings)
):
    """
    刷新访问令牌
    """
    try:
        # 验证刷新令牌
        if not await auth_service.is_refresh_token_valid(db, refresh_request.refresh_token):
            raise AuthenticationError("无效的刷新令牌")

        # 解码令牌获取用户信息
        payload = auth_service.verify_token(refresh_request.refresh_token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise AuthenticationError("无效的令牌数据")

        # 获取用户
        user = await auth_service.get_user_by_email(db, email)
        if not user or not user.is_active:
            raise AuthenticationError("用户不存在或账户未激活")

        # 生成新的访问令牌
        access_token = auth_service.create_access_token(
            data={"sub": user_id, "email": email}
        )

        # 生成新的刷新令牌
        refresh_token = auth_service.create_refresh_token(
            data={"sub": user_id, "email": email}
        )

        # 使旧的刷新令牌失效
        await auth_service.invalidate_refresh_token(db, refresh_request.refresh_token)

        # 保存新的刷新令牌
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            access_token_version=2,
            expires_at=(datetime.now(timezone.utc) +
                       timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        )
        db.add(refresh_token_obj)
        await db.commit()

        return RefreshTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌过程中发生错误"
        )


@router.post("/logout")
async def logout(
    logout_request: LogoutRequest,
    credentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    注销登录
    """
    try:
        token = credentials.credentials
        payload = auth_service.verify_token(token)
        if payload.get("type") != "access":
            raise AuthenticationError("无效的访问令牌")

        # Revoke current access token in-memory for immediate sign-out semantics.
        revoked_access_tokens.add(token)

        if await auth_service.is_refresh_token_valid(db, logout_request.refresh_token):
            # 使刷新令牌失效
            await auth_service.invalidate_refresh_token(db, logout_request.refresh_token)

        return {"message": "注销成功"}

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注销过程中发生错误"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户信息
    """
    try:
        # 验证令牌
        token = credentials.credentials
        if token in revoked_access_tokens:
            raise AuthenticationError("令牌已失效，请重新登录")
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("无效的令牌")

        # 获取用户信息
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("用户不存在")

        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            role=user.role,
            last_login=user.last_login,
            created_at=user.created_at
        )

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息时发生错误"
        )


class VerifyEmailResponse(BaseModel):
    """邮箱验证响应"""
    message: str


def get_verification_token(token: str) -> str:
    """
    获取验证令牌（用于测试）
    TODO: 实际应该从数据库查询
    """
    return "mock_user_id"


@router.get("/verify/{token}", response_model=VerifyEmailResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    验证邮箱

    - 验证令牌有效性
    - 检查令牌是否过期
    - 激活用户账户
    """
    # 查找验证令牌
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token,
            EmailVerificationToken.is_used == False
        )
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="验证令牌无效或已使用"
        )

    # 检查令牌是否过期
    if verification.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证令牌已过期，请重新注册"
        )

    # 查找用户
    user_result = await db.execute(select(User).where(User.id == verification.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 激活用户并标记令牌已使用
    user.is_active = True
    user.is_verified = True
    verification.is_used = True

    await db.commit()

    return {
        "message": "邮箱验证成功，账户已激活"
    }
