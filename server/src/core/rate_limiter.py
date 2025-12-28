"""速率限制中间件"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque
from fastapi import Request, HTTPException, status
import time


class RateLimiter:
    """基于内存的速率限制器"""

    def __init__(self):
        # 存储每个 IP 的请求时间戳队列
        self.requests: Dict[str, Deque[datetime]] = defaultdict(deque)
        # 清理过期数据的定时器
        self.last_cleanup = datetime.now()

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """
        检查是否允许请求

        Args:
            key: 唯一标识（通常是 IP 地址）
            limit: 时间窗口内允许的请求数
            window: 时间窗口大小（秒）

        Returns:
            bool: 是否允许请求
        """
        now = datetime.now()

        # 定期清理过期数据（每小时清理一次）
        if now - self.last_cleanup > timedelta(hours=1):
            self.cleanup()
            self.last_cleanup = now

        # 获取该 key 的请求队列
        request_queue = self.requests[key]

        # 移除时间窗口外的请求
        window_start = now - timedelta(seconds=window)
        while request_queue and request_queue[0] < window_start:
            request_queue.popleft()

        # 检查是否超过限制
        if len(request_queue) >= limit:
            return False

        # 记录当前请求
        request_queue.append(now)
        return True

    def cleanup(self):
        """清理过期的请求记录"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)  # 保留24小时内的记录

        # 清理每个 IP 的过期记录
        for key in list(self.requests.keys()):
            queue = self.requests[key]
            while queue and queue[0] < cutoff:
                queue.popleft()

            # 如果队列为空，删除该 key
            if not queue:
                del self.requests[key]


# 创建全局速率限制器实例
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP 地址"""
    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 返回直接连接的 IP
    return request.client.host if request.client else "unknown"


async def check_rate_limit(
    request: Request,
    limit: int = 5,
    window: int = 300,
    identifier: str | None = None
):
    """
    检查速率限制

    Args:
        request: FastAPI 请求对象
        limit: 时间窗口内允许的请求数
        window: 时间窗口大小（秒）
        identifier: 自定义标识符，默认使用 IP
    """
    key = identifier or get_client_ip(request)

    if not rate_limiter.is_allowed(key, limit, window):
        # 计算重试时间（可选）
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "请求过于频繁",
                "message": f"在 {window} 秒内最多允许 {limit} 次请求",
                "retry_after": window
            },
            headers={"Retry-After": str(window)}
        )