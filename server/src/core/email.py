"""邮件服务配置和发送"""

import os
from typing import List
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from jinja2 import Environment, FileSystemLoader
from src.core.settings import settings

# 邮件配置
conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER or os.getenv("SMTP_USER"),
    MAIL_PASSWORD=settings.SMTP_PASSWORD or os.getenv("SMTP_PASSWORD"),
    MAIL_FROM=settings.MAIL_FROM or os.getenv("MAIL_FROM", "noreply@sector-strength.com"),
    MAIL_PORT=settings.SMTP_PORT or int(os.getenv("SMTP_PORT", 587)),
    MAIL_SERVER=settings.SMTP_HOST or os.getenv("SMTP_HOST", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# 初始化 FastMail
fastmail = FastMail(conf)


async def send_verification_email(
    email_to: EmailStr,
    verification_token: str,
    username: str | None = None
) -> bool:
    """
    发送邮箱验证邮件

    Args:
        email_to: 收件人邮箱
        verification_token: 验证令牌
        username: 用户名（可选）

    Returns:
        bool: 发送是否成功
    """
    try:
        # 构建验证链接
        verification_url = f"{settings.FRONTEND_URL or 'http://localhost:3000'}/verify-email?token={verification_token}"

        # 创建邮件消息
        message = MessageSchema(
            subject="验证您的 Sector Strength 账户",
            recipients=[email_to],
            template_body={
                "username": username or email_to.split('@')[0],
                "verification_url": verification_url,
                "app_name": "Sector Strength",
                "support_email": "support@sector-strength.com"
            },
            subtype=MessageType.html
        )

        # 发送邮件
        await fastmail.send_message(message, template_name="verify_email.html")
        return True
    except Exception as e:
        print(f"发送验证邮件失败: {e}")
        # 在开发环境中，打印验证链接
        print(f"验证链接: {verification_url}")
        return False


async def send_password_reset_email(
    email_to: EmailStr,
    reset_token: str,
    username: str | None = None
) -> bool:
    """
    发送密码重置邮件

    Args:
        email_to: 收件人邮箱
        reset_token: 重置令牌
        username: 用户名（可选）

    Returns:
        bool: 发送是否成功
    """
    try:
        # 构建重置链接
        reset_url = f"{settings.FRONTEND_URL or 'http://localhost:3000'}/reset-password?token={reset_token}"

        # 创建邮件消息
        message = MessageSchema(
            subject="重置您的 Sector Strength 密码",
            recipients=[email_to],
            template_body={
                "username": username or email_to.split('@')[0],
                "reset_url": reset_url,
                "app_name": "Sector Strength",
                "support_email": "support@sector-strength.com"
            },
            subtype=MessageType.html
        )

        # 发送邮件
        await fastmail.send_message(message, template_name="reset_password.html")
        return True
    except Exception as e:
        print(f"发送密码重置邮件失败: {e}")
        return False