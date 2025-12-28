"""
计算结果持久化服务

负责将强度计算结果保存到数据库。
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.sector_repository import SectorRepository
from src.repositories.stock_repository import StockRepository

logger = logging.getLogger(__name__)


class CalculationResultSaver:
    """
    计算结果持久化服务

    将强度得分和趋势方向保存到对应的实体表。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化结果保存服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.sector_repo = SectorRepository(session)
        self.stock_repo = StockRepository(session)

    async def save_calculation_results(
        self,
        entity_type: str,
        entity_id: int,
        strength_score: Optional[float],
        trend_direction: int,
    ) -> bool:
        """
        保存计算结果到实体表

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体 ID
            strength_score: 强度得分 (0-100)
            trend_direction: 趋势方向 (1=上升, 0=横盘, -1=下降)

        Returns:
            是否保存成功
        """
        try:
            if strength_score is None:
                logger.warning(f"[结果保存] {entity_type} ID={entity_id} 强度得分为 None，跳过保存")
                return False

            if entity_type == "sector":
                await self.sector_repo.update_strength_score(entity_id, strength_score)
                await self.sector_repo.update_trend_direction(entity_id, trend_direction)
                logger.info(f"[结果保存] 板块 ID={entity_id} 强度得分={strength_score:.2f}, 趋势={trend_direction}")
                return True

            elif entity_type == "stock":
                await self.stock_repo.update_strength_score(entity_id, strength_score)
                await self.stock_repo.update_trend_direction(entity_id, trend_direction)
                logger.info(f"[结果保存] 股票 ID={entity_id} 强度得分={strength_score:.2f}, 趋势={trend_direction}")
                return True

            else:
                logger.error(f"[结果保存] 不支持的实体类型: {entity_type}")
                return False

        except Exception as e:
            logger.error(f"[结果保存] 保存失败: {entity_type} ID={entity_id}, 错误: {e}")
            return False

    async def save_batch_results(
        self,
        results: list[dict],
    ) -> dict:
        """
        批量保存计算结果

        Args:
            results: 结果列表，每个元素包含:
                {
                    "entity_type": str,
                    "entity_id": int,
                    "strength_score": float | None,
                    "trend_direction": int
                }

        Returns:
            保存统计 {"success": int, "failed": int}
        """
        success_count = 0
        failed_count = 0

        for result in results:
            entity_type = result.get("entity_type")
            entity_id = result.get("entity_id")
            strength_score = result.get("strength_score")
            trend_direction = result.get("trend_direction", 0)

            saved = await self.save_calculation_results(
                entity_type, entity_id, strength_score, trend_direction
            )

            if saved:
                success_count += 1
            else:
                failed_count += 1

        logger.info(f"[结果保存] 批量保存完成: 成功={success_count}, 失败={failed_count}")

        return {
            "success": success_count,
            "failed": failed_count,
        }
