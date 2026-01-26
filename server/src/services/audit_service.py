"""
审计服务

提供审计日志记录功能，满足 NFR-SEC-006、NFR-SEC-007、NFR-SEC-008 要求。
记录所有管理员操作以支持事后追溯和责任认定。
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json

from src.models.audit_log import AuditLog
from src.models.user import User


class AuditService:
    """
    审计服务类

    提供统一的审计日志记录接口。
    所有管理员操作都应通过此服务记录到审计日志。
    """

    # 操作类型常量
    ACTION_TEST_CLASSIFICATION = "test_classification"
    ACTION_INIT_DATA = "init_data"
    ACTION_UPDATE_DATA = "update_data"
    ACTION_OVERWRITE_DATA = "overwrite_data"
    ACTION_CANCEL_TASK = "cancel_task"
    ACTION_CHANGE_ROLE = "change_role"
    ACTION_DISABLE_USER = "disable_user"

    @staticmethod
    async def log_action(
        db: AsyncSession,
        user: User,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        result: Optional[str] = None,
    ) -> AuditLog:
        """
        记录操作到审计日志

        Args:
            db: 数据库会话
            user: 操作用户
            action: 操作类型
            resource_type: 资源类型（可选）
            resource_id: 资源 ID（可选）
            details: 操作详情（可选，字典格式）
            ip_address: 操作来源 IP（可选）
            user_agent: 用户代理（可选）
            status: 操作状态（success, failed, partial）
            result: 操作结果描述（可选）

        Returns:
            创建的审计日志记录
        """
        log_entry = AuditLog(
            user_id=user.id,
            username=user.username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            result=result,
            created_at=datetime.now(),
        )

        db.add(log_entry)
        await db.flush()

        return log_entry

    @staticmethod
    async def log_classification_test(
        db: AsyncSession,
        user: User,
        total_count: int,
        success_count: int,
        failure_count: int,
        duration_ms: int,
        failures: Optional[list] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        记录分类算法测试操作

        专门用于 Story 4.2 的分类算法测试功能。

        Args:
            db: 数据库会话
            user: 操作用户
            total_count: 总板块数
            success_count: 成功数量
            failure_count: 失败数量
            duration_ms: 计算耗时（毫秒）
            failures: 失败详情列表（可选）
            ip_address: 操作来源 IP（可选）
            user_agent: 用户代理（可选）

        Returns:
            创建的审计日志记录
        """
        # 根据失败数量确定状态
        if failure_count == 0:
            status = "success"
            result = f"测试成功：共 {total_count} 个板块，全部计算完成，耗时 {duration_ms}ms"
        elif success_count == 0:
            status = "failed"
            result = f"测试失败：共 {total_count} 个板块，全部计算失败"
        else:
            status = "partial"
            result = f"部分成功：共 {total_count} 个板块，成功 {success_count} 个，失败 {failure_count} 个，耗时 {duration_ms}ms"

        # 构建详情
        details = {
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "duration_ms": duration_ms,
        }

        if failures:
            details["failures"] = failures

        return await AuditService.log_action(
            db=db,
            user=user,
            action=AuditService.ACTION_TEST_CLASSIFICATION,
            resource_type="sector_classification",
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            result=result,
        )

    @staticmethod
    async def query_logs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """
        查询审计日志

        Args:
            db: 数据库会话
            user_id: 按用户 ID 筛选（可选）
            action: 按操作类型筛选（可选）
            resource_type: 按资源类型筛选（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            status: 按状态筛选（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (日志列表, 总数)
        """
        query = select(AuditLog)

        # 应用筛选条件
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action is not None:
            query = query.where(AuditLog.action == action)
        if resource_type is not None:
            query = query.where(AuditLog.resource_type == resource_type)
        if start_date is not None:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            query = query.where(AuditLog.created_at <= end_date)
        if status is not None:
            query = query.where(AuditLog.status == status)

        # 按时间倒序排列
        query = query.order_by(AuditLog.created_at.desc())

        # 获取总数
        count_query = select(AuditLog.id)
        if user_id is not None:
            count_query = count_query.where(AuditLog.user_id == user_id)
        if action is not None:
            count_query = count_query.where(AuditLog.action == action)
        if resource_type is not None:
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if start_date is not None:
            count_query = count_query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            count_query = count_query.where(AuditLog.created_at <= end_date)
        if status is not None:
            count_query = count_query.where(AuditLog.status == status)

        count_result = await db.execute(count_query)
        total = len(count_result.all())

        # 应用分页
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        logs = result.scalars().all()

        return list(logs), total
