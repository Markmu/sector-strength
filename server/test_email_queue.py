"""邮件队列功能测试"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.core.email_queue import email_queue, EmailType, EmailJob
from src.core.email import send_verification_email
import uuid


@pytest.mark.asyncio
async def test_add_email_to_queue():
    """测试添加邮件到队列"""
    # 清空队列
    email_queue.clear_queue()

    # 添加测试邮件
    email_id = email_queue.add_email(
        email_type=EmailType.VERIFICATION,
        email_to="test@example.com",
        template_data={"verification_token": "test_token", "username": "test_user"}
    )

    # 验证邮件ID生成
    assert email_id is not None
    assert len(email_id) > 0

    # 验证队列大小
    assert email_queue.stats["current_queue_size"] == 1

    # 验证邮件任务属性
    email_job = email_queue.queue[0]
    assert email_job.email_type == EmailType.VERIFICATION
    assert email_job.email_to == "test@example.com"
    assert email_job.template_data["verification_token"] == "test_token"


@pytest.mark.asyncio
async def test_email_queue_processing():
    """测试邮件队列处理"""
    # 清空队列
    email_queue.clear_queue()

    # 模拟邮件发送成功
    with patch('src.core.email_queue.send_verification_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True

        # 添加邮件到队列
        email_id = email_queue.add_email(
            email_type=EmailType.VERIFICATION,
            email_to="test@example.com",
            template_data={"verification_token": "test_token", "username": "test_user"}
        )

        # 处理队列
        await email_queue.process_queue()

        # 验证邮件已发送
        mock_send.assert_called_once()

        # 验证队列已清空
        assert email_queue.stats["current_queue_size"] == 0
        assert email_queue.stats["total_sent"] == 1
        assert email_queue.stats["total_processed"] == 1


@pytest.mark.asyncio
async def test_email_queue_retry_on_failure():
    """测试邮件发送失败时的重试机制"""
    # 清空队列
    email_queue.clear_queue()

    # 模拟邮件发送失败
    with patch('src.core.email_queue.send_verification_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = False

        # 添加邮件到队列
        email_id = email_queue.add_email(
            email_type=EmailType.VERIFICATION,
            email_to="test@example.com",
            template_data={"verification_token": "test_token", "username": "test_user"},
            max_retries=2
        )

        # 处理队列
        await email_queue.process_queue()

        # 验证邮件被重试
        assert mock_send.call_count == 2  # 初始发送 + 1次重试

        # 验证队列有剩余（因为重试）
        assert email_queue.queue[0].retry_count == 1


@pytest.mark.asyncio
async def test_email_queue_stats():
    """测试邮件队列统计信息"""
    # 清空队列
    email_queue.clear_queue()

    # 添加一些邮件
    for i in range(5):
        email_queue.add_email(
            email_type=EmailType.VERIFICATION,
            email_to=f"test{i}@example.com",
            template_data={"verification_token": f"token{i}", "username": f"user{i}"}
        )

    stats = email_queue.get_queue_stats()

    # 验证统计信息
    assert stats["current_queue_size"] == 5
    assert stats["total_processed"] == 0
    assert stats["total_sent"] == 0
    assert stats["total_failed"] == 0


def test_email_job_serialization():
    """测试邮件任务序列化"""
    # 创建邮件任务
    email_job = EmailJob(
        id=str(uuid.uuid4()),
        email_type=EmailType.VERIFICATION,
        email_to="test@example.com",
        template_data={"verification_token": "test_token", "username": "test_user"}
    )

    # 转换为字典
    job_dict = email_job.to_dict()

    # 验证字典内容
    assert job_dict["email_type"] == "verification"
    assert job_dict["email_to"] == "test@example.com"
    assert job_dict["template_data"]["verification_token"] == "test_token"

    # 从字典重建
    email_job2 = EmailJob.from_dict(job_dict)
    assert email_job2.email_type == EmailType.VERIFICATION
    assert email_job2.email_to == "test@example.com"


@pytest.mark.asyncio
async def test_email_processor_control():
    """测试邮件处理器控制"""
    # 清空队列
    email_queue.clear_queue()

    # 添加邮件
    email_queue.add_email(
        email_type=EmailType.VERIFICATION,
        email_to="test@example.com",
        template_data={"verification_token": "test_token", "username": "test_user"}
    )

    # 启动处理器
    await email_queue.start_processor()
    assert email_queue.processing == True

    # 停止处理器
    await email_queue.stop_processor()
    assert email_queue.processing == False