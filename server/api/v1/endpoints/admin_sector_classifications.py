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
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import time
import re

from src.db.database import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User
from src.models.sector import Sector
from src.models.sector_classification import SectorClassification
from src.models.audit_log import AuditLog
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


@router.get("/sector-classification/status")
async def get_monitoring_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取分类运行状态监控数据

    返回系统的运行状态信息，包括：
    - 最后计算时间
    - 计算状态（正常/异常/失败）
    - 最近一次计算耗时
    - 今日计算次数
    - 数据完整性信息

    权限：仅管理员

    返回：
        - last_calculation_time: 最后计算时间
        - calculation_status: 计算状态
        - last_calculation_duration_ms: 最近一次计算耗时
        - today_calculation_count: 今日计算次数
        - data_integrity: 数据完整性信息
    """
    # 验证管理员权限
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="权限不足：仅管理员可执行此操作"
        )

    # 获取最后计算时间
    last_classification = await db.execute(
        select(SectorClassification)
        .order_by(SectorClassification.created_at.desc())
        .limit(1)
    )
    last_classification_result = last_classification.scalar_one_or_none()

    if not last_classification_result:
        # 没有任何分类记录
        return {
            "success": True,
            "data": {
                "last_calculation_time": datetime.now().isoformat(),
                "calculation_status": "failed",
                "last_calculation_duration_ms": 0,
                "today_calculation_count": 0,
                "data_integrity": {
                    "total_sectors": 0,
                    "sectors_with_data": 0,
                    "missing_sectors": []
                }
            }
        }

    last_calculation_time = last_classification_result.created_at

    # 检查最近计算是否成功（检查最近一小时内的计算）
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_classifications = await db.execute(
        select(func.count(SectorClassification.id))
        .where(SectorClassification.created_at >= one_hour_ago)
    )
    recent_count = recent_classifications.scalar() or 0

    # 判断计算状态
    if recent_count > 0:
        calculation_status = "normal"
    else:
        # 检查最近一次计算是否有错误（从审计日志）
        recent_error = await db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.action == "test_classification",
                    AuditLog.created_at >= one_hour_ago
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        error_log = recent_error.scalar_one_or_none()

        if error_log and error_log.result and "失败" in error_log.result:
            calculation_status = "failed"
        else:
            calculation_status = "abnormal"

    # 获取最近一次计算耗时（从审计日志）
    recent_test = await db.execute(
        select(AuditLog)
        .where(AuditLog.action == "test_classification")
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    test_log = recent_test.scalar_one_or_none()

    duration_ms = 0
    if test_log and test_log.result:
        # 从 result 解析耗时（格式："测试成功：共 X 个板块，全部计算完成，耗时 Zms"）
        match = re.search(r'耗时(\d+)ms', test_log.result)
        if match:
            duration_ms = int(match.group(1))

    # 统计今日计算次数
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.execute(
        select(func.count(AuditLog.id))
        .where(
            and_(
                AuditLog.action == "test_classification",
                AuditLog.created_at >= today_start
            )
        )
    )
    today_calculation_count = today_count.scalar() or 0

    # 检查数据完整性
    total_sectors = await db.execute(select(func.count(Sector.id)))
    total_sectors_count = total_sectors.scalar() or 0

    # 获取有最新分类数据的板块（最近24小时）
    yesterday = datetime.now() - timedelta(days=1)
    sectors_with_data = await db.execute(
        select(func.count(func.distinct(SectorClassification.sector_id)))
        .where(SectorClassification.created_at >= yesterday)
    )
    sectors_with_data_count = sectors_with_data.scalar() or 0

    # 获取缺失数据的板块
    all_sectors = await db.execute(select(Sector))
    sectors_list = all_sectors.scalars().all()

    missing_sectors = []
    if sectors_with_data_count < total_sectors_count:
        # 获取有数据的板块 ID 列表
        sectors_with_classification = await db.execute(
            select(SectorClassification.sector_id)
            .where(SectorClassification.created_at >= yesterday)
            .distinct()
        )
        sector_ids_with_data = set([row[0] for row in sectors_with_classification.all()])

        # 找出缺失的板块
        for sector in sectors_list:
            if sector.id not in sector_ids_with_data:
                missing_sectors.append({
                    "sector_id": str(sector.id),
                    "sector_name": sector.name
                })

    return {
        "success": True,
        "data": {
            "last_calculation_time": last_calculation_time.isoformat(),
            "calculation_status": calculation_status,
            "last_calculation_duration_ms": duration_ms,
            "today_calculation_count": today_calculation_count,
            "data_integrity": {
                "total_sectors": total_sectors_count,
                "sectors_with_data": sectors_with_data_count,
                "missing_sectors": missing_sectors
            }
        }
    }


@router.post("/sector-classification/fix")
async def fix_sector_classification_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    修复板块分类数据

    重新计算指定板块的分类数据并保存到数据库。

    权限：仅管理员
    审计：操作记录到审计日志（NFR-SEC-006）

    参数：
        - sector_id: 板块 ID（可选，与 sector_name 二选一）
        - sector_name: 板块名称（可选，与 sector_id 二选一）
        - days: 时间范围（最近 N 天）
        - overwrite: 是否覆盖已有数据

    返回：
        - success_count: 成功修复的板块数量
        - failed_count: 失败的板块数量
        - duration_seconds: 修复耗时（秒）
        - sectors: 修复的板块列表
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

    # 解析请求参数
    request_data = await request.json()
    sector_id = request_data.get('sector_id')
    sector_name = request_data.get('sector_name')
    days = request_data.get('days', 30)
    overwrite = request_data.get('overwrite', False)

    # 验证参数
    if not sector_id and not sector_name:
        raise HTTPException(
            status_code=400,
            detail="必须提供板块 ID 或板块名称"
        )

    if sector_id and sector_name:
        raise HTTPException(
            status_code=400,
            detail="只能提供板块 ID 或板块名称其中之一"
        )

    if days <= 0:
        raise HTTPException(
            status_code=400,
            detail="时间范围必须大于 0"
        )

    start_time = time.time()

    # 查询需要修复的板块
    if sector_id:
        # 按 ID 查询单个板块
        sector_query = select(Sector).where(Sector.id == sector_id)
        sector_result = await db.execute(sector_query)
        sectors = [sector_result.scalar_one_or_none()]

        if not sectors[0]:
            raise HTTPException(
                status_code=404,
                detail=f"未找到 ID 为 {sector_id} 的板块"
            )
    else:
        # 按名称查询单个板块
        sector_query = select(Sector).where(Sector.name == sector_name)
        sector_result = await db.execute(sector_query)
        sectors = [sector_result.scalar_one_or_none()]

        if not sectors[0]:
            raise HTTPException(
                status_code=404,
                detail=f"未找到名称为 {sector_name} 的板块"
            )

    # 初始化分类服务
    classification_service = SectorClassificationService(db)

    # 修复结果
    success_count = 0
    failed_count = 0
    sector_results = []

    for sector in sectors:
        try:
            # 检查是否已有分类数据
            start_date = datetime.now().date() - timedelta(days=days)
            existing_query = select(SectorClassification).where(
                and_(
                    SectorClassification.sector_id == sector.id,
                    SectorClassification.classification_date >= start_date
                )
            ).order_by(SectorClassification.classification_date.desc())

            existing_result = await db.execute(existing_query)
            existing_classification = existing_result.scalar_one_or_none()

            # 如果不覆盖且已有数据，跳过
            if not overwrite and existing_classification:
                sector_results.append({
                    "sector_id": str(sector.id),
                    "sector_name": sector.name,
                    "success": False,
                    "error": "已有分类数据且未启用覆盖选项",
                })
                failed_count += 1
                continue

            # 计算分类
            classification_result = await classification_service.calculate_classification(
                sector_id=sector.id
            )

            # 保存或更新分类结果
            if existing_classification and overwrite:
                # 更新已有记录
                existing_classification.classification_level = classification_result.get('classification_level')
                existing_classification.state = classification_result.get('state')
                existing_classification.current_price = classification_result.get('current_price')
                existing_classification.change_percent = classification_result.get('change_percent')
                existing_classification.ma_5 = classification_result.get('ma_5')
                existing_classification.ma_10 = classification_result.get('ma_10')
                existing_classification.ma_20 = classification_result.get('ma_20')
                existing_classification.ma_30 = classification_result.get('ma_30')
                existing_classification.ma_60 = classification_result.get('ma_60')
                existing_classification.ma_90 = classification_result.get('ma_90')
                existing_classification.ma_120 = classification_result.get('ma_120')
                existing_classification.ma_240 = classification_result.get('ma_240')
                existing_classification.price_5_days_ago = classification_result.get('price_5_days_ago')
            else:
                # 创建新记录
                new_classification = SectorClassification(
                    sector_id=sector.id,
                    classification_date=datetime.now().date(),
                    classification_level=classification_result.get('classification_level'),
                    state=classification_result.get('state'),
                    current_price=classification_result.get('current_price'),
                    change_percent=classification_result.get('change_percent'),
                    ma_5=classification_result.get('ma_5'),
                    ma_10=classification_result.get('ma_10'),
                    ma_20=classification_result.get('ma_20'),
                    ma_30=classification_result.get('ma_30'),
                    ma_60=classification_result.get('ma_60'),
                    ma_90=classification_result.get('ma_90'),
                    ma_120=classification_result.get('ma_120'),
                    ma_240=classification_result.get('ma_240'),
                    price_5_days_ago=classification_result.get('price_5_days_ago'),
                )
                db.add(new_classification)

            await db.commit()

            sector_results.append({
                "sector_id": str(sector.id),
                "sector_name": sector.name,
                "success": True,
            })
            success_count += 1

        except Exception as e:
            await db.rollback()
            sector_results.append({
                "sector_id": str(sector.id),
                "sector_name": sector.name,
                "success": False,
                "error": str(e),
            })
            failed_count += 1

    end_time = time.time()
    duration_seconds = end_time - start_time

    # 记录审计日志（NFR-SEC-006, NFR-SEC-007）
    await AuditService.log_action(
        db=db,
        user=current_user,
        action="fix_data",
        resource_type="sector_classification",
        details=f"修复分类数据：成功{success_count}个，失败{failed_count}个",
        ip_address=client_ip,
        user_agent=user_agent,
        status="success" if failed_count == 0 else "partial",
        result=f"耗时{duration_seconds:.2f}秒",
    )
    await db.commit()

    # 清除缓存（Story 4.5 Task 4.6）
    try:
        classification_service.invalidate_cache()
    except Exception as cache_error:
        # 缓存清除失败不应影响修复操作的成功
        pass

    return {
        "success": True,
        "data": {
            "success_count": success_count,
            "failed_count": failed_count,
            "duration_seconds": duration_seconds,
            "sectors": sector_results,
        }
    }
