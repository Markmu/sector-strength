"""邮件队列服务 - 异步处理邮件发送"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import deque
import uuid

from src.core.email import send_verification_email, send_password_reset_email
from src.core.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailType(Enum):
    """邮件类型枚举"""
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    NOTIFICATION = "notification"


@dataclass
class EmailJob:
    """邮件任务"""
    id: str
    email_type: EmailType
    email_to: str
    template_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, processing, sent, failed

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "email_type": self.email_type.value,
            "email_to": self.email_to,
            "template_data": self.template_data,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailJob':
        """从字典创建邮件任务"""
        return cls(
            id=data["id"],
            email_type=EmailType(data["email_type"]),
            email_to=data["email_to"],
            template_data=data["template_data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            status=data.get("status", "pending")
        )


class EmailQueue:
    """邮件队列管理器"""

    def __init__(self, max_queue_size: int = 1000):
        self.queue: deque = deque(maxlen=max_queue_size)
        self.processing: bool = False
        self.processor_task: Optional[asyncio.Task] = None
        self.stats = {
            "total_sent": 0,
            "total_failed": 0,
            "total_processed": 0,
            "current_queue_size": 0
        }

    def add_email(
        self,
        email_type: EmailType,
        email_to: str,
        template_data: Dict[str, Any],
        scheduled_at: Optional[datetime] = None,
        priority: bool = False
    ) -> str:
        """
        添加邮件到队列

        Args:
            email_type: 邮件类型
            email_to: 收件人邮箱
            template_data: 模板数据
            scheduled_at: 计划发送时间（可选）
            priority: 是否优先处理

        Returns:
            str: 邮件任务ID
        """
        email_job = EmailJob(
            id=str(uuid.uuid4()),
            email_type=email_type,
            email_to=email_to,
            template_data=template_data,
            scheduled_at=scheduled_at
        )

        if priority:
            self.queue.appendleft(email_job)
        else:
            self.queue.append(email_job)

        self.stats["current_queue_size"] = len(self.queue)
        logger.info(f"邮件已加入队列: {email_job.id} - {email_to}")

        return email_job.id

    async def process_email(self, email_job: EmailJob) -> bool:
        """
        处理单个邮件任务

        Args:
            email_job: 邮件任务

        Returns:
            bool: 发送是否成功
        """
        try:
            email_job.status = "processing"

            # 检查是否到了发送时间
            if email_job.scheduled_at and datetime.utcnow() < email_job.scheduled_at:
                await asyncio.sleep((email_job.scheduled_at - datetime.utcnow()).total_seconds())

            # 根据邮件类型调用相应的发送函数
            success = False

            if email_job.email_type == EmailType.VERIFICATION:
                token = email_job.template_data.get("verification_token")
                username = email_job.template_data.get("username")
                success = await send_verification_email(
                    email_to=email_job.email_to,
                    verification_token=token,
                    username=username
                )
            elif email_job.email_type == EmailType.PASSWORD_RESET:
                token = email_job.template_data.get("reset_token")
                username = email_job.template_data.get("username")
                success = await send_password_reset_email(
                    email_to=email_job.email_to,
                    reset_token=token,
                    username=username
                )
            else:
                logger.warning(f"不支持的邮件类型: {email_job.email_type}")
                return False

            if success:
                email_job.status = "sent"
                self.stats["total_sent"] += 1
                logger.info(f"邮件发送成功: {email_job.id} - {email_job.email_to}")
            else:
                email_job.status = "failed"
                email_job.retry_count += 1

                # 如果还有重试次数，重新加入队列
                if email_job.retry_count < email_job.max_retries:
                    logger.warning(f"邮件发送失败，准备重试: {email_job.id} - 尝试 {email_job.retry_count}/{email_job.max_retries}")
                    self.queue.appendleft(email_job)  # 优先重试
                    self.stats["current_queue_size"] = len(self.queue)
                else:
                    logger.error(f"邮件发送失败，已达最大重试次数: {email_job.id}")
                    self.stats["total_failed"] += 1

                return False

            return True

        except Exception as e:
            logger.error(f"处理邮件时发生错误: {email_job.id} - {str(e)}")
            email_job.status = "failed"
            email_job.retry_count += 1

            if email_job.retry_count < email_job.max_retries:
                self.queue.appendleft(email_job)  # 优先重试
                self.stats["current_queue_size"] = len(self.queue)
            else:
                self.stats["total_failed"] += 1

            return False

    async def process_queue(self):
        """处理队列中的所有邮件"""
        self.processing = True

        try:
            while self.queue:
                email_job = self.queue.popleft()
                self.stats["current_queue_size"] = len(self.queue)

                await self.process_email(email_job)
                self.stats["total_processed"] += 1

                # 添加短暂延迟，避免过于频繁的邮件发送
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"处理队列时发生错误: {str(e)}")
        finally:
            self.processing = False

    async def start_processor(self):
        """启动邮件处理器"""
        if not self.processing:
            self.processor_task = asyncio.create_task(self.process_queue())
            logger.info("邮件处理器已启动")

    async def stop_processor(self):
        """停止邮件处理器"""
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        self.processing = False
        logger.info("邮件处理器已停止")

    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            **self.stats,
            "processing": self.processing,
            "queue_size": len(self.queue)
        }

    def clear_queue(self):
        """清空队列"""
        self.queue.clear()
        self.stats["current_queue_size"] = 0
        logger.info("邮件队列已清空")


# 全局邮件队列实例
email_queue = EmailQueue()


# 邮件发送辅助函数
async def send_verification_email_queue(
    email_to: str,
    verification_token: str,
    username: str | None = None
) -> str:
    """
    将验证邮件加入队列

    Args:
        email_to: 收件人邮箱
        verification_token: 验证令牌
        username: 用户名（可选）

    Returns:
        str: 邮件任务ID
    """
    template_data = {
        "verification_token": verification_token,
        "username": username or email_to.split('@')[0]
    }

    return email_queue.add_email(
        email_type=EmailType.VERIFICATION,
        email_to=email_to,
        template_data=template_data
    )


async def send_password_reset_email_queue(
    email_to: str,
    reset_token: str,
    username: str | None = None
) -> str:
    """
    将密码重置邮件加入队列

    Args:
        email_to: 收件人邮箱
        reset_token: 重置令牌
        username: 用户名（可选）

    Returns:
        str: 邮件任务ID
    """
    template_data = {
        "reset_token": reset_token,
        "username": username or email_to.split('@')[0]
    }

    return email_queue.add_email(
        email_type=EmailType.PASSWORD_RESET,
        email_to=email_to,
        template_data=template_data
    )


# 初始化时自动启动队列处理器
async def initialize_email_queue():
    """初始化邮件队列"""
    await email_queue.start_processor()


# 应用关闭时停止队列处理器
async def shutdown_email_queue():
    """关闭邮件队列"""
    await email_queue.stop_processor()