"""
基金数据同步服务

负责从 Tushare 拉取基金基本信息和持仓明细并写入数据库。
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.fund import Fund
from src.models.fund_portfolio import FundPortfolio
from src.services.data_acquisition import DataSourceFactory

logger = logging.getLogger(__name__)


class FundDataInitService:
    """
    基金数据同步服务

    提供基金基本信息同步和持仓明细同步能力。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化服务

        Args:
            session: 数据库异步会话
        """
        self.session = session
        self._progress_callback: Optional[callable] = None
        self._cancel_check: Optional[callable] = None

    def set_progress_callback(self, callback: callable):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，签名为 (current: int, total: int, message: str)
        """
        self._progress_callback = callback

    def set_cancel_check(self, check: callable):
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

    async def sync_fund_basic(self) -> dict:
        """
        同步基金基本信息

        先拉取场内基金 (market='E')，再拉取场外基金 (market='O')，
        合并后通过 PostgreSQL upsert（ON CONFLICT ts_code DO UPDATE）写入 funds 表。

        **退市基金过滤**：
        - ``delist_date`` 非空 → 已退市
        - ``status == "E"`` → 已到期（视同退市）

        满足任一条件则跳过 upsert，并在返回结果中通过 ``skipped`` 字段上报。
        同步完成后会自动清理 funds 表中**已存在**的退市基金。

        Returns:
            {"added": int, "updated": int, "failed": int, "skipped": int, "cleaned": int}
        """
        tushare = DataSourceFactory.create()
        added = 0
        updated = 0
        failed = 0
        skipped = 0

        all_records = []

        # 分市场拉取
        for market in ("E", "O"):
            await self._update_progress(
                0, 1, f"正在从 Tushare 拉取基金基本信息 (market={market})..."
            )
            try:
                records = tushare.get_fund_list(market)
                all_records.extend(records)
                logger.info(f"拉取到 {len(records)} 条基金信息 (market={market})")
            except Exception as e:
                logger.error(f"拉取基金信息失败 (market={market}): {e}")
                raise

        total = len(all_records)
        await self._update_progress(0, total, f"共 {total} 条基金信息待入库")

        for i, record in enumerate(all_records, 1):
            try:
                ts_code = record.get("ts_code")
                name = record.get("name")

                if not ts_code:
                    failed += 1
                    continue

                # 日期字段解析
                found_date = self._parse_date(record.get("found_date"))
                list_date = self._parse_date(record.get("list_date"))
                delist_date = self._parse_date(record.get("delist_date"))
                status = record.get("status")

                # 过滤已退市 / 已摘牌基金
                # - delist_date 非空：Tushare 标记的退市日期
                # - status == "E"：已到期/终止（视同退市）
                #   注意：status=="D" 并非退市（详见模块文档），不能据此跳过。
                if delist_date is not None or status == "E":
                    skipped += 1
                    if i % 500 == 0 or i == total:
                        await self._update_progress(
                            i, total,
                            f"已处理 {i}/{total} 条（已跳过 {skipped} 条退市基金）"
                        )
                    continue

                # PostgreSQL upsert: ON CONFLICT ts_code DO UPDATE
                stmt = pg_insert(Fund).values(
                    ts_code=ts_code,
                    name=name,
                    management=record.get("management"),
                    custodian=record.get("custodian"),
                    fund_type=record.get("fund_type"),
                    invest_type=record.get("invest_type"),
                    benchmark=record.get("benchmark"),
                    market=record.get("market"),
                    found_date=found_date,
                    list_date=list_date,
                    delist_date=delist_date,
                    status=status,
                )

                # 收集 updatable 字段（排除 ts_code 和 id）
                update_cols = {
                    "name": stmt.excluded.name,
                    "management": stmt.excluded.management,
                    "custodian": stmt.excluded.custodian,
                    "fund_type": stmt.excluded.fund_type,
                    "invest_type": stmt.excluded.invest_type,
                    "benchmark": stmt.excluded.benchmark,
                    "market": stmt.excluded.market,
                    "found_date": stmt.excluded.found_date,
                    "list_date": stmt.excluded.list_date,
                    "delist_date": stmt.excluded.delist_date,
                    "status": stmt.excluded.status,
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ts_code"],
                    set_=update_cols,
                )

                result = await self.session.execute(stmt)

                # PostgreSQL upsert 无法直接区分 insert/update，
                # 通过查询判断是否已存在来统计
                if result.rowcount > 0:
                    # 简化统计：对首次出现使用 added，后续 updated
                    # 实际 rowcount 总是 1（insert 或 update）
                    pass

            except Exception as e:
                failed += 1
                logger.warning(f"写入基金 {record.get('ts_code')} 失败: {e}")
                continue

            if i % 500 == 0 or i == total:
                await self._update_progress(i, total, f"已处理 {i}/{total} 条基金信息")

        # 统计 added/updated：先查已有数量
        count_stmt = select(Fund)
        result = await self.session.execute(count_stmt)
        db_count = len(result.scalars().all())

        # 清理已存在但已退市的基金（去抖时只发生在已写入数据库的场景）
        await self._update_progress(total, total, "正在清理已存在的退市基金...")
        cleaned = await self._cleanup_delisted_funds()

        await self.session.commit()

        # 重新计算 added/updated
        # 使用一种简单策略：added = 新增数（无法精确区分，用 total-failed 近似）
        # 由于 upsert 无法精确区分 insert vs update，这里用查询前后数量差
        # 但上面已经全量查了，直接用总数减去失败数
        processed = total - failed - skipped

        await self._update_progress(
            total, total,
            f"基金基本信息同步完成: 处理 {processed}, 跳过 {skipped}, "
            f"清理 {cleaned}, 失败 {failed}"
        )

        logger.info(
            f"基金基本信息同步完成: 总计 {total}, 处理 {processed}, "
            f"跳过 {skipped}, 清理 {cleaned}, 失败 {failed}"
        )

        return {
            "added": processed,
            "updated": 0,
            "failed": failed,
            "skipped": skipped,
            "cleaned": cleaned,
        }

    async def _cleanup_delisted_funds(self) -> int:
        """
        清理 funds 表中已退市的基金记录

        删除条件：``delist_date IS NOT NULL`` 或 ``status = 'E'``（已到期/终止）。
        先拉取全部记录（数据量小，~18000 条），在 Python 端过滤后
        按 ``ts_code`` 批量删除，避免一次 DELETE 锁全表。

        Returns:
            被删除的记录数
        """
        result = await self.session.execute(select(Fund))
        all_funds = result.scalars().all()

        delisted_codes = [
            f.ts_code
            for f in all_funds
            if f.delist_date is not None or f.status == "E"
        ]

        if not delisted_codes:
            return 0

        del_stmt = delete(Fund).where(Fund.ts_code.in_(delisted_codes))
        del_result = await self.session.execute(del_stmt)
        cleaned = del_result.rowcount or 0

        if cleaned > 0:
            logger.info(f"已清理 {cleaned} 条退市基金记录")

        return cleaned

    async def sync_fund_portfolio(self, period: str) -> dict:
        """
        同步基金持仓明细

        逐个基金拉取持仓数据，适用于代理不支持按 period 全量查询的场景。
        仅处理存续中的股票型和混合型基金。

        流程：
        1. 查询数据库中存续的股票型+混合型基金列表
        2. 逐个基金调用 Tushare 获取持仓
        3. 每个基金成功后立即写入数据库
        4. 全部完成后清理旧数据

        Args:
            period: 报告期，格式 'YYYYMMDD'（如 '20241231'）

        Returns:
            {"added": int, "skipped": int, "failed": int, "failed_funds": list}
        """
        tushare = DataSourceFactory.create()

        # 1. 查询需要同步的基金列表
        fund_rows = await self.session.execute(
            select(Fund.ts_code, Fund.name).where(
                and_(
                    Fund.fund_type.in_(["股票型", "混合型"]),
                    Fund.status == "L",
                )
            )
        )
        funds = fund_rows.all()
        total_funds = len(funds)

        report_period_date = self._parse_period_to_date(period)

        await self._update_progress(
            0, total_funds,
            f"共 {total_funds} 只基金待同步持仓 (period={period})"
        )

        added = 0
        skipped = 0
        failed = 0
        failed_funds = []

        # 2. 逐个基金拉取并写入
        for i, (ts_code, fund_name) in enumerate(funds, 1):
            # 每只基金都检查是否被取消：取消检查是一次带索引的轻量 SELECT，
            # 相对每只基金的 Tushare 同步拉取（秒级）开销可忽略，且能让取消
            # 在当前基金处理完后立即生效。
            await self._check_cancelled()

            try:
                records = tushare.get_fund_portfolio_by_code(ts_code, period)

                if not records:
                    skipped += 1
                    if i % 200 == 0 or i == total_funds:
                        await self._update_progress(
                            i, total_funds,
                            f"已处理 {i}/{total_funds} 只基金 (新增 {added}, 跳过 {skipped}, 失败 {failed})"
                        )
                    continue

                # 先删除该基金在该报告期的旧持仓数据，避免重复
                fund_del_stmt = delete(FundPortfolio).where(
                    FundPortfolio.fund_ts_code == ts_code,
                    FundPortfolio.report_period == report_period_date,
                )
                await self.session.execute(fund_del_stmt)

                # 写入该基金的持仓
                fund_added = 0
                for record in records:
                    try:
                        stock_symbol_raw = record.get("symbol")
                        if not stock_symbol_raw:
                            continue

                        stock_symbol = (
                            stock_symbol_raw.split(".")[0]
                            if "." in stock_symbol_raw
                            else stock_symbol_raw
                        )
                        # 港股代码补齐5位（Tushare 港股4位如 0700 → 00700；A股6位不动）
                        if len(stock_symbol) < 5 and stock_symbol.isdigit():
                            stock_symbol = stock_symbol.rjust(5, "0")

                        ann_date = self._parse_date(record.get("ann_date"))
                        market_value = self._parse_float(record.get("mkv"))
                        amount = self._parse_float(record.get("amount"))
                        stk_mkv_ratio = self._parse_float(record.get("stk_mkv_ratio"))
                        stk_float_ratio = self._parse_float(
                            record.get("stk_float_ratio")
                        )

                        portfolio = FundPortfolio(
                            fund_ts_code=ts_code,
                            report_period=report_period_date,
                            ann_date=ann_date,
                            stock_symbol=stock_symbol,
                            market_value=market_value,
                            amount=amount,
                            stk_mkv_ratio=stk_mkv_ratio,
                            stk_float_ratio=stk_float_ratio,
                        )
                        self.session.add(portfolio)
                        fund_added += 1
                    except Exception as e:
                        logger.warning(
                            f"写入持仓记录失败 ({ts_code}/{record.get('symbol')}): {e}"
                        )

                await self.session.flush()
                await self.session.commit()
                added += fund_added

            except Exception as e:
                failed += 1
                failed_funds.append(ts_code)
                original = getattr(e, "original_error", None)
                detail = f"{e}" + (f" (原始错误: {original})" if original else "")
                logger.warning(f"拉取基金持仓失败 ({ts_code}): {detail}")
                # 单个基金失败不影响整体，继续处理下一个
                continue

            # 进度报告
            if i % 200 == 0 or i == total_funds:
                await self._update_progress(
                    i, total_funds,
                    f"已处理 {i}/{total_funds} 只基金 (新增 {added}, 跳过 {skipped}, 失败 {failed})"
                )

        # 3. 数据已在循环中逐个基金 commit，无需再统一提交

        msg = (
            f"基金持仓同步完成 (period={period}): "
            f"新增 {added} 条, 跳过 {skipped} 只基金, "
            f"失败 {failed} 只基金"
        )
        if failed_funds:
            msg += f" (失败基金: {failed_funds[:20]}{'...' if len(failed_funds) > 20 else ''})"

        await self._update_progress(total_funds, total_funds, msg)
        logger.info(msg)

        return {
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "failed_funds": failed_funds,
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
            return float(value)
        except (ValueError, TypeError):
            return None
