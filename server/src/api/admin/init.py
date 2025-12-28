"""
数据初始化 API 端点

提供系统数据初始化相关的 API 接口，需要管理员权限。
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.services.data_init import DataInitService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/init", tags=["Admin - Data Init"])


# 全局任务状态存储（生产环境应使用 Redis 或数据库）
_init_tasks: dict = {}
# 正在运行的任务（用于并发保护）
_running_tasks: set = set()


class InitRequest(BaseModel):
    """初始化请求模型"""
    days: int = Field(60, ge=1, le=365, description="回溯天数")


class InitStatusResponse(BaseModel):
    """初始化状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, running, completed, failed, cancelled")
    current: int = Field(0, description="当前进度")
    total: int = Field(0, description="总数")
    message: str = Field(..., description="当前消息")
    result: Optional[dict] = Field(None, description="最终结果")
    created_at: datetime = Field(..., description="创建时间")


def _check_if_task_running() -> bool:
    """检查是否有任务正在运行"""
    return len(_running_tasks) > 0


@router.post("/sectors", response_model=ApiResponse[dict])
async def init_sectors(
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    初始化板块数据

    从 AkShare 获取板块列表并填充数据库。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有初始化任务正在运行，请等待当前任务完成"
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
    background_tasks.add_task(_run_init_sectors, task_id)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": "板块初始化任务已创建"}
    )


@router.post("/stocks", response_model=ApiResponse[dict])
async def init_stocks(
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    初始化股票数据

    从 AkShare 获取股票列表并填充数据库。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有初始化任务正在运行，请等待当前任务完成"
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
    background_tasks.add_task(_run_init_stocks, task_id)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": "股票初始化任务已创建"}
    )


@router.post("/historical/sectors", response_model=ApiResponse[dict])
async def init_sector_historical(
    request: InitRequest,
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    初始化板块历史行情数据

    从 AkShare 获取指定天数的板块历史数据。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有初始化任务正在运行，请等待当前任务完成"
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
    background_tasks.add_task(_run_init_sector_historical, task_id, request.days)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": f"板块历史数据初始化任务已创建 ({request.days} 天)"}
    )


@router.post("/historical", response_model=ApiResponse[dict])
async def init_historical(
    request: InitRequest,
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    初始化历史行情数据

    从 AkShare 获取指定天数的历史数据。

    Args:
        request: 初始化请求，包含回溯天数
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有初始化任务正在运行，请等待当前任务完成"
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
    background_tasks.add_task(_run_init_historical, task_id, request.days)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": f"历史数据初始化任务已创建 ({request.days} 天)"}
    )


