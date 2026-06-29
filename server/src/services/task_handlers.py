"""
异步任务处理器

将现有的数据初始化和更新服务包装成异步任务处理器。
"""

import logging
from datetime import date
from typing import Dict, Any
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.async_task import AsyncTask
from src.services.task_executor import TaskRegistry
from src.services.task_manager import TaskManager
from src.services.data_init import DataInitService
from src.services.data_update import DataUpdateService
from src.services.sector_ma_service import SectorMAService
from src.services.sector_strength_service import SectorStrengthService
from src.services.sector_classification_service import SectorClassificationService

# ============== 任务类型常量 ==============

logger = logging.getLogger(__name__)

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

    # 数据状态补齐任务
    BACKFILL_HISTORY = "backfill_history"
    BACKFILL_MA = "backfill_ma"
    BACKFILL_STRENGTH = "backfill_strength"

    # 板块分类任务
    INIT_SECTOR_CLASSIFICATIONS = "init_sector_classifications"
    UPDATE_SECTOR_CLASSIFICATION_DAILY = "update_sector_classification_daily"

    # 基金数据同步任务
    SYNC_FUND_BASIC = "sync_fund_basic"
    SYNC_FUND_PORTFOLIO = "sync_fund_portfolio"

    # 股票十大流通股东同步任务
    SYNC_TOP10_HOLDERS = "sync_top10_holders"

    # 券商月度金股同步任务
    SYNC_BROKER_RECOMMEND = "sync_broker_recommend"


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
    1. 从数据源获取板块列表
    2. 创建板块记录

    Args:
        task_id: 任务ID
        params: 任务参数 {"sector_type": "industry"|"concept"|"region"|None}
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
        msg = (
            f"Sector initialization completed: "
            f"{result.get('created')} created, "
            f"{result.get('updated')} updated, "
            f"{result.get('skipped')} skipped, "
            f"{result.get('deleted')} deleted; "
            f"members: {result.get('members_total')} total, "
            f"{result.get('members_added')} added, "
            f"{result.get('members_removed')} removed"
        )
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

    使用数据源接口按板块类型路由获取历史数据。

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
    "backfill_history_task",
    "backfill_ma_task",
    "backfill_strength_task",
    "sync_fund_basic_task",
    "sync_fund_portfolio_task",
    "sync_top10_holders_task",
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


# ============== 数据状态补齐任务 ==============

@TaskRegistry.register(TaskType.BACKFILL_HISTORY)
async def backfill_history_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """补齐板块历史数据缺口，复用 init_sector_historical_data_task"""
    await init_sector_historical_data_task(task_id, {
        "start_date": params["start_date"],
        "end_date": params["end_date"],
    }, manager)


@TaskRegistry.register(TaskType.BACKFILL_MA)
async def backfill_ma_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """补齐板块均线数据缺口（逐日循环）"""
    from src.services.trading_calendar import TradingCalendar

    start_date = date.fromisoformat(params["start_date"])
    end_date = date.fromisoformat(params["end_date"])

    calendar = TradingCalendar()
    trading_days = await calendar.get_trading_days_between(start_date, end_date)

    if not trading_days:
        await manager.log_message(task_id, "INFO", "No trading days in range, skipping")
        return

    total = len(trading_days)
    success_count = 0
    fail_count = 0

    await manager.log_message(
        task_id, "INFO",
        f"Starting MA backfill: {total} trading days from {trading_days[0]} to {trading_days[-1]}"
    )

    for i, target_date in enumerate(trading_days, 1):
        try:
            service = SectorMAService(manager.db)
            await service.backfill_sector_ma(target_date)
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"MA backfill failed for {target_date}: {e}")
            await manager.log_message(
                task_id, "WARNING",
                f"MA backfill failed for {target_date}: {e}"
            )

        await manager.update_progress(task_id, i, total)

    await manager.log_message(
        task_id, "INFO",
        f"MA backfill completed: {success_count} succeeded, {fail_count} failed out of {total}"
    )

    if fail_count == total:
        raise Exception(f"All {total} days failed")


