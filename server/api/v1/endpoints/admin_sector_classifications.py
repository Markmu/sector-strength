"""
管理员板块分类 API 端点

提供管理员专用的分类功能：
- 测试分类算法
- 查看运行状态
- 数据修复

所有操作均记录审计日志（NFR-SEC-006, NFR-SEC-007, NFR-SEC-008）
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time

from src.db.database import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User
from src.models.sector import Sector
from src.services.sector_classification_service import SectorClassificationService
from src.services.audit_service import AuditService

router = APIRouter()


@router.post("/sector-classification/test")
async def test_classification_algorithm(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试分类算法

    验证分类算法是否正常工作，对所有板块执行分类计算。

    权限：仅管理员

    审计：操作记录到审计日志（NFR-SEC-006）

    返回：
        - total_count: 总板块数
        - success_count: 成功计算数
        - failure_count: 失败计算数
        - duration_ms: 计算耗时（毫秒）
        - timestamp: 测试时间戳
        - failures: 失败的板块列表（如果有）
    """
    # 获取客户端信息用于审计
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # 验证管理员权限
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="权限不足：仅管理员可执行此操作"
        )

    # 获取所有板块
    result = await db.execute(select(Sector))
    sectors = result.scalars().all()

    if not sectors:
        # 空结果也需要记录审计日志
        await AuditService.log_classification_test(
            db=db,
            user=current_user,
            total_count=0,
            success_count=0,
            failure_count=0,
            duration_ms=0,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        await db.commit()

        return {
            "success": True,
            "data": {
                "total_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "duration_ms": 0,
                "timestamp": datetime.now().isoformat(),
            }
        }

    # 执行分类测试
    start_time = time.time()
    service = SectorClassificationService(db)

    success_count = 0
    failure_count = 0
    failures = []

    for sector in sectors:
        try:
            # 调用分类算法
            await service.calculate_classification(sector.id)
            success_count += 1
        except Exception as e:
            failure_count += 1
            failures.append({
                "sector_id": str(sector.id),
                "sector_name": sector.name,
                "error": str(e),
            })

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    # 构建响应
    test_result = {
        "total_count": len(sectors),
        "success_count": success_count,
        "failure_count": failure_count,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
    }

    # 如果有失败，添加失败详情
    if failures:
        test_result["failures"] = failures

    # 记录审计日志（NFR-SEC-006）
    await AuditService.log_classification_test(
        db=db,
        user=current_user,
        total_count=len(sectors),
        success_count=success_count,
        failure_count=failure_count,
        duration_ms=duration_ms,
        failures=failures if failures else None,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # 提交审计日志
    await db.commit()

    return {
        "success": True,
        "data": test_result,
    }
