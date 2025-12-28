"""登录相关API实现"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.database import get_db
from src.core.auth_service import AuthService
from src.core.exceptions import (
    AuthenticationError,
    RateLimitExceeded,
    AccountLockedError,
    ValidationError
)
from src.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutRequest,
    UserResponse
)
from src.models.user import User, RefreshToken
from src.core.deps import get_settings


router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings = Depends(get_settings)
):
    """
    用户登录
    """
    # 获取客户端信息
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    try:
        # 检查速率限制
        if not await auth_service.check_rate_limit(db, login_data.email, client_ip):
            await auth_service.record_login_attempt(
                db, login_data.email, client_ip, user_agent,
                success=False, failure_reason="rate_limit_exceeded"
            )
            raise RateLimitExceeded("请求频率过高，请稍后再试")

        # 检查账户锁定
        await auth_service.check_account_lock(db, login_data.email)

        # 获取用户
        user = await auth_service.get_user_by_email(db, login_data.email)
        if not user:
            # 用户不存在，记录失败尝试
            await auth_service.record_login_attempt(
                db, login_data.email, client_ip, user_agent,
                success=False, failure_reason="user_not_found"
            )
            # 不暴露具体的用户不存在信息
            raise AuthenticationError("邮箱或密码错误")

        # 检查账户状态
        if not user.is_active:
            await auth_service.record_login_attempt(
                db, login_data.email, client_ip, user_agent,
                success=False, failure_reason="account_inactive"
            )
            raise AuthenticationError("账户未激活，请联系管理员")

        # 验证密码
        if not auth_service.verify_password(login_data.password, user.password_hash):
            await auth_service.record_login_attempt(
                db, login_data.email, client_ip, user_agent,
                success=False, failure_reason="invalid_password"
            )
            raise AuthenticationError("邮箱或密码错误")

        # 登录成功，清除失败计数
        await auth_service.clear_login_attempts(db, str(user.id))

        # 生成令牌
        access_token_expire = timedelta(
            minutes=7*24*60 if login_data.remember_me else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_token_expire = timedelta(
            days=7*7 if login_data.remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        access_token = auth_service.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions or []
            },
            expires_delta=access_token_expire
        )
        refresh_token = auth_service.create_refresh_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions or []
            },
            expires_delta=refresh_token_expire
        )

        # 保存刷新令牌
        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            access_token_version=1,
            expires_at=datetime.now(timezone.utc) + refresh_token_expire
        )
        db.add(refresh_token_obj)
        await db.commit()

        # 更新最后登录时间
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        # 记录成功登录
        await auth_service.record_login_attempt(
            db, login_data.email, client_ip, user_agent,
            user_id=str(user.id), success=True
        )

        # 返回用户信息
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active,
            "role": user.role
        }

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expire.total_seconds()),
            user=user_data
        )

    except (RateLimitExceeded, AccountLockedError, AuthenticationError):
        raise
    except Exception as e:
        await db.rollback()
        # 打印日志
        print(f"登录过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误"
        )