@TaskRegistry.register(TaskType.BACKFILL_STRENGTH)
async def backfill_strength_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """补齐板块强度数据缺口"""
    service = SectorStrengthService(manager.db)

    start_date = date.fromisoformat(params["start_date"])
    end_date = date.fromisoformat(params["end_date"])

    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(
        task_id, "INFO",
        f"Starting strength backfill: {start_date} to {end_date}"
    )

    result = await service.calculate_sector_strength_by_range(
        start_date=start_date,
        end_date=end_date,
    )

    if result.get("success"):
        total = result.get("total_sectors", 0)
        created = result.get("created", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)

        await manager.log_message(
            task_id, "INFO",
            f"Strength backfill completed: {total} sectors, "
            f"{created} created, {updated} updated, {skipped} skipped, {errors} errors"
        )
    else:
        error_msg = result.get("error", "Unknown error")
        await manager.log_message(task_id, "ERROR", f"Strength backfill failed: {error_msg}")
        raise Exception(error_msg)


# ============== 基金数据同步任务 ==============

@TaskRegistry.register(TaskType.SYNC_FUND_BASIC)
async def sync_fund_basic_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    基金基本信息同步任务

    从 Tushare 拉取场内+场外基金基本信息，通过 upsert 写入 funds 表。

    Args:
        task_id: 任务ID
        params: 任务参数（无必需参数）
        manager: 任务管理器
    """
    from src.services.data_init_fund import FundDataInitService

    service = FundDataInitService(manager.db)

    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    await manager.log_message(task_id, "INFO", "Starting fund basic info sync")

    try:
        result = await service.sync_fund_basic()

        msg = (
            f"Fund basic info sync completed: "
            f"added={result.get('added')}, "
            f"updated={result.get('updated')}, "
            f"failed={result.get('failed')}, "
            f"skipped={result.get('skipped', 0)}, "
            f"cleaned={result.get('cleaned', 0)}"
        )
        await manager.log_message(task_id, "INFO", msg)
    except Exception as e:
        error_msg = f"Fund basic info sync failed: {e}"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise


@TaskRegistry.register(TaskType.SYNC_FUND_PORTFOLIO)
async def sync_fund_portfolio_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    基金持仓明细同步任务

    逐个基金从 Tushare 拉取指定报告期的持仓明细并写入数据库。
    仅处理存续中的股票型和混合型基金。

    Args:
        task_id: 任务ID
        params: 任务参数 {"period": "YYYYMMDD"}
        manager: 任务管理器
    """
    from src.services.data_init_fund import FundDataInitService

    period = params.get("period")
    if not period:
        error_msg = "Missing required parameter: period"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise ValueError(error_msg)

    service = FundDataInitService(manager.db)

    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    # 设置取消检查：直接查 status 标量列。
    # 注意：不能用 manager.get_task() —— 它返回的 ORM 对象会留在执行器 session 的
    # identity map 里（且 expire_on_commit=False），任务期间外部取消 API 用独立
    # session 写入的 cancelled 状态永远读不到，导致"取消后任务一直跑"。
    async def _check_cancelled():
        result = await manager.db.execute(
            select(AsyncTask.status).where(AsyncTask.task_id == task_id)
        )
        return result.scalar_one_or_none() == "cancelled"

    service.set_cancel_check(_check_cancelled)

    await manager.log_message(
        task_id, "INFO", f"Starting fund portfolio sync (period={period})"
    )

    try:
        result = await service.sync_fund_portfolio(period)

        # 持仓同步成功后清除基金扎堆分析缓存（ADR-6 修订）：
        # 同 report_period 补数据为 DELETE+重写（见 data_init_fund.py），
        # 旧聚合缓存会脏读，必须主动失效整个 fund_crowd 命名空间。
        from src.services.cache.fund_crowd_cache import get_fund_crowd_cache

        await get_fund_crowd_cache().invalidate_all()

        msg = (
            f"Fund portfolio sync completed (period={period}): "
            f"added={result.get('added')}, "
            f"skipped={result.get('skipped')}, "
            f"failed={result.get('failed')}"
        )
        failed_funds = result.get("failed_funds", [])
        if failed_funds:
            msg += f", failed_funds_count={len(failed_funds)}"
        await manager.log_message(task_id, "INFO", msg)
    except Exception as e:
        original_error = getattr(e, "original_error", None)
        detail = f"{e}" + (f" | 原始错误: {original_error}" if original_error else "")
        error_msg = f"Fund portfolio sync failed (period={period}): {detail}"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise


