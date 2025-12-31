"""
历史数据服务

查询和分析历史强度数据。
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.strength_score import StrengthScore

logger = logging.getLogger(__name__)


class StrengthHistoryService:
    """
    历史数据服务

    查询和分析历史强度数据。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化历史数据服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_stock_history(
        self,
        stock_id: int,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        获取个股历史强度数据

        Args:
            stock_id: 股票ID
            days: 查询天数
            end_date: 结束日期，None 表示今天

        Returns:
            历史数据列表，按日期升序排列
        """
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days - 1)

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == 'stock',
                    StrengthScore.entity_id == stock_id,
                    StrengthScore.period == 'all',
                    StrengthScore.date >= start_date,
                    StrengthScore.date <= end_date
                )
            ).order_by(StrengthScore.date.asc())

            result = await self.session.execute(stmt)
            scores = result.scalars().all()

            return [
                {
                    'date': score.date,
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
                    'current_price': score.current_price,
                }
                for score in scores
            ]

        except Exception as e:
            logger.error(f"获取个股历史失败 (stock_id={stock_id}): {e}")
            return []

    async def get_sector_history(
        self,
        sector_id: int,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        获取板块历史强度数据

        Args:
            sector_id: 板块ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            历史数据列表
        """
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days - 1)

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == 'sector',
                    StrengthScore.entity_id == sector_id,
                    StrengthScore.period == 'all',
                    StrengthScore.date >= start_date,
                    StrengthScore.date <= end_date
                )
            ).order_by(StrengthScore.date.asc())

            result = await self.session.execute(stmt)
            scores = result.scalars().all()

            return [
                {
                    'date': score.date,
                    'score': score.score,
                    'rank': score.rank,
                    'percentile': score.percentile,
                    'strength_grade': score.strength_grade,
                    'price_position_score': score.price_position_score,
                    'ma_alignment_score': score.ma_alignment_score,
                    'current_price': score.current_price,
                }
                for score in scores
            ]

        except Exception as e:
            logger.error(f"获取板块历史失败 (sector_id={sector_id}): {e}")
            return []

    async def get_history_stats(
        self,
        entity_type: str,
        entity_id: int,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        获取历史统计数据

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 统计天数
            end_date: 结束日期

        Returns:
            统计数据字典
        """
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days - 1)

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.period == 'all',
                    StrengthScore.date >= start_date,
                    StrengthScore.date <= end_date,
                    StrengthScore.score.isnot(None)
                )
            )

            result = await self.session.execute(stmt)
            scores = result.scalars().all()

            if not scores:
                return {
                    'entity_id': entity_id,
                    'entity_type': entity_type,
                    'days': days,
                    'data_count': 0,
                    'error': '无历史数据'
                }

            # 计算统计数据（WHERE已过滤NULL，直接提取即可）
            score_values = [s.score for s in scores]

            # 最高/最低/平均
            max_score = max(score_values) if score_values else None
            min_score = min(score_values) if score_values else None
            avg_score = sum(score_values) / len(score_values) if score_values else None

            # 涨跌天数统计
            up_days = sum(1 for i in range(1, len(scores))
                        if scores[i].score and scores[i-1].score
                        and scores[i].score > scores[i-1].score)
            down_days = sum(1 for i in range(1, len(scores))
                          if scores[i].score and scores[i-1].score
                          and scores[i].score < scores[i-1].score)
            flat_days = len(scores) - 1 - up_days - down_days

            # 等级分布
            grade_counts = {}
            for score in scores:
                grade = score.strength_grade or 'Unknown'
                grade_counts[grade] = grade_counts.get(grade, 0) + 1

            # 最新得分
            latest_score = scores[-1].score if scores else None

            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'days': days,
                'data_count': len(scores),
                'latest_score': latest_score,
                'max_score': max_score,
                'min_score': min_score,
                'avg_score': round(avg_score, 2) if avg_score else None,
                'up_days': up_days,
                'down_days': down_days,
                'flat_days': flat_days,
                'grade_distribution': grade_counts,
                'start_date': start_date,
                'end_date': end_date,
            }

        except Exception as e:
            logger.error(f"获取历史统计失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'days': days,
                'error': str(e)
            }

    async def get_latest_score(
        self,
        entity_type: str,
        entity_id: int,
        before_date: Optional[date] = None
    ) -> Optional[Dict]:
        """
        获取最新的强度数据

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            before_date: 日期限制

        Returns:
            最新强度数据，不存在返回 None
        """
        if before_date is None:
            before_date = date.today()

        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.period == 'all',
                    StrengthScore.date <= before_date
                )
            ).order_by(StrengthScore.date.desc()).limit(1)

            result = await self.session.execute(stmt)
            score = result.scalar_one_or_none()

            if not score:
                return None

            return {
                'date': score.date,
                'score': score.score,
                'rank': score.rank,
                'percentile': score.percentile,
                'strength_grade': score.strength_grade,
                'price_position_score': score.price_position_score,
                'ma_alignment_score': score.ma_alignment_score,
                'current_price': score.current_price,
            }

        except Exception as e:
            logger.error(f"获取最新强度失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
            return None
