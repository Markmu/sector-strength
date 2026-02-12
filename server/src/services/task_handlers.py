"""
异步任务处理器

将现有的数据初始化和更新服务包装成异步任务处理器。
"""

import logging
from datetime import date
from typing import Dict, Any
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_executor import TaskRegistry
from src.services.task_manager import TaskManager
from src.services.data_init import DataInitService
from src.services.data_update import DataUpdateService
from src.services.sector_ma_service import SectorMAService
from src.services.sector_strength_service import SectorStrengthService
from src.services.sector_classification_service import SectorClassificationService

logger = logging.getLogger(__name__)


# ============== 任务类型常量 ==============

class TaskType(str, Enum):
    """任务类型枚举，避免硬编码字符串"""

    # 数据初始化任务
    INIT_SECTORS = "init_sectors"
    INIT_STOCKS = "init_stocks"
    INIT_HISTORICAL_DATA = "init_historical_data"
    INIT_SECTOR_HISTORICAL_DATA = "init_sector_historical_data"

    # 数据补齐任务
    BACKFILL_BY_DATE = "backfill_by_date"
    BACKFILL_BY_RANGE = "backfill_by_range"

    # 均线计算任务
    CALCULATE_SECTOR_MA = "calculate_sector_ma"
    BACKFILL_SECTOR_MA_BY_DATE = "backfill_sector_ma_by_date"
    CALCULATE_SECTOR_MA_FULL_HISTORY = "calculate_sector_ma_full_history"

    # 强度计算任务
    CALCULATE_SECTOR_STRENGTH_BY_DATE = "calculate_sector_strength_by_date"
    CALCULATE_SECTOR_STRENGTH_BY_RANGE = "calculate_sector_strength_by_range"
    CALCULATE_SECTOR_STRENGTH_FULL_HISTORY = "calculate_sector_strength_full_history"

    # 板块分类任务
    INIT_SECTOR_CLASSIFICATIONS = "init_sector_classifications"
    UPDATE_SECTOR_CLASSIFICATION_DAILY = "update_sector_classification_daily"


async def _make_progress_callback(manager: TaskManager, task_id: str):
    """
    创建进度回调函数

    Args:
        manager: 任务管理器
        task_id: 任务ID

    Returns:
        进度回调函数
    """
    async def progress_callback(current: int, total: int, message: str):
        await manager.update_progress(task_id, current, total)
        await manager.log_message(task_id, "INFO", f"[{current}/{total}] {message}")

    return progress_callback


