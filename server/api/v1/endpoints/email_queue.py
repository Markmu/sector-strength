"""邮件队列管理 API 端点"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel

from src.core.email_queue import email_queue, EmailType

router = APIRouter()


class EmailQueueStatsResponse(BaseModel):
    """队列统计信息响应"""
    total_sent: int
    total_failed: int
    total_processed: int
    current_queue_size: int
    processing: bool


class QueueInfoResponse(BaseModel):
    """队列信息响应"""
    stats: EmailQueueStatsResponse
    message: str


@router.get("/queue/stats", response_model=QueueInfoResponse)
async def get_email_queue_stats():
    """
    获取邮件队列统计信息
    """
    stats = email_queue.get_queue_stats()

    return QueueInfoResponse(
        stats=EmailQueueStatsResponse(**stats),
        message="邮件队列统计信息获取成功"
    )


@router.post("/queue/start")
async def start_email_processor():
    """
    启动邮件队列处理器
    """
    if email_queue.processing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮件处理器已在运行中"
        )

    await email_queue.start_processor()
    return {"message": "邮件处理器已启动"}


@router.post("/queue/stop")
async def stop_email_processor():
    """
    停止邮件队列处理器
    """
    if not email_queue.processing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮件处理器未在运行"
        )

    await email_queue.stop_processor()
    return {"message": "邮件处理器已停止"}


@router.post("/queue/clear")
async def clear_email_queue():
    """
    清空邮件队列
    """
    email_queue.clear_queue()
    return {"message": "邮件队列已清空"}


@router.get("/queue/types")
async def get_email_types():
    """
    获取支持的邮件类型
    """
    return {
        "email_types": [{"value": et.value, "name": et.name} for et in EmailType],
        "message": "支持的邮件类型列表"
    }


@router.get("/queue/health")
async def get_queue_health():
    """
    检查队列健康状态
    """
    stats = email_queue.get_queue_stats()

    health_status = {
        "status": "healthy" if stats["current_queue_size"] < 100 else "warning",
        "queue_size": stats["current_queue_size"],
        "is_processing": stats["processing"],
        "success_rate": stats["total_sent"] / max(stats["total_processed"], 1) * 100,
        "timestamp": "2025-12-06T10:00:00Z"  # 实际应用中应使用当前时间
    }

    return health_status