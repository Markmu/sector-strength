"""
数据初始化脚本

初始化周期配置等基础数据。
"""

import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.period_config import PeriodConfig
from src.core.database import async_session_maker


DEFAULT_PERIOD_CONFIGS = [
    {
        "period": "5d",
        "name": "5日均线",
        "days": 5,
        "weight": 0.15,
        "is_active": True,
    },
    {
        "period": "10d",
        "name": "10日均线",
        "days": 10,
        "weight": 0.20,
        "is_active": True,
    },
    {
        "period": "20d",
        "name": "20日均线",
        "days": 20,
        "weight": 0.25,
        "is_active": True,
    },
    {
        "period": "30d",
        "name": "30日均线",
        "days": 30,
        "weight": 0.20,
        "is_active": True,
    },
    {
        "period": "60d",
        "name": "60日均线",
        "days": 60,
        "weight": 0.20,
        "is_active": True,
    },
]


async def seed_period_configs(session: AsyncSession) -> int:
    """
    初始化周期配置数据

    Args:
        session: 异步数据库会话

    Returns:
        插入的记录数
    """
    # 检查是否已存在数据
    from sqlalchemy import select, func

    count_stmt = select(func.count()).select_from(PeriodConfig)
    result = await session.execute(count_stmt)
    existing_count = result.scalar()

    if existing_count > 0:
        print(f"周期配置已存在 {existing_count} 条记录，跳过初始化")
        return 0

    # 批量插入
    inserted_count = 0
    for config in DEFAULT_PERIOD_CONFIGS:
        period_config = PeriodConfig(**config)
        session.add(period_config)
        inserted_count += 1

    await session.commit()
    print(f"成功初始化 {inserted_count} 条周期配置")
    return inserted_count


async def init_all_data():
    """初始化所有基础数据"""
    async with async_session_maker() as session:
        await seed_period_configs(session)


def main():
    """命令行入口"""
    print("开始初始化基础数据...")
    asyncio.run(init_all_data())
    print("基础数据初始化完成!")


if __name__ == "__main__":
    main()