@TaskRegistry.register(TaskType.INIT_SECTORS)
async def init_sectors_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块初始化任务

    此任务会：
    1. 从 AkShare 获取板块列表
    2. 创建板块记录

    Args:
        task_id: 任务ID
        params: 任务参数 {"sector_type": "industry" | "concept" | None}
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataInitService(manager.db)
    sector_type = params.get("sector_type")

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(task_id, "INFO", f"Starting sector initialization (type: {sector_type or 'all'})")

    # 执行初始化
    result = await service.init_sectors(sector_type)

    if result.get("success"):
        msg = f"Sector initialization completed: {result.get('created')} created, {result.get('skipped')} skipped"
        await manager.log_message(task_id, "INFO", msg)
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector initialization failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.INIT_STOCKS)
async def init_stocks_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    股票初始化任务

    Args:
        task_id: 任务ID
        params: 任务参数 (空)
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataInitService(manager.db)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(task_id, "INFO", "Starting stock initialization")

    # 执行初始化
    result = await service.init_stocks()

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Stock initialization completed: {result.get('created')} created, {result.get('skipped')} skipped"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Stock initialization failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.INIT_HISTORICAL_DATA)
async def init_historical_data_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    历史数据初始化任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "start_date": "YYYY-MM-DD",  # 开始日期
            "end_date": "YYYY-MM-DD",    # 结束日期
            "symbol_filter": [...] | None  # 可选：股票代码过滤
        }
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataInitService(manager.db)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    # 支持两种参数格式：新的 start_date/end_date 或旧的 days
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")

    if start_date_str and end_date_str:
        # 新格式：使用日期范围
        from datetime import date
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        symbol_filter = params.get("symbol_filter")

        await manager.log_message(
            task_id,
            "INFO",
            f"Starting historical data initialization: {start_date} to {end_date}"
        )

        # 执行初始化（使用日期范围）
        result = await service.init_historical_data_by_date_range(start_date, end_date, symbol_filter)
    else:
        # 旧格式：使用天数（向后兼容）
        days = params.get("days", 60)
        symbol_filter = params.get("symbol_filter")

        await manager.log_message(task_id, "INFO", f"Starting historical data initialization ({days} days)")

        # 执行初始化
        result = await service.init_historical_data(days, symbol_filter)

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Historical data initialization completed: {result.get('created')} records created"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Historical data initialization failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.INIT_SECTOR_HISTORICAL_DATA)
async def init_sector_historical_data_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块历史数据初始化任务

    使用 AkShare 同花顺接口按板块类型路由获取历史数据。

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "start_date": "YYYY-MM-DD",  # 开始日期
            "end_date": "YYYY-MM-DD",    # 结束日期
            "sector_filter": [...] | None  # 可选：板块代码过滤
        }
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataInitService(manager.db)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    # 支持两种参数格式：新的 start_date/end_date 或旧的 days
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    sector_filter = params.get("sector_filter")

    if start_date_str and end_date_str:
        # 新格式：使用日期范围
        from datetime import date, timedelta
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)

        await manager.log_message(
            task_id,
            "INFO",
            f"Starting sector historical data initialization: {start_date} to {end_date}"
        )

        # 执行初始化，直接传递日期范围
        result = await service.init_sector_historical_data(
            start_date=start_date,
            end_date=end_date,
            sector_filter=sector_filter
        )
    else:
        # 旧格式：使用天数（向后兼容）
        days = params.get("days", 60)

        await manager.log_message(task_id, "INFO", f"Starting sector historical data initialization ({days} days)")

        # 执行初始化
        result = await service.init_sector_historical_data(days=days, sector_filter=sector_filter)

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Sector historical data initialization completed: {result.get('created')} records created, {result.get('total_sectors')} sectors processed"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector historical data initialization failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.BACKFILL_BY_DATE)
async def backfill_by_date_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    按日期补齐数据任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "target_date": "YYYY-MM-DD",
            "overwrite": false,
            "target_type": "stock" | "sector" | None,
            "target_id": "000001" | None
        }
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataUpdateService(manager.db)

    # 解析参数
    target_date_str = params.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
    overwrite = params.get("overwrite", False)
    target_type = params.get("target_type")
    target_id = params.get("target_id")

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(
        task_id,
        "INFO",
        f"Starting backfill by date: {target_date} (overwrite={overwrite})"
    )

    # 执行补齐
    result = await service.backfill_by_date(target_date, overwrite, target_type, target_id)

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Backfill completed: {result.get('created')} created, "
            f"{result.get('updated')} updated, {result.get('skipped')} skipped"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Backfill failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.BACKFILL_BY_RANGE)
