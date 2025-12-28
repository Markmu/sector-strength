"""认证服务模块"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.models.user import User, LoginAttempt, RefreshToken
from src.core.settings import settings
from src.core.exceptions import AuthenticationError, RateLimitExceeded, AccountLockedError


class AuthService:
    """认证服务"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.SECRET_KEY

        # 安全限制
        self.max_login_attempts = 5
        self.lockout_duration = 30  # 30分钟锁定
        self.rate_limit_window = 60  # 1分钟窗口
        self.rate_limit_attempts = 5  # 每分钟最多5次尝试

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return self.pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise AuthenticationError("Invalid token")

    def decode_token(self, token: str) -> Dict[str, Any]:
        """解码令牌（不验证签名，用于调试）"""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_signature": False})

    async def check_rate_limit(self, db: AsyncSession, email: str, ip_address: str) -> bool:
        """检查登录速率限制"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.rate_limit_window)

        # 检查同一邮箱/IP在时间窗口内的登录尝试次数
        result = await db.execute(
            select(func.count(LoginAttempt.id))
            .where(
                LoginAttempt.email == email,
                LoginAttempt.created_at >= window_start
            )
        )
        attempts_count = result.scalar()

        return attempts_count < self.rate_limit_attempts

    async def check_account_lock(self, db: AsyncSession, email: str) -> bool:
        """检查账户是否被锁定"""
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.login_attempts))
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining_time = user.locked_until - datetime.now(timezone.utc)
            raise AccountLockedError(f"账户已锁定，请{remaining_time.seconds // 60}分钟后再试")

        return False

    async def record_login_attempt(self, db: AsyncSession, email: str, ip_address: str,
                                  user_agent: str, user_id: Optional[str] = None,
                                  success: bool = False, failure_reason: Optional[str] = None) -> None:
        """记录登录尝试"""
        login_attempt = LoginAttempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            success=success,
            failure_reason=failure_reason
        )
        db.add(login_attempt)

        # 如果登录失败，更新用户的失败计数
        if not success and user_id:
            result = await db.execute(
                select(User)
                .where(User.id == user_id)
            )
            user = result.scalar_one()
            user.login_attempts_count += 1

            # 检查是否需要锁定账户
            if user.login_attempts_count >= self.max_login_attempts:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=self.lockout_duration)

        await db.commit()

    async def clear_login_attempts(self, db: AsyncSession, user_id: str) -> None:
        """清除登录失败计数"""
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )
        user = result.scalar_one()
        user.login_attempts_count = 0
        user.locked_until = None
        await db.commit()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await db.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.refresh_tokens))
        )
        return result.scalar_one_or_none()

    async def invalidate_refresh_token(self, db: AsyncSession, refresh_token: str) -> None:
        """使刷新令牌失效（注销）"""
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token == refresh_token)
        )
        token = result.scalar_one_or_none()

        if token:
            token.revoked = True
            token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    async def is_refresh_token_valid(self, db: AsyncSession, refresh_token: str) -> bool:
        """检查刷新令牌是否有效"""
        result = await db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.token == refresh_token,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        )
        token = result.scalar_one_or_none()

        return token is not None