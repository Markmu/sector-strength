"""
强度快照服务

提供每日快照创建和批量快照功能，用于历史趋势分析。
"""

import logging
import asyncio
from datetime import date, timedelta
from typing import Dict, List, Optional, Callable

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import Stock
from src.models.sector import Sector
from src.models.strength_score import StrengthScore
from src.services.strength_service_v2 import StrengthServiceV2

logger = logging.getLogger(__name__)


class StrengthSnapshotService:
    """
    强度快照服务

    负责创建每日强度快照，用于历史趋势分析。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化快照服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.strength_service = StrengthServiceV2(session)
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        设置进度回调函数

        Args:
            callback: 回调函数 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    async def _report_progress(self, current: int, total: int, message: str):
        """报告进度"""
        if self._progress_callback:
            await self._progress_callback(current, total, message)
        logger.info(f"[{current}/{total}] {message}")

    async def create_daily_snapshot(
        self,
        snapshot_date: Optional[date] = None,
        update_ranks: bool = True
    ) -> Dict:
        """
        创建单日快照

        遍历所有股票和板块，计算当日强度并保存到数据库。

        Args:
            snapshot_date: 快照日期，None 表示使用今天
            update_ranks: 是否更新排名和百分位

        Returns:
            快照结果字典
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        logger.info(f"开始创建 {snapshot_date} 的强度快照")

        total_success = 0
        total_error = 0
        results = {
            "date": snapshot_date,
            "stocks": {"success": 0, "error": 0, "details": []},
            "sectors": {"success": 0, "error": 0, "details": []}
        }

        # 获取所有股票ID
        stock_stmt = select(Stock.id).order_by(Stock.id)
        stock_result = await self.session.execute(stock_stmt)
        stock_ids = [row[0] for row in stock_result.all()]

        # 获取所有板块ID
        sector_stmt = select(Sector.id).order_by(Sector.id)
        sector_result = await self.session.execute(sector_stmt)
        sector_ids = [row[0] for row in sector_result.all()]

        total_entities = len(stock_ids) + len(sector_ids)
        current_count = 0

        # 处理股票快照
        for idx, stock_id in enumerate(stock_ids):
            current_count += 1
            try:
                await self._report_progress(
                    current_count,
                    total_entities,
                    f"计算股票强度 ID: {stock_id}"
                )

                result = await self.strength_service.calculate_stock_strength(
                    stock_id,
                    snapshot_date
                )

                if result.get("success"):
                    total_success += 1
                    results["stocks"]["success"] += 1
                    results["stocks"]["details"].append({
                        "id": stock_id,
                        "success": True,
                        "score": result.get("result", {}).get("composite_score")
                    })
                else:
                    total_error += 1
                    results["stocks"]["error"] += 1
                    results["stocks"]["details"].append({
                        "id": stock_id,
                        "success": False,
                        "error": result.get("error")
                    })

            except Exception as e:
                logger.error(f"股票快照失败 (stock_id={stock_id}): {e}")
                total_error += 1
                results["stocks"]["error"] += 1
                results["stocks"]["details"].append({
                    "id": stock_id,
                    "success": False,
                    "error": str(e)
                })

        # 处理板块快照
        logger.info(f"开始处理板块快照: 共{len(sector_ids)}个板块")
        for idx, sector_id in enumerate(sector_ids):
            current_count += 1
            try:
                await self._report_progress(
                    current_count,
                    total_entities,
                    f"计算板块强度 ID: {sector_id} ({idx+1}/{len(sector_ids)})"
                )

                result = await self.strength_service.calculate_sector_strength(
                    sector_id,
                    snapshot_date
                )

                if result.get("success"):
                    total_success += 1
                    results["sectors"]["success"] += 1
                    results["sectors"]["details"].append({
                        "id": sector_id,
                        "success": True,
                        "score": result.get("result", {}).get("composite_score")
                    })
                else:
                    total_error += 1
                    results["sectors"]["error"] += 1
                    results["sectors"]["details"].append({
                        "id": sector_id,
                        "success": False,
                        "error": result.get("error")
                    })

            except Exception as e:
                logger.error(f"板块快照失败 (sector_id={sector_id}): {e}")
                total_error += 1
                results["sectors"]["error"] += 1
                results["sectors"]["details"].append({
                    "id": sector_id,
                    "success": False,
                    "error": str(e)
                })

        logger.info(
            f"板块快照处理完成: 成功={results['sectors']['success']}, "
            f"失败={results['sectors']['error']}, "
            f"总数={len(sector_ids)}"
        )

        # 更新排名和百分位
        if update_ranks:
            logger.info(f"开始更新排名和百分位: date={snapshot_date}")
            await self._update_ranks_and_percentiles(snapshot_date)

        logger.info(
            f"快照完成: 日期={snapshot_date}, "
            f"成功={total_success}, 失败={total_error}"
        )

        results["summary"] = {
            "total_entities": total_entities,
            "total_success": total_success,
            "total_error": total_error,
            "success_rate": round(total_success / total_entities * 100, 2)
            if total_entities > 0 else 0
        }

        return results

    async def batch_create_snapshots(
        self,
        start_date: date,
        end_date: date,
        update_ranks: bool = True,
        concurrent_limit: int = 1
    ) -> Dict:
        """
        批量创建多日快照

        Args:
            start_date: 开始日期
            end_date: 结束日期
            update_ranks: 是否更新排名和百分位
            concurrent_limit: 并发数限制

        Returns:
            批量快照结果
        """
        if start_date > end_date:
            return {
                "success": False,
                "error": "开始日期不能晚于结束日期"
            }

        # 计算日期范围
        days = (end_date - start_date).days + 1

        if days > 365:
            return {
                "success": False,
                "error": "批量快照最多支持365天"
            }

        logger.info(f"开始批量创建快照: {start_date} 至 {end_date} (共{days}天)")

        results = {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": days,
            "daily_results": [],
            "summary": {
                "total_success": 0,
                "total_error": 0,
                "total_entities_processed": 0
            }
        }

        # 获取股票和板块总数用于进度展示
        stock_stmt = select(Stock.id)
        stock_result = await self.session.execute(stock_stmt)
        total_stocks = len(stock_result.all())

        sector_stmt = select(Sector.id)
        sector_result = await self.session.execute(sector_stmt)
        total_sectors = len(sector_result.all())

        logger.info(f"待处理实体总数: 股票={total_stocks}个, 板块={total_sectors}个")
        logger.info(f"预计总处理量: {days}天 × (股票{total_stocks} + 板块{total_sectors}) = {days * (total_stocks + total_sectors)}个计算任务")

        # 按顺序创建每日快照（避免并发导致的数据一致性问题）
        current_date = start_date
        day_count = 0

        while current_date <= end_date:
            day_count += 1
            try:
                logger.info(f"处理第 {day_count}/{days} 天: {current_date}")

                day_result = await self.create_daily_snapshot(
                    current_date,
                    update_ranks
                )

                results["daily_results"].append(day_result)
                results["summary"]["total_success"] += day_result["summary"]["total_success"]
                results["summary"]["total_error"] += day_result["summary"]["total_error"]
                results["summary"]["total_entities_processed"] += day_result["summary"]["total_entities"]

                # 每日完成后输出进度摘要
                cumulative_success_rate = (
                    results["summary"]["total_success"] /
                    (results["summary"]["total_success"] + results["summary"]["total_error"]) * 100
                    if (results["summary"]["total_success"] + results["summary"]["total_error"]) > 0
                    else 0
                )
                logger.info(
                    f"第 {day_count}/{days} 天完成 - "
                    f"当日: 成功={day_result['summary']['total_success']}, "
                    f"失败={day_result['summary']['total_error']} | "
                    f"累计: 成功={results['summary']['total_success']}, "
                    f"失败={results['summary']['total_error']}, "
                    f"成功率={cumulative_success_rate:.1f}%"
                )

            except Exception as e:
                logger.error(f"日期 {current_date} 快照失败: {e}")
                results["daily_results"].append({
                    "date": current_date,
                    "success": False,
                    "error": str(e)
                })
                results["summary"]["total_error"] += 1

            current_date += timedelta(days=1)

        logger.info(f"批量快照完成: 总成功={results['summary']['total_success']}, "
                   f"总失败={results['summary']['total_error']}")

        results["success"] = True
        return results

    async def _update_ranks_and_percentiles(self, calc_date: date) -> None:
        """
        更新指定日期的排名和百分位

        分别为股票和板块计算排名和百分位。

        Args:
            calc_date: 计算日期
        """
        try:
            # 更新股票排名
            stock_stmt = select(StrengthScore).where(
                StrengthScore.entity_type == "stock",
                StrengthScore.date == calc_date,
                StrengthScore.period == "all",
                StrengthScore.score.isnot(None)
            ).order_by(StrengthScore.score.desc())

            stock_result = await self.session.execute(stock_stmt)
            stock_scores = stock_result.scalars().all()

            total_stocks = len(stock_scores)
            for idx, score in enumerate(stock_scores):
                score.rank = idx + 1
                score.percentile = round(
                    ((total_stocks - idx) / total_stocks) * 100, 2
                ) if total_stocks > 0 else 0

            # 更新板块排名
            sector_stmt = select(StrengthScore).where(
                StrengthScore.entity_type == "sector",
                StrengthScore.date == calc_date,
                StrengthScore.period == "all",
                StrengthScore.score.isnot(None)
            ).order_by(StrengthScore.score.desc())

            sector_result = await self.session.execute(sector_stmt)
            sector_scores = sector_result.scalars().all()

            total_sectors = len(sector_scores)
            for idx, score in enumerate(sector_scores):
                score.rank = idx + 1
                score.percentile = round(
                    ((total_sectors - idx) / total_sectors) * 100, 2
                ) if total_sectors > 0 else 0

            await self.session.commit()
            logger.info(
                f"排名更新完成: 股票={total_stocks}个, "
                f"板块={total_sectors}个, 日期={calc_date}"
            )

        except Exception as e:
            logger.error(f"更新排名失败 (date={calc_date}): {e}")
            await self.session.rollback()
            raise

    async def get_snapshot_status(self, snapshot_date: date) -> Dict:
        """
        获取指定日期的快照状态

        Args:
            snapshot_date: 快照日期

        Returns:
            快照状态信息
        """
        try:
            # 统计股票快照数量
            stock_stmt = select(func.count()).where(
                StrengthScore.entity_type == "stock",
                StrengthScore.date == snapshot_date,
                StrengthScore.period == "all"
            )
            stock_result = await self.session.execute(stock_stmt)
            stock_count = stock_result.scalar() or 0

            # 统计板块快照数量
            sector_stmt = select(func.count()).where(
                StrengthScore.entity_type == "sector",
                StrengthScore.date == snapshot_date,
                StrengthScore.period == "all"
            )
            sector_result = await self.session.execute(sector_stmt)
            sector_count = sector_result.scalar() or 0

            # 获取总股票和板块数
            total_stock_stmt = select(func.count()).select_from(Stock)
            total_stock_result = await self.session.execute(total_stock_stmt)
            total_stocks = total_stock_result.scalar() or 0

            total_sector_stmt = select(func.count()).select_from(Sector)
            total_sector_result = await self.session.execute(total_sector_stmt)
            total_sectors = total_sector_result.scalar() or 0

            return {
                "date": snapshot_date,
                "stocks": {
                    "total": total_stocks,
                    "snapshotted": stock_count,
                    "missing": total_stocks - stock_count,
                    "coverage": round(stock_count / total_stocks * 100, 2)
                    if total_stocks > 0 else 0
                },
                "sectors": {
                    "total": total_sectors,
                    "snapshotted": sector_count,
                    "missing": total_sectors - sector_count,
                    "coverage": round(sector_count / total_sectors * 100, 2)
                    if total_sectors > 0 else 0
                },
                "is_complete": stock_count >= total_stocks and sector_count >= total_sectors
            }

        except Exception as e:
            logger.error(f"获取快照状态失败 (date={snapshot_date}): {e}")
            return {
                "date": snapshot_date,
                "error": str(e)
            }
