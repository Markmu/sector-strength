"""用户注册相关 API"""

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from src.db.database import get_db
from src.models.user import User, EmailVerificationToken
from src.core.security import hash_password
from src.core.rate_limiter import check_rate_limit
from src.core.sanitizer import InputValidator
from src.core.email import send_verification_email as core_send_verification_email


router = APIRouter( )


# Pydantic 模型
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr
    password: str
    username: str | None = None


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    message: str
    user_id: str


async def send_verification_email(email: str, verification_token: str, username: str | None = None) -> bool:
    """Compatibility wrapper for tests patching this symbol."""
    return await core_send_verification_email(email_to=email, verification_token=verification_token, username=username)






@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    用户注册

    - 验证邮箱格式
    - 验证密码强度
    - 检查邮箱是否已注册
    - 创建未激活用户
    - 发送邮箱验证邮件
    - 应用速率限制
    """
    # 验证和清理输入数据
    is_valid, cleaned_data, validation_errors = InputValidator.validate_and_sanitize_register_data({
        'email': user_data.email,
        'password': user_data.password,
        'username': user_data.username
    })

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码强度不够" if any("密码" in err for err in validation_errors) else {"errors": validation_errors}
        )

    # 应用速率限制：每个 IP 5 分钟内最多 3 次注册尝试
    await check_rate_limit(request, limit=3, window=300, identifier=f"register:{cleaned_data['email']}")

    # 检查邮箱是否已注册
    result = await db.execute(select(User).where(User.email == cleaned_data['email']))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 创建用户（待邮箱验证）
    hashed_password = hash_password(cleaned_data['password'])
    user = User(
        email=cleaned_data['email'],
        password_hash=hashed_password,
        username=cleaned_data.get('username')
    )
    user.is_active = False
    user.is_verified = False

    db.add(user)
    await db.flush()

    verification_token = str(uuid4())
    token = EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_used=False,
    )
    db.add(token)
    await db.commit()

    await send_verification_email(
        email=cleaned_data['email'],
        verification_token=verification_token,
        username=cleaned_data.get('username'),
    )

    return {
        "message": "注册成功，请查看邮箱进行验证",
        "user_id": str(user.id)
    }
