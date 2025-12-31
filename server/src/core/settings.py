"""应用配置设置"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "Sector Strength API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # 数据库配置
    DATABASE_URL: Optional[str] = None
    DATABASE_URL_ASYNC: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "sector_user"
    POSTGRES_PASSWORD: str = "sector_pass"
    POSTGRES_DB: str = "sector_strength"
    POSTGRES_PORT: int = 5432

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS配置
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]

    # 日志配置
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/app.log"

    # 数据源配置
    AKSHARE_TIMEOUT: int = 30
    CACHE_TTL: int = 300

    # 邮件服务配置
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@sector-strength.com"

    # 前端URL
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def database_url(self) -> str:
        """获取异步数据库连接 URL"""
        if self.DATABASE_URL_ASYNC:
            return self.DATABASE_URL_ASYNC
        elif self.DATABASE_URL and "asyncpg" in self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """获取同步数据库连接 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

# 创建全局设置实例
settings = Settings()