@router.post("/all", response_model=ApiResponse[dict])
async def init_all(
    request: InitRequest,
    background_tasks: BackgroundTasks,
    _admin = Depends(require_admin)
):
    """
    初始化所有数据

    依次执行板块、股票、历史数据初始化。
    """
    # 并发保护
    if _check_if_task_running():
        return ApiResponse(
            success=False,
            data=None,
            message="已有初始化任务正在运行，请等待当前任务完成"
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
    background_tasks.add_task(_run_init_all, task_id, request.days)

    return ApiResponse(
        success=True,
        data={"task_id": task_id, "message": f"完整初始化任务已创建 ({request.days} 天)"}
    )


@router.get("/status/{task_id}", response_model=ApiResponse[InitStatusResponse])
async def get_init_status(
    task_id: str,
    _admin = Depends(require_admin)
):
    """
    获取初始化任务状态

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
        data=InitStatusResponse(**task)
    )


@router.post("/cancel/{task_id}", response_model=ApiResponse[dict])
async def cancel_init(
    task_id: str,
    _admin = Depends(require_admin)
):
    """
    取消初始化任务

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

    # 如果任务正在运行，需要通过 service 的 cancel 方法来中断
    # 注意：这会在下一个检查点中断任务
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


async def _run_init_sectors(task_id: str):
    """执行板块初始化任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataInitService(session)
            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 定义取消检查函数
            def cancel_check():
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

            # 注入取消检查到 service（通过 monkey patch）
            original_check = service._check_cancelled
            service._check_cancelled = lambda: (cancel_check(), original_check())[1]

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = "正在初始化板块数据"

                result = await service.init_sectors()

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "板块初始化完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"板块初始化任务已取消: {task_id[:8]}")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"板块初始化任务失败: {e}")
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"初始化失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)


async def _run_init_stocks(task_id: str):
    """执行股票初始化任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataInitService(session)
            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 定义取消检查函数
            def cancel_check():
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

            # 注入取消检查到 service
            original_check = service._check_cancelled
            service._check_cancelled = lambda: (cancel_check(), original_check())[1]

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = "正在初始化股票数据"

                result = await service.init_stocks()

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "股票初始化完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"股票初始化任务已取消: {task_id[:8]}")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"股票初始化任务失败: {e}")
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"初始化失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)


async def _run_init_sector_historical(task_id: str, days: int):
    """执行板块历史数据初始化任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataInitService(session)
            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 定义取消检查函数
            def cancel_check():
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

            # 注入取消检查到 service
            original_check = service._check_cancelled
            service._check_cancelled = lambda: (cancel_check(), original_check())[1]

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = f"正在初始化板块历史数据 ({days} 天)"

                result = await service.init_sector_historical_data(days=days)

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "板块历史数据初始化完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"板块历史数据初始化任务已取消: {task_id[:8]}")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"板块历史数据初始化任务失败: {e}")
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"初始化失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)


async def _run_init_historical(task_id: str, days: int):
    """执行历史数据初始化任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        async with AsyncSessionLocal() as session:
            service = DataInitService(session)
            service.set_progress_callback(lambda c, t, m: _update_task_progress(task_id, c, t, m))

            # 定义取消检查函数
            def cancel_check():
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

            # 注入取消检查到 service
            original_check = service._check_cancelled
            service._check_cancelled = lambda: (cancel_check(), original_check())[1]

            try:
                _init_tasks[task_id]["status"] = "running"
                _init_tasks[task_id]["message"] = f"正在初始化历史数据 ({days} 天)"

                result = await service.init_historical_data(days=days)

                # 检查是否在执行过程中被取消
                if _check_task_cancelled(task_id):
                    raise InterruptedError("任务已取消")

                _init_tasks[task_id]["status"] = "completed"
                _init_tasks[task_id]["message"] = "历史数据初始化完成"
                _init_tasks[task_id]["result"] = result

            except InterruptedError:
                logger.info(f"历史数据初始化任务已取消: {task_id[:8]}")
                _init_tasks[task_id]["status"] = "cancelled"
                _init_tasks[task_id]["message"] = "任务已取消"
                _init_tasks[task_id]["result"] = {"cancelled": True}

            except Exception as e:
                logger.error(f"历史数据初始化任务失败: {e}")
                _init_tasks[task_id]["status"] = "failed"
                _init_tasks[task_id]["message"] = f"初始化失败: {str(e)}"
                _init_tasks[task_id]["result"] = {"error": str(e)}
    finally:
        _running_tasks.discard(task_id)


async def _run_init_all(task_id: str, days: int):
    """执行完整初始化任务"""
    from src.db.database import AsyncSessionLocal

    _running_tasks.add(task_id)
    try:
        # 检查取消状态
        if _check_task_cancelled(task_id):
            raise InterruptedError("任务已取消")

        # 1. 初始化板块（现在包含自动建立板块-股票关联）
        await _run_init_sectors(f"{task_id}_sectors")
        if _check_task_cancelled(task_id):
            raise InterruptedError("任务已取消")

        # 2. 初始化股票
        await _run_init_stocks(f"{task_id}_stocks")
        if _check_task_cancelled(task_id):
            raise InterruptedError("任务已取消")

        # 3. 初始化板块历史数据
        await _run_init_sector_historical(f"{task_id}_sector_historical", days)

        if _check_task_cancelled(task_id):
            raise InterruptedError("任务已取消")

        # 4. 初始化股票历史数据
        await _run_init_historical(f"{task_id}_historical", days)

        # 检查最终取消状态
        if _check_task_cancelled(task_id):
            raise InterruptedError("任务已取消")

        # 更新总任务状态
        _init_tasks[task_id]["status"] = "completed"
        _init_tasks[task_id]["message"] = "完整初始化完成"
        _init_tasks[task_id]["result"] = {
            "sectors": _init_tasks.get(f"{task_id}_sectors", {}).get("result"),
            "stocks": _init_tasks.get(f"{task_id}_stocks", {}).get("result"),
            "sector_historical": _init_tasks.get(f"{task_id}_sector_historical", {}).get("result"),
            "stock_historical": _init_tasks.get(f"{task_id}_historical", {}).get("result")
        }

    except InterruptedError:
        logger.info(f"完整初始化任务已取消: {task_id[:8]}")
        _init_tasks[task_id]["status"] = "cancelled"
        _init_tasks[task_id]["message"] = "任务已取消"
        _init_tasks[task_id]["result"] = {"cancelled": True}

    except Exception as e:
        logger.error(f"完整初始化任务失败: {e}")
        _init_tasks[task_id]["status"] = "failed"
        _init_tasks[task_id]["message"] = f"初始化失败: {str(e)}"
    finally:
        _running_tasks.discard(task_id)
