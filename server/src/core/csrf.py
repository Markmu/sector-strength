"""CSRF 保护中间件"""

import uuid
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class CSRFProtection:
    """CSRF 保护类"""

    def __init__(self):
        # 在生产环境中，这应该使用 Redis 或其他持久化存储
        self._tokens = {}  # 简化实现，仅用于演示

    def generate_token(self) -> str:
        """生成 CSRF 令牌"""
        return str(uuid.uuid4())

    def validate_token(
        self,
        request: Request,
        token: Optional[str] = None
    ) -> bool:
        """
        验证 CSRF 令牌

        Args:
            request: FastAPI 请求对象
            token: 要验证的令牌，如果为 None 则从请求头获取

        Returns:
            bool: 令牌是否有效
        """
        # 从请求头获取令牌
        if token is None:
            token = request.headers.get("X-CSRF-Token")

        if not token:
            return False

        # 从会话中获取存储的令牌（简化实现）
        session_token = self._tokens.get(request.client.host if request.client else "unknown")

        if not session_token:
            return False

        # 使用简单的字符串比较（生产环境应考虑更安全的比较方法）
        return token == session_token

    def store_token(self, request: Request, token: str):
        """存储 CSRF 令牌到会话"""
        # 简化实现，使用 IP 作为 key
        # 在生产环境中应该使用安全的会话存储
        key = request.client.host if request.client else "unknown"
        self._tokens[key] = token


# 创建全局 CSRF 保护实例
csrf_protection = CSRFProtection()


async def get_csrf_token(request: Request) -> str:
    """获取或生成 CSRF 令牌"""
    # 从请求头获取
    token = request.headers.get("X-CSRF-Token")
    if token:
        return token

    # 生成新令牌
    token = csrf_protection.generate_token()
    csrf_protection.store_token(request, token)
    return token


async def verify_csrf_token(request: Request, token: Optional[str] = None):
    """
    验证 CSRF 令牌

    Args:
        request: FastAPI 请求对象
        token: 要验证的令牌
    """
    if not csrf_protection.validate_token(request, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF 令牌无效或缺失"
        )