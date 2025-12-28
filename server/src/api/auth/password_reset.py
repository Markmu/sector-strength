"""密码重置相关 API"""

from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, validator
import re

from src.db.database import get_db
from src.models.user import User, PasswordResetToken
from src.core.security import hash_password
from src.core.email_queue import send_password_reset_email_queue
from src.core.rate_limiter import check_rate_limit
from src.core.sanitizer import InputValidator
from fastapi import Request, Header
import uuid

router = APIRouter()


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """密码重置确认请求"""
    token: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含大写字母')
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含小写字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含数字')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('密码必须包含特殊字符')
        return v

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """验证两次密码是否一致"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v


def generate_password_reset_token() -> str:
    """生成密码重置令牌"""
    return str(uuid.uuid4())


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: PasswordResetRequest,
    request_obj: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    请求密码重置

    - 验证邮箱是否存在
    - 生成重置令牌
    - 将重置邮件加入队列
    """
    # 验证邮箱格式
    is_valid, cleaned_data, validation_errors = InputValidator.validate_and_sanitize_register_data({
        'email': request.email
    })

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": validation_errors}
        )

    # 应用速率限制：每个邮箱 5 分钟内最多 3 次重置请求
    await check_rate_limit(
        request_obj,
        limit=3,
        window=300,
        identifier=f"password_reset:{cleaned_data['email']}"
    )

    # 查找用户
    result = await db.execute(select(User).where(User.email == cleaned_data['email']))
    user = result.scalar_one_or_none()

    if not user:
        # 为了安全，即使邮箱不存在也返回成功，避免泄露用户信息
        print(f"密码重置请求 - 邮箱不存在: {cleaned_data['email']}")
        return {"message": "如果您的邮箱存在，我们将向您发送重置链接"}

    # 检查用户是否已激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账户未激活，请先激活您的账户"
        )

    # 生成重置令牌
    reset_token = generate_password_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)  # 重置令牌1小时有效期

    # 创建重置令牌
    password_reset_token = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at
    )

    db.add(password_reset_token)
    await db.commit()

    # 将重置邮件加入队列
    email_task_id = await send_password_reset_email_queue(
        email_to=cleaned_data['email'],
        reset_token=reset_token,
        username=user.username
    )

    print(f"密码重置邮件已加入队列，任务ID: {email_task_id}, 用户: {cleaned_data['email']}")

    return {"message": "密码重置链接已发送到您的邮箱"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    确认密码重置

    - 验证重置令牌
    - 检查令牌是否过期
    - 更新用户密码
    - 标记令牌已使用
    """
    # 查找重置令牌
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token,
            PasswordResetToken.is_used == False
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="重置令牌无效或已使用"
        )

    # 检查令牌是否过期
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌已过期，请重新申请"
        )

    # 查找用户
    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新用户密码
    hashed_password = hash_password(request.new_password)
    user.password_hash = hashed_password
    user.updated_at = datetime.utcnow()

    # 标记令牌已使用
    reset_token.is_used = True

    await db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}