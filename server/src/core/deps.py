"""依赖注入"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.core.settings import settings

# HTTP Bearer 认证
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取当前用户 - 待实现"""
    # TODO: 实现 JWT 认证逻辑
    # 暂时跳过认证
    return {"user_id": "temp_user", "username": "temp_user"}

def get_settings():
    """获取应用配置"""
    return settings