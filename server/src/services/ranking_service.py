"""
排名计算服务

计算强度排名和百分位。
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.strength_score import StrengthScore

logger = logging.getLogger(__name__)


class RankingService:
    """
    排名计算服务

    计算和查询强度排名数据。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化排名服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def calculate_rankings(
        self,
        calc_date: Optional[date] = None,
        entity_types: Optional[List[str]] = None
    ) -> Dict:
        """
        计算当日排名

        获取当日所有强度数据，按实体类型分组排名。

        Args:
            calc_date: 计算日期，None 表示使用最新日期
            entity_types: 要排名的实体类型列表，None 表示全部

        Returns:
            排名结果字典
        """
        if calc_date is None:
            calc_date = date.today()

        if entity_types is None:
            entity_types = ['stock', 'sector']

        try:
            results = {}

            for entity_type in entity_types:
                # 获取该实体类型的所有强度数据
                stmt = select(StrengthScore).where(
                    and_(
                        StrengthScore.entity_type == entity_type,
                        StrengthScore.date == calc_date,
                        StrengthScore.period == 'all',
                        StrengthScore.score.isnot(None)
                    )
                )

                result = await self.session.execute(stmt)
                scores = result.scalars().all()

                if not scores:
                    logger.warning(f"{entity_type} 在 {calc_date} 无强度数据")
                    results[entity_type] = {
                        'total': 0,
                        'ranked': 0,
                        'unranked': 0
                    }
                    continue

                # 按得分降序排序
                sorted_scores = sorted(scores, key=lambda x: x.score or 0, reverse=True)
                total = len(sorted_scores)

                # 更新排名和百分位
                for rank, score in enumerate(sorted_scores, start=1):
                    score.rank = rank
                    score.percentile = round((1 - rank / total) * 100, 2) if total > 0 else 0

                results[entity_type] = {
                    'total': total,
                    'ranked': total,
                    'unranked': 0
                }

            await self.session.commit()

            return {
                "success": True,
                "date": calc_date,
                "results": results
            }

        except Exception as e:
            logger.error(f"计算排名失败 (date={calc_date}): {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e),
                "date": calc_date
            }

    async def get_top_rankings(
        self,
        entity_type: str,
        limit: int = 10,
        calc_date: Optional[date] = None
    ) -> List[Dict]:
        """
        获取排名前列的实体

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            limit: 返回数量
            calc_date: 计算日期

        Returns:
            前N名实体列表
        """
        if calc_date is None:
            calc_date = date.today()

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == 'all',
                    StrengthScore.rank.isnot(None)
                )
            ).order_by(StrengthScore.rank.asc()).limit(limit)

            result = await self.session.execute(stmt)
            scores = result.scalars().all()

            return [
                {
                    'entity_id': score.entity_id,
                    'symbol': score.symbol,
                    'score': score.score,
                    'rank': score.rank,
                    'percentile': score.percentile,
                    'strength_grade': score.strength_grade
                }
                for score in scores
            ]

        except Exception as e:
            logger.error(f"获取排名失败 (entity_type={entity_type}, date={calc_date}): {e}")
            return []

    async def get_percentile(
        self,
        score: float,
        entity_type: str,
        calc_date: Optional[date] = None
    ) -> Optional[float]:
        """
        获取得分对应的百分位

        Args:
            score: 强度得分
            entity_type: 实体类型
            calc_date: 计算日期

        Returns:
            百分位 (0-100)，None 表示无法计算
        """
        if calc_date is None:
            calc_date = date.today()

        try:
            # 获取该实体类型的总数和低于该得分数量
            total_stmt = select(func.count(StrengthScore.id)).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == 'all',
                    StrengthScore.score.isnot(None)
                )
            )

            lower_stmt = select(func.count(StrengthScore.id)).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == 'all',
                    StrengthScore.score < score
                )
            )

            total_result = await self.session.execute(total_stmt)
            lower_result = await self.session.execute(lower_stmt)

            total = total_result.scalar()
            lower = lower_result.scalar()

            if total is None or total == 0:
                return None

            percentile = round((1 - lower / total) * 100, 2)
            return percentile

        except Exception as e:
            logger.error(f"计算百分位失败 (score={score}, entity_type={entity_type}): {e}")
            return None

    async def get_entity_ranking(
        self,
        entity_id: int,
        entity_type: str,
        calc_date: Optional[date] = None
    ) -> Optional[Dict]:
        """
        获取特定实体的排名信息

        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            calc_date: 计算日期

        Returns:
            排名信息字典，不存在返回 None
        """
        if calc_date is None:
            calc_date = date.today()

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == 'all'
                )
            )

            result = await self.session.execute(stmt)
            score = result.scalar_one_or_none()

            if not score:
                return None

            return {
                'entity_id': score.entity_id,
                'symbol': score.symbol,
                'score': score.score,
                'rank': score.rank,
                'percentile': score.percentile,
                'strength_grade': score.strength_grade,
                'price_position_score': score.price_position_score,
                'ma_alignment_score': score.ma_alignment_score,
                'ma_alignment_state': score.ma_alignment_state,
                'short_term_score': score.short_term_score,
                'medium_term_score': score.medium_term_score,
                'long_term_score': score.long_term_score,
            }

        except Exception as e:
            logger.error(f"获取实体排名失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
            return None
