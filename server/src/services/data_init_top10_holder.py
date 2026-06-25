"""
股票十大流通股东数据同步服务

负责从 Tushare 拉取十大流通股东数据并写入数据库。
逐股票遍历，先删后写保证幂等性，逐股票 commit 确保部分成功不丢失。
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, delete, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import Stock
from src.models.top10_float_holder import Top10FloatHolder
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.models import A_STOCK_EXCHANGES
from src.services.data_acquisition.tushare_client import TushareDataSource

logger = logging.getLogger(__name__)


class Top10HolderDataInitService:
    """
    十大流通股东数据同步服务

    逐股票遍历全市场在市股票，调用 Tushare 获取前十大流通股东数据，
    先删后写保证幂等性，逐股票 commit 确保部分成功不丢失。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化服务

        Args:
            session: 数据库异步会话
        """
        self.session = session
        self.tushare: TushareDataSource = DataSourceFactory.create()
        self._progress_callback = None
        self._cancel_check = None

    def set_progress_callback(self, callback):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，签名为 async (current: int, total: int, message: str)
        """
        self._progress_callback = callback

    def set_cancel_check(self, check):
        """
        设置取消检查回调函数

        Args:
            check: 异步回调函数，返回 bool（True = 已取消）
        """
        self._cancel_check = check

    async def _check_cancelled(self):
        """检查任务是否被取消，如果已取消则抛出异常"""
        if self._cancel_check:
            import asyncio
            if asyncio.iscoroutinefunction(self._cancel_check):
                cancelled = await self._cancel_check()
            else:
                cancelled = self._cancel_check()
            if cancelled:
                raise asyncio.CancelledError("任务已被用户取消")

    async def _update_progress(self, current: int, total: int, message: str):
        """更新进度"""
        if self._progress_callback:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self._progress_callback):
                    await self._progress_callback(current, total, message)
                else:
                    self._progress_callback(current, total, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    async def sync_top10_holders(self, period: str) -> dict:
        """
        同步十大流通股东数据

        逐股票遍历全市场在市股票，调用 Tushare 获取前十大流通股东数据，
        先删后写保证幂等性，逐股票 commit 确保部分成功不丢失。

        Args:
            period: 报告期，格式 'YYYYMMDD'（如 '20241231'）

        Returns:
            {"added": int, "skipped": int, "failed": int,
             "failed_stocks": [{"symbol": str, "reason": str}]}
        """
        # 1. 查询在市股票列表（ts_code 非空即有效股票，不依赖 list_status）
        #    仅 A 股：十大流通股东接口面向 A 股，排除港股（HKEX）
        stock_rows = await self.session.execute(
            select(Stock.symbol, Stock.ts_code).where(
                Stock.ts_code.isnot(None),
                Stock.exchange.in_(A_STOCK_EXCHANGES),
            )
        )
        stocks = stock_rows.all()
        total_stocks = len(stocks)

        report_period_date = self._parse_period_to_date(period)

        await self._update_progress(
            0, total_stocks,
            f"共 {total_stocks} 只股票待同步十大流通股东 (period={period})"
        )

        # 2. 初始化计数器
        added = 0
        skipped = 0
        failed = 0
        failed_stocks = []

        # 3. 遍历股票列表
        for i, (symbol, ts_code) in enumerate(stocks, 1):
            # 每 50 只检查一次取消
            if i % 50 == 0:
                await self._check_cancelled()

            # ts_code 为空时尝试转换
            if not ts_code:
                ts_code = TushareDataSource._symbol_to_ts_code(symbol)
                if not ts_code or "." not in ts_code:
                    skipped += 1
                    logger.warning(
                        f"股票 {symbol} 无 ts_code 且无法转换，跳过",
                        extra={
                            "action": "skip_no_tscode",
                            "symbol": symbol,
                            "period": period,
                        },
                    )
                    await self._update_progress(
                        i, total_stocks,
                        f"已处理 {i}/{total_stocks} 只股票 "
                        f"(新增 {added}, 跳过 {skipped}, 失败 {failed})"
                    )
                    continue

            try:
                records = await self.tushare.get_top10_float_holders(ts_code, period)

                # 空数据：正常跳过（ADR-5）
                if not records:
                    skipped += 1
                    await self._update_progress(
                        i, total_stocks,
                        f"已处理 {i}/{total_stocks} 只股票 "
                        f"(新增 {added}, 跳过 {skipped}, 失败 {failed})"
                    )
                    continue

                # DELETE：先删后写（ADR-1）
                del_stmt = delete(Top10FloatHolder).where(
                    and_(
                        Top10FloatHolder.symbol == symbol,
                        Top10FloatHolder.report_period == report_period_date,
                    )
                )
                await self.session.execute(del_stmt)

                # 解析返回数据，逐条创建 Top10FloatHolder 实例
                instances = []
                for record in records:
                    try:
                        # 从 ts_code 提取纯数字代码（确保 symbol 一致性）
                        record_ts_code = record.get("ts_code", ts_code)
                        record_symbol = (
                            record_ts_code.split(".")[0]
                            if "." in record_ts_code
                            else symbol
                        )

                        ann_date = self._parse_date(record.get("ann_date"))
                        hold_amount = self._parse_float(record.get("hold_amount"))
                        hold_ratio = self._parse_float(record.get("hold_ratio"))
                        hold_float_ratio = self._parse_float(
                            record.get("hold_float_ratio")
                        )
                        hold_change = self._parse_float(record.get("hold_change"))
                        holder_type = record.get("holder_type")
                        holder_name = record.get("holder_name")

                        if not holder_name:
                            continue

                        holder = Top10FloatHolder(
                            symbol=record_symbol,
                            ts_code=record_ts_code,
                            report_period=report_period_date,
                            ann_date=ann_date,
                            holder_name=holder_name,
                            hold_amount=hold_amount,
                            hold_ratio=hold_ratio,
                            hold_float_ratio=hold_float_ratio,
                            hold_change=hold_change,
                            holder_type=holder_type,
                        )
                        instances.append(holder)
                    except Exception as e:
                        logger.warning(
                            f"解析股东记录失败 ({symbol}/{record.get('holder_name')}): {e}",
                            extra={
                                "action": "parse_record_error",
                                "symbol": symbol,
                                "period": period,
                                "error": str(e),
                            },
                        )

                if instances:
                    self.session.add_all(instances)
                    await self.session.flush()
                    await self.session.commit()
                    added += len(instances)

            except Exception as e:
                failed += 1
                original_error = getattr(e, "original_error", None)
                detail = f"{e}" + (
                    f" (原始错误: {original_error})" if original_error else ""
                )
                failed_stocks.append({"symbol": symbol, "reason": detail})
                logger.warning(
                    f"同步股票十大流通股东失败 ({symbol}): {detail}",
                    extra={
                        "action": "sync_stock_error",
                        "symbol": symbol,
                        "period": period,
                        "error": detail,
                    },
                )
                # rollback 该股票的写入，继续下一只
                try:
                    await self.session.rollback()
                except Exception:
                    pass
                continue

            # 4. 每只股票处理完后回调进度
            await self._update_progress(
                i, total_stocks,
                f"已处理 {i}/{total_stocks} 只股票 "
                f"(新增 {added}, 跳过 {skipped}, 失败 {failed})"
            )

        # 5. 返回结果
        msg = (
            f"股票十大流通股东同步完成 (period={period}): "
            f"新增 {added} 条, 跳过 {skipped} 只股票, "
            f"失败 {failed} 只股票"
        )
        if failed_stocks:
            msg += (
                f" (失败股票: {[s['symbol'] for s in failed_stocks[:20]]}"
                f"{'...' if len(failed_stocks) > 20 else ''})"
            )

        await self._update_progress(total_stocks, total_stocks, msg)
        logger.info(msg)

        return {
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "failed_stocks": failed_stocks,
        }

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        """解析日期字符串，支持 YYYYMMDD 格式"""
        if value is None:
            return None
        try:
            s = str(value).strip()
            if not s or s == "None":
                return None
            return datetime.strptime(s, "%Y%m%d").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_period_to_date(period) -> date:
        """将 YYYYMMDD 格式的报告期字符串转为 date"""
        return datetime.strptime(str(period), "%Y%m%d").date()

    @staticmethod
    def _parse_float(value) -> Optional[float]:
        """安全解析浮点数"""
        if value is None:
            return None
        try:
            f = float(value)
            import math
            if math.isnan(f):
                return None
            return f
        except (ValueError, TypeError):
            return None