# ============== 股票十大流通股东同步任务 ==============

@TaskRegistry.register(TaskType.SYNC_TOP10_HOLDERS)
async def sync_top10_holders_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    十大流通股东同步任务

    逐只股票从 Tushare 拉取指定报告期的前十大流通股东数据并写入数据库。

    Args:
        task_id: 任务ID
        params: 任务参数 {"period": "YYYYMMDD"}
        manager: 任务管理器
    """
    from src.services.data_init_top10_holder import Top10HolderDataInitService

    period = params.get("period")
    if not period:
        error_msg = "Missing required parameter: period"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise ValueError(error_msg)

    service = Top10HolderDataInitService(manager.db)

    # 设置进度回调（await 异步工厂函数）
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    # 设置取消检查：直接查 status 标量列。
    # 注意：不能用 manager.get_task() —— 它返回的 ORM 对象会留在执行器 session 的
    # identity map 里（且 expire_on_commit=False），任务期间外部取消 API 用独立
    # session 写入的 cancelled 状态永远读不到，导致"取消后任务一直跑"。
    async def _check_cancelled():
        result = await manager.db.execute(
            select(AsyncTask.status).where(AsyncTask.task_id == task_id)
        )
        return result.scalar_one_or_none() == "cancelled"

    service.set_cancel_check(_check_cancelled)

    await manager.log_message(
        task_id, "INFO", f"Starting stock top10 holders sync (period={period})"
    )

    try:
        result = await service.sync_top10_holders(period)

        msg = (
            f"Stock top10 holders sync completed (period={period}): "
            f"added={result.get('added')}, "
            f"skipped={result.get('skipped')}, "
            f"failed={result.get('failed')}"
        )
        failed_stocks = result.get("failed_stocks", [])
        if failed_stocks:
            msg += f", failed_stocks_count={len(failed_stocks)}"
        await manager.log_message(task_id, "INFO", msg)
    except Exception as e:
        original_error = getattr(e, "original_error", None)
        detail = f"{e}" + (f" | 原始错误: {original_error}" if original_error else "")
        error_msg = f"Stock top10 holders sync failed (period={period}): {detail}"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise


# ============== 券商月度金股同步任务 ==============

@TaskRegistry.register(TaskType.SYNC_BROKER_RECOMMEND)
async def sync_broker_recommend_task(
    task_id: str,
    params: Dict[str, Any],
    manager: TaskManager,
) -> None:
    """
    券商月度金股同步任务

    从 Tushare 按月拉取券商金股数据并写入数据库。

    Args:
        task_id: 任务ID
        params: 任务参数 {"month": "YYYYMM"}
        manager: 任务管理器
    """
    from src.services.data_init_broker_recommend import BrokerRecommendDataInitService

    month = params.get("month")
    if not month:
        error_msg = "Missing required parameter: month"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise ValueError(error_msg)

    service = BrokerRecommendDataInitService(manager.db)

    # 设置进度回调（await 异步工厂函数）
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)

    # 设置取消检查：直接查 status 标量列。
    # 注意：不能用 manager.get_task() —— 它返回的 ORM 对象会留在执行器 session 的
    # identity map 里（且 expire_on_commit=False），任务期间外部取消 API 用独立
    # session 写入的 cancelled 状态永远读不到，导致"取消后任务一直跑"。
    async def _check_cancelled():
        result = await manager.db.execute(
            select(AsyncTask.status).where(AsyncTask.task_id == task_id)
        )
        return result.scalar_one_or_none() == "cancelled"

    service.set_cancel_check(_check_cancelled)

    await manager.log_message(
        task_id, "INFO", f"Starting broker recommend sync (month={month})"
    )

    try:
        result = await service.sync_broker_recommend(month)

        msg = (
            f"Broker recommend sync completed (month={month}): "
            f"added={result.get('added')}, "
            f"failed={result.get('failed')}"
        )
        await manager.log_message(task_id, "INFO", msg)
    except Exception as e:
        original_error = getattr(e, "original_error", None)
        detail = f"{e}" + (f" | 原始错误: {original_error}" if original_error else "")
        error_msg = f"Broker recommend sync failed (month={month}): {detail}"
        await manager.log_message(task_id, "ERROR", error_msg)
        raise
