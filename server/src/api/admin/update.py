"""
数据更新 API 端点

提供系统数据更新相关的 API 接口，需要管理员权限。
"""

import logging
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from pydantic import BaseModel, Field, field_validator, ValidationInfo

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.services.data_update import DataUpdateService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/update", tags=["Admin - Data Update"])


# 全局任务状态存储（与 init.py 共享相同的架构）
from src.api.admin.init import _init_tasks, _running_tasks, _check_if_task_running


class ByDateRequest(BaseModel):
    """按日期补齐请求"""
    target_date: date = Field(..., alias="date", description="目标日期")
    overwrite: bool = Field(False, description="是否覆盖已有数据")
    target_type: Optional[str] = Field(None, description="目标类型: all, sector, stock")
    target_id: Optional[str] = Field(None, description="目标 ID: 板块代码或股票代码")

    model_config = {"populate_by_name": True}

    @field_validator('target_type')
    @classmethod
    def validate_target_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ['all', 'sector', 'stock']:
            raise ValueError('target_type 必须是 all, sector 或 stock')
        return v

    @field_validator('target_id')
    @classmethod
    def validate_target_id(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        target_type = info.data.get('target_type') if info.data else None
        if target_type == 'stock' and not v:
            raise ValueError('target_type=stock 时必须提供 target_id')
        if target_type == 'sector' and not v:
            raise ValueError('target_type=sector 时必须提供 target_id')
        return v


class ByRangeRequest(BaseModel):
    """按时间段补齐请求"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    overwrite: bool = Field(False, description="是否覆盖已有数据")
    target_type: Optional[str] = Field(None, description="目标类型: all, sector, stock")
    target_id: Optional[str] = Field(None, description="目标 ID: 板块代码或股票代码")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: date, info: ValidationInfo) -> date:
        start_date = info.data.get('start_date') if info.data else None
        if start_date and v < start_date:
            raise ValueError('end_date 不能早于 start_date')
        if start_date:
            days = (v - start_date).days + 1
            if days > 365:
                raise ValueError('日期范围不能超过 365 天')
        return v

    @field_validator('target_type')
    @classmethod
    def validate_target_type(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ['all', 'sector', 'stock']:
            raise ValueError('target_type 必须是 all, sector 或 stock')
        return v

    @field_validator('target_id')
    @classmethod
    def validate_target_id(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        target_type = info.data.get('target_type') if info.data else None
        if target_type == 'stock' and not v:
            raise ValueError('target_type=stock 时必须提供 target_id')
        if target_type == 'sector' and not v:
            raise ValueError('target_type=sector 时必须提供 target_id')
        return v


class UpdateStatusResponse(BaseModel):
    """更新状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    current: int = Field(0, description="当前进度")
    total: int = Field(0, description="总数")
    message: str = Field(..., description="当前消息")
    result: Optional[dict] = Field(None, description="最终结果")
    created_at: datetime = Field(..., description="创建时间")


@router.post("/by-date", response_model=ApiResponse[dict])
async def update_by_date(
    request: ByDateRequest,
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    按日期补齐数据

    拉取指定日期的所有股票数据。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有数据任务正在运行，请等待当前任务完成"
        )

    # 验证日期不能是未来
    if request.target_date > date.today():
        return ApiResponse(
            success=False,
            data=None,
            message="日期不能是未来"
        )

    task_id = str(uuid.uuid4())

    # 创建任务记录
    _init_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "current": 0,
        "total": 0,
        "message": "任务已创建，等待执行",
        "result": None,
        "created_at": datetime.now()
    }

    # 在后台执行任务
    background_tasks.add_task(_run_update_by_date, task_id, request)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": f"按日期补齐任务已创建 ({request.target_date})"}
    )


@router.post("/by-range", response_model=ApiResponse[dict])
async def update_by_range(
    request: ByRangeRequest,
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    按时间段补齐数据

    拉取指定时间段的所有股票数据。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有数据任务正在运行，请等待当前任务完成"
        )

    # 验证日期不能是未来
    if request.end_date > date.today():
        return ApiResponse(
            success=False,
            data=None,
            message="结束日期不能是未来"
        )

    task_id = str(uuid.uuid4())

    # 创建任务记录
    _init_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "current": 0,
        "total": 0,
        "message": "任务已创建，等待执行",
        "result": None,
        "created_at": datetime.now()
    }

    # 在后台执行任务
    background_tasks.add_task(_run_update_by_range, task_id, request)

    days = (request.end_date - request.start_date).days + 1
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "message": f"按时间段补齐任务已创建 ({request.start_date} 至 {request.end_date}, 共 {days} 天)"
        }
    )


@router.get("/missing-dates", response_model=ApiResponse[dict])
async def get_missing_dates(
    stock_symbol: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin)
):
    """
    查询缺失的日期

    返回指定股票或所有股票缺失数据的日期列表。
    """
    service = DataUpdateService(session)
    result = await service.fetch_missing_dates(stock_symbol, start_date, end_date)

    if result["success"]:
        return ApiResponse(success=True, data=result)
    else:
        return ApiResponse(success=False, data=None, message=result.get("error", "查询失败"))


