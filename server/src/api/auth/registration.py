"""用户注册相关 API"""

from typing import Any
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, validator
import re

from src.db.database import get_db
from src.models.user import User
from src.core.security import hash_password
from src.core.rate_limiter import check_rate_limit
from src.core.sanitizer import InputValidator


router = APIRouter( )


# Pydantic 模型
class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr
    password: str
    username: str | None = None

    @validator('password')
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

    @validator('username')
    def validate_username(cls, v):
        """验证用户名"""
        if v and len(v) > 50:
            raise ValueError('用户名长度不能超过50个字符')
        return v


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    message: str
    user_id: str






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
    - 创建用户并直接激活
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
            detail={"errors": validation_errors}
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

    # 创建用户并直接激活
    hashed_password = hash_password(cleaned_data['password'])
    user = User(
        email=cleaned_data['email'],
        password_hash=hashed_password,
        username=cleaned_data.get('username')
    )
    # 强制设置用户为激活状态，确保迁移后的兼容性
    user.is_active = True

    db.add(user)
    await db.commit()

    return {
        "message": "注册成功，账户已激活",
        "user_id": str(user.id)
    }