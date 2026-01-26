"""
管理员审计日志 API 端点

提供管理员专用的审计日志查询功能：
- 查询审计日志（支持筛选和分页）
- 自动清理 6 个月前的日志

满足 NFR-SEC-002, NFR-SEC-003, NFR-SEC-006, NFR-SEC-007, NFR-SEC-008 要求
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from datetime import datetime, timedelta
from typing import Optional, List

from src.db.database import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User
from src.models.audit_log import AuditLog

router = APIRouter()


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    action_type: Optional[str] = Query(None, description="操作类型筛选"),
    user_id: Optional[str] = Query(None, description="用户 ID 筛选"),
    start_date: Optional[str] = Query(None, description="开始日期（ISO 8601）"),
    end_date: Optional[str] = Query(None, description="结束日期（ISO 8601）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取操作审计日志列表

    支持按操作类型、操作人、日期范围筛选，支持分页。

    权限：仅管理员

    参数：
        - page: 页码（默认 1）
        - page_size: 每页大小（默认 20，最大 100）
        - action_type: 操作类型筛选（如 test_classification, view_config 等）
        - user_id: 用户 ID 筛选
        - start_date: 开始日期（ISO 8601 格式）
        - end_date: 结束日期（ISO 8601 格式）

    返回：
        - items: 审计日志列表
        - total: 总记录数
        - page: 当前页
        - page_size: 每页大小
        - total_pages: 总页数

    响应格式：
        ```json
        {
          "success": true,
          "data": {
            "items": [
              {
                "id": "1",
                "action_type": "test_classification",
                "action_details": "测试完成：成功15个，失败0个，耗时125ms",
                "user_id": "1",
                "username": "admin",
                "ip_address": "192.168.1.100",
                "created_at": "2026-01-27T10:30:00Z"
              }
            ],
            "total": 100,
            "page": 1,
            "page_size": 20,
            "total_pages": 5
          }
        }
        ```
    """
    # 获取客户端信息
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # 验证管理员权限（NFR-SEC-002, NFR-SEC-003）
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="权限不足：仅管理员可执行此操作"
        )

    # 构建查询条件
    conditions = []

    if action_type:
        conditions.append(AuditLog.action == action_type)

    if user_id:
        try:
            user_id_int = int(user_id)
            conditions.append(AuditLog.user_id == user_id_int)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="用户 ID 格式无效"
            )

    if start_date:
        try:
            # 支持两种格式：YYYY-MM-DD (HTML date input) 和 ISO 8601
            if 'T' not in start_date:
                # HTML date input 格式: YYYY-MM-DD
                start_dt = datetime.fromisoformat(start_date)
            else:
                # ISO 8601 格式
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            conditions.append(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="开始日期格式无效，请使用 YYYY-MM-DD 或 ISO 8601 格式"
            )

    if end_date:
        try:
            # 支持两种格式：YYYY-MM-DD (HTML date input) 和 ISO 8601
            if 'T' not in end_date:
                # HTML date input 格式: YYYY-MM-DD，包含整天
                end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)
            else:
                # ISO 8601 格式
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00')) + timedelta(days=1)
            conditions.append(AuditLog.created_at < end_dt)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="结束日期格式无效，请使用 YYYY-MM-DD 或 ISO 8601 格式"
            )

    # 查询总数
    count_query = select(func.count(AuditLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 计算分页
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    # 查询审计日志（关联 users 表获取用户名，按操作时间降序排列）
    # 满足 Story 4.4 Subtask 5.4: 关联 users 表获取用户名
    query = (
        select(
            AuditLog.id,
            AuditLog.action,
            AuditLog.result,
            AuditLog.details,
            AuditLog.user_id,
            AuditLog.ip_address,
            AuditLog.created_at,
            AuditLog.resource_type,
            AuditLog.resource_id,
            AuditLog.status,
            User.username.label('db_username'),
        )
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .order_by(AuditLog.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    log_rows = result.all()

    # 构建响应数据
    items = []
    for row in log_rows:
        # 优先使用 JOIN 获取的用户名，回退到 AuditLog.username
        username = row.db_username if row.db_username else row.username or '未知用户'

        item = {
            "id": str(row.id),
            "action_type": row.action,
            "action_details": row.result or row.details or "",
            "user_id": str(row.user_id),
            "username": username,
            "ip_address": row.ip_address or "",
            "created_at": row.created_at.isoformat(),
            "status": row.status,
        }
        if row.resource_type:
            item["resource_type"] = row.resource_type
        if row.resource_id:
            item["resource_id"] = str(row.resource_id)
        items.append(item)

    # 记录查看审计日志的操作（NFR-SEC-006, NFR-SEC-007）
    from src.services.audit_service import AuditService
    await AuditService.log_action(
        db=db,
        user=current_user,
        action="view_audit_logs",
        resource_type="audit_logs",
        details=f"查看审计日志，第 {page} 页，筛选条件：action_type={action_type}, user_id={user_id}",
        ip_address=client_ip,
        user_agent=user_agent,
        status="success",
        result=f"查看成功，共 {total} 条记录",
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    }


@router.post("/audit-logs/cleanup")
async def cleanup_old_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    清理 6 个月前的审计日志

    此端点供系统定时任务调用，自动清理过期日志。
    满足 NFR-SEC-008 要求：审计日志应保留至少 6 个月。

    权限：仅管理员

    返回：
        - deleted_count: 删除的日志数量
    """
    # 获取客户端信息
    client_ip = request.client.host if request.client else None

    # 验证管理员权限
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="权限不足：仅管理员可执行此操作"
        )

    # 计算 6 个月前的日期（NFR-SEC-008）
    six_months_ago = datetime.now() - timedelta(days=180)

    # 统计要删除的日志数量
    count_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at < six_months_ago
    )
    count_result = await db.execute(count_query)
    deleted_count = count_result.scalar() or 0

    # 删除过期日志
    if deleted_count > 0:
        delete_stmt = delete(AuditLog).where(
            AuditLog.created_at < six_months_ago
        )
        await db.execute(delete_stmt)
        await db.commit()

    # 记录清理操作
    from src.services.audit_service import AuditService
    await AuditService.log_action(
        db=db,
        user=current_user,
        action="cleanup_audit_logs",
        resource_type="audit_logs",
        details=f"清理 6 个月前的审计日志",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        status="success",
        result=f"清理完成，删除 {deleted_count} 条过期日志",
    )
    await db.commit()

    return {
        "success": True,
        "data": {
            "deleted_count": deleted_count,
        }
    }