async def backfill_by_range_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    按时间段补齐数据任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "overwrite": false,
            "target_type": "stock" | "sector" | None,
            "target_id": "000001" | None
        }
        manager: 任务管理器
    """
    # 使用 TaskManager 的会话，而不是创建新的会话
    service = DataUpdateService(manager.db)

    # 解析参数
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    start_date = date.fromisoformat(start_date_str) if start_date_str else date.today()
    end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()
    overwrite = params.get("overwrite", False)
    target_type = params.get("target_type")
    target_id = params.get("target_id")

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(
        task_id,
        "INFO",
        f"Starting backfill by range: {start_date} to {end_date} (overwrite={overwrite})"
    )

    # 执行补齐
    result = await service.backfill_by_range(start_date, end_date, overwrite, target_type, target_id)

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Backfill completed: {result.get('created')} created, "
            f"{result.get('updated')} updated, {result.get('skipped')} skipped"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Backfill failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.CALCULATE_SECTOR_MA)
async def calculate_sector_ma_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块均线计算任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "sector_id": int | None,  # 板块ID，None表示所有板块
            "start_date": "YYYY-MM-DD" | None,  # 开始日期
            "end_date": "YYYY-MM-DD" | None,    # 结束日期
            "periods": [5, 10, 20, ...] | None,  # 均线周期列表
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorMAService(manager.db)

    # 解析参数
    sector_id = params.get("sector_id")
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    periods = params.get("periods")
    overwrite = params.get("overwrite", False)

    # 转换日期
    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else None

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    sector_desc = f"sector {sector_id}" if sector_id else "all sectors"
    date_desc = f"{start_date} to {end_date}" if start_date and end_date else "all available data"
    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector MA calculation: {sector_desc}, {date_desc} (overwrite={overwrite})"
    )

    # 执行计算
    result = await service.calculate_sector_moving_averages(
        sector_id=sector_id,
        start_date=start_date,
        end_date=end_date,
        periods=periods,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector MA calculation completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector MA calculation failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.BACKFILL_SECTOR_MA_BY_DATE)
async def backfill_sector_ma_by_date_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    按日期补齐板块均线任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "target_date": "YYYY-MM-DD",  # 目标日期
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorMAService(manager.db)

    # 解析参数
    target_date_str = params.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
    overwrite = params.get("overwrite", False)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector MA backfill by date: {target_date} (overwrite={overwrite})"
    )

    # 执行补齐
    result = await service.backfill_sector_ma(target_date, overwrite)

    if result.get("success"):
        await manager.log_message(
            task_id,
            "INFO",
            f"Sector MA backfill completed: {result.get('created')} created, "
            f"{result.get('updated')} updated, {result.get('skipped')} skipped"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector MA backfill failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.CALCULATE_SECTOR_MA_FULL_HISTORY)
async def calculate_sector_ma_full_history_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块完整历史均线计算任务

    从板块最早的数据日期开始，逐步计算到最新数据的所有均线数据。

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "sector_id": int | None,  # 板块ID，None表示所有板块
            "periods": [5, 10, 20, ...] | None,  # 均线周期列表
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorMAService(manager.db)

    # 解析参数
    sector_id = params.get("sector_id")
    periods = params.get("periods")
    overwrite = params.get("overwrite", False)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    sector_desc = f"sector {sector_id}" if sector_id else "all sectors"
    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector MA full history calculation: {sector_desc} (overwrite={overwrite})"
    )

    # 执行完整历史计算
    result = await service.calculate_full_history_ma(
        sector_id=sector_id,
        periods=periods,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector MA full history calculation completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector MA full history calculation failed: {error_msg}")
        raise Exception(error_msg)


# 导出任务注册表和注册的任务类型
__all__ = [
    "TaskRegistry",
    "init_sectors_task",
    "init_stocks_task",
    "init_historical_data_task",
    "init_sector_historical_data_task",
    "backfill_by_date_task",
    "backfill_by_range_task",
    "calculate_sector_ma_task",
    "backfill_sector_ma_by_date_task",
    "calculate_sector_ma_full_history_task",
    "calculate_sector_strength_by_date_task",
    "calculate_sector_strength_by_range_task",
    "calculate_sector_strength_full_history_task",
    "init_sector_classifications_task",
    "update_sector_classification_daily_task",
]


# ============== 板块强度计算任务 ==============

@TaskRegistry.register(TaskType.CALCULATE_SECTOR_STRENGTH_BY_DATE)
async def calculate_sector_strength_by_date_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    按日期计算板块强度任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "target_date": "YYYY-MM-DD",  # 目标日期
            "sector_id": int | None,  # 板块ID，None表示所有板块
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorStrengthService(manager.db)

    # 解析参数
    target_date_str = params.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
    sector_id = params.get("sector_id")
    overwrite = params.get("overwrite", False)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    sector_desc = f"sector {sector_id}" if sector_id else "all sectors"
    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector strength calculation by date: {target_date} for {sector_desc} (overwrite={overwrite})"
    )

    # 执行计算
    result = await service.calculate_sector_strength_by_date(
        target_date=target_date,
        sector_id=sector_id,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector strength calculation completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector strength calculation failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.CALCULATE_SECTOR_STRENGTH_BY_RANGE)
async def calculate_sector_strength_by_range_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    按时间段计算板块强度任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "start_date": "YYYY-MM-DD",  # 开始日期
            "end_date": "YYYY-MM-DD",    # 结束日期
            "sector_id": int | None,  # 板块ID，None表示所有板块
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorStrengthService(manager.db)

    # 解析参数
    start_date_str = params.get("start_date")
    end_date_str = params.get("end_date")
    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else None
    sector_id = params.get("sector_id")
    overwrite = params.get("overwrite", False)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    sector_desc = f"sector {sector_id}" if sector_id else "all sectors"
    date_desc = f"{start_date} to {end_date}" if start_date and end_date else "all available data"
    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector strength calculation: {sector_desc}, {date_desc} (overwrite={overwrite})"
    )

    # 执行计算
    result = await service.calculate_sector_strength_by_range(
        sector_id=sector_id,
        start_date=start_date,
        end_date=end_date,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector strength calculation completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector strength calculation failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.CALCULATE_SECTOR_STRENGTH_FULL_HISTORY)
async def calculate_sector_strength_full_history_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块完整历史强度计算任务

    从板块最早的数据日期开始，计算到最新日期的所有强度数据。

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "sector_id": int | None,  # 板块ID，None表示所有板块
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorStrengthService(manager.db)

    # 解析参数
    sector_id = params.get("sector_id")
    overwrite = params.get("overwrite", False)

    # 设置进度回调
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    sector_desc = f"sector {sector_id}" if sector_id else "all sectors"
    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector strength full history calculation: {sector_desc} (overwrite={overwrite})"
    )

    # 执行完整历史计算
    result = await service.calculate_sector_strength_full_history(
        sector_id=sector_id,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector strength full history calculation completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Sector strength calculation failed: {error_msg}")
        raise Exception(error_msg)


# ============== 板块分类数据初始化任务 ==============

@TaskRegistry.register(TaskType.INIT_SECTOR_CLASSIFICATIONS)
async def init_sector_classifications_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块分类历史初始化任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "start_date": "YYYY-MM-DD" | None,  # 起始日期，None表示从最早日期开始
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorClassificationService(manager.db)
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    start_date_str = params.get("start_date")
    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    overwrite = params.get("overwrite", False)

    await manager.log_message(
        task_id,
        "INFO",
        f"Starting sector classification initialization (start_date: {start_date or 'earliest'}, overwrite: {overwrite})"
    )

    result = await service.initialize_classifications(
        start_date=start_date,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Sector classification initialization completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Classification initialization failed: {error_msg}")
        raise Exception(error_msg)


@TaskRegistry.register(TaskType.UPDATE_SECTOR_CLASSIFICATION_DAILY)
async def update_sector_classification_daily_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    板块分类每日增量更新任务

    Args:
        task_id: 任务ID
        params: 任务参数 {
            "target_date": "YYYY-MM-DD" | None,  # 目标日期，None表示今天
            "overwrite": false  # 是否覆盖已有数据
        }
        manager: 任务管理器
    """
    service = SectorClassificationService(manager.db)
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    target_date_str = params.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else None
    overwrite = params.get("overwrite", False)

    await manager.log_message(
        task_id,
        "INFO",
        f"Starting daily classification update (target_date: {target_date or 'today'}, overwrite: {overwrite})"
    )

    result = await service.update_daily_classification(
        target_date=target_date,
        overwrite=overwrite
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)

        await manager.log_message(
            task_id,
            "INFO",
            f"Daily classification update completed: {total} sectors processed, "
            f"{created} created, {updated} updated, {skipped} skipped, cache cleared"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Daily classification update failed: {error_msg}")
        raise Exception(error_msg)
