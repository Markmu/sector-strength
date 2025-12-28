"""
API 依赖注入

提供数据库会话、认证等依赖项。
"""

import logging
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.database import AsyncSessionLocal
from src.models.user import User
from src.core.auth_service import AuthService

logger = logging.getLogger(__name__)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    用于 FastAPI 依赖注入，自动管理会话生命周期。

    Yields:
        AsyncSession: 异步数据库会话

    Examples:
        ```python
        @router.get("/sectors")
        async def get_sectors(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(Sector))
            return result.scalars().all()
        ```
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# 为未来认证预留的依赖（Epic-2 完成后使用）
# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     session: AsyncSession = Depends(get_session)
# ) -> User:
#     """
#     获取当前登录用户
#
#     Args:
#         token: JWT token
#         session: 数据库会话
#
#     Returns:
#         User: 当前用户对象
#
#     Raises:
#         HTTPException: 认证失败时抛出 401
#     """
#     # TODO: Epic-2 实现用户认证后添加
#     pass


# 认证相关依赖
security = HTTPBearer()
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    获取当前登录用户

    验证JWT token并返回用户对象。

    Args:
        credentials: HTTP Bearer认证凭证
        session: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出 401
    """
    try:
        token = credentials.credentials
        logger.debug(f"正在验证token，长度: {len(token)}")

        # 验证token并获取payload
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            logger.warning("Token中缺少sub字段")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌：缺少用户标识"
            )

        # 获取用户信息
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"用户不存在: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        if not user.is_active:
            logger.warning(f"账户未激活: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户未激活"
            )

        logger.debug(f"认证成功: user_id={user_id}, email={user.email}, role={user.role}")
        return user

    except HTTPException:
        # 直接重新抛出HTTPException
        raise
    except Exception as e:
        logger.error(f"认证失败: {type(e).__name__} - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    要求管理员权限

    验证当前用户是否为管理员角色。

    Args:
        current_user: 当前登录用户

    Returns:
        User: 管理员用户对象

    Raises:
        HTTPException: 非管理员时抛出 403
    """
    logger.info(f"当前用户角色: {current_user.role}")
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