@router.get("/status/{task_id}", response_model=ApiResponse[UpdateStatusResponse])
async def get_update_status(
    task_id: str,
    _admin = Depends(require_admin)
):
    """
    获取更新任务状态

    Args:
        task_id: 任务ID
    """
    if task_id not in _init_tasks:
        return ApiResponse(
            success=False,
            data=None,
            message="任务不存在"
        )

    task = _init_tasks[task_id]
    return ApiResponse(
        success=True,
        data=UpdateStatusResponse(**task)
    )


@router.post("/cancel/{task_id}", response_model=ApiResponse[dict])
async def cancel_update(
    task_id: str,
    _admin = Depends(require_admin)
):
    """
    取消更新任务

    Args:
        task_id: 任务ID
    """
    if task_id not in _init_tasks:
        return ApiResponse(
            success=False,
            data=None,
            message="任务不存在"
        )

    task = _init_tasks[task_id]

    if task["status"] in ["completed", "failed", "cancelled"]:
        return ApiResponse(
            success=False,
            data=None,
            message=f"任务已 {task['status']}，无法取消"
        )

    # 标记任务为取消状态
    task["status"] = "cancelled"
    task["message"] = "任务已请求取消"

    logger.info(f"任务 {task_id[:8]} 已请求取消")

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": "取消请求已发送"}
    )


# ============== 后台任务函数 ==============

def _check_task_cancelled(task_id: str) -> bool:
    """检查任务是否已被请求取消"""
    if task_id in _init_tasks and _init_tasks[task_id].get("status") == "cancelled":
        return True
    return False


def _update_task_progress(task_id: str, current: int, total: int, message: str):
    """更新任务进度"""
    if task_id in _init_tasks:
        _init_tasks[task_id]["current"] = current
        _init_tasks[task_id]["total"] = total
        _init_tasks[task_id]["message"] = message
        logger.info(f"[{task_id[:8]}] {current}/{total}: {message}")


async def _run_update_by_date(task_id: str, request: ByDateRequest):
    """执行按日期补齐任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataUpdateService(session)

            # 创建历史记录
            await service.create_update_history(
                task_id=task_id,
                update_type="by_date",
                target_type=request.target_type,
                target_id=request.target_id,
                start_date=request.target_date,
                end_date=request.target_date,
                overwrite=request.overwrite
            )

            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 注入取消检查到 service - 使用包装函数而不是 monkey patching
            original_check = service._check_cancelled

            def combined_cancel_check():
                # 首先检查任务是否已被请求取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")
                # 然后执行原始的取消检查
                original_check()

            service._check_cancelled = combined_cancel_check

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = f"正在补齐 {request.target_date} 的数据"

                result = await service.backfill_by_date(
                    target_date=request.target_date,
                    overwrite=request.overwrite,
                    target_type=request.target_type,
                    target_id=request.target_id
                )

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                # 更新历史记录
                await service.update_update_history(
                    task_id=task_id,
                    status="completed",
                    records_created=result.get("created", 0),
                    records_updated=result.get("updated", 0),
                    records_failed=result.get("failed", 0)
                )

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "按日期补齐完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"按日期补齐任务已取消: {task_id[:8]}")
                await service.update_update_history(task_id, "cancelled")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"按日期补齐任务失败: {e}")
                await service.update_update_history(
                    task_id, "failed",
                    error_message=str(e)
                )
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"补齐失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)


async def _run_update_by_range(task_id: str, request: ByRangeRequest):
    """执行按时间段补齐任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataUpdateService(session)

            # 创建历史记录
            await service.create_update_history(
                task_id=task_id,
                update_type="by_range",
                target_type=request.target_type,
                target_id=request.target_id,
                start_date=request.start_date,
                end_date=request.end_date,
                overwrite=request.overwrite
            )

            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 注入取消检查到 service - 使用包装函数而不是 monkey patching
            original_check = service._check_cancelled

            def combined_cancel_check():
                # 首先检查任务是否已被请求取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")
                # 然后执行原始的取消检查
                original_check()

            service._check_cancelled = combined_cancel_check

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = f"正在补齐 {request.start_date} 至 {request.end_date} 的数据"

                result = await service.backfill_by_range(
                    start_date=request.start_date,
                    end_date=request.end_date,
                    overwrite=request.overwrite,
                    target_type=request.target_type,
                    target_id=request.target_id
                )

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                # 更新历史记录
                await service.update_update_history(
                    task_id=task_id,
                    status="completed",
                    records_created=result.get("created", 0),
                    records_updated=result.get("updated", 0),
                    records_failed=result.get("failed", 0)
                )

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "按时间段补齐完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"按时间段补齐任务已取消: {task_id[:8]}")
                await service.update_update_history(task_id, "cancelled")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"按时间段补齐任务失败: {e}")
                await service.update_update_history(
                    task_id, "failed",
                    error_message=str(e)
                )
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"补齐失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)
