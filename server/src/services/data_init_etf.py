"""ETF 数据采集服务（第 14 期）

负责从 Tushare 拉取 ETF 基础信息与日份额/净值并写入数据库。
仿 ``FundDataInitService``（progress/cancel 回调 + pg upsert）范式。

- ``sync_etf_basic()``：拉 ETF 清单 → 经 EtfIndexClassifier 归类 → upsert etf_basic。
- ``sync_etf_daily(trade_date)``：拉当日份额 → 逐只拉净值 → 查前日份额 →
  计算 share_change / net_inflow → upsert etf_daily。

净流入额公式（ADR-3）：``net_inflow = share_change(万份) × unit_nav / 10000``（亿元）。
采集时即计算并存储，查询直接读现成字段。
"""

import logging
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.etf import EtfBasic, EtfDaily
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.etf_index_classifier import classify
from src.services.trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)


class EtfDataInitService:
    """ETF 数据采集服务

    提供 ETF 基础信息同步（sync_etf_basic）与日份额/净值采集（sync_etf_daily）。
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        初始化服务

        Args:
            session: 数据库异步会话。为 None 时由调用方（如 collector）传入。
        """
        self.session = session
        self._progress_callback: Optional[callable] = None
        self._cancel_check: Optional[callable] = None

    def set_session(self, session: AsyncSession):
        """设置数据库会话（collector 模式下由外部注入）"""
        self.session = session

    def set_progress_callback(self, callback: callable):
        """设置进度回调，签名 (current: int, total: int, message: str)"""
        self._progress_callback = callback

    def set_cancel_check(self, check: callable):
        """设置取消检查回调，返回 bool（True = 已取消）"""
        self._cancel_check = check

    async def _check_cancelled(self):
        if self._cancel_check:
            if asyncio.iscoroutinefunction(self._cancel_check):
                cancelled = await self._cancel_check()
            else:
                cancelled = self._cancel_check()
            if cancelled:
                raise asyncio.CancelledError("任务已被用户取消")

    async def _update_progress(self, current: int, total: int, message: str):
        if self._progress_callback:
            try:
                if asyncio.iscoroutinefunction(self._progress_callback):
                    await self._progress_callback(current, total, message)
                else:
                    self._progress_callback(current, total, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    # ------------------------------------------------------------------
    # sync_etf_basic：ETF 基础信息 + 指数归类
    # ------------------------------------------------------------------

    async def sync_etf_basic(self) -> dict:
        """同步 ETF 基础信息并归类指数。

        流程（仿 FundDataInitService.sync_fund_basic）：
        1. 调 get_fund_basic_etf() 拉 ETF 清单
        2. 逐条经 EtfIndexClassifier.classify 得 index_name / category
        3. upsert etf_basic（冲突键 ts_code，on_conflict_do_update 覆盖字段）

        Returns:
            {"added": int, "updated": int, "failed": int, "skipped": int}
            （added/upsert 处理数；upsert 无法精确区分 insert/update，
             added=成功 upsert 条数，updated 固定 0）
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        added = 0
        failed = 0
        skipped = 0
        other_samples = []  # 归类失败（other）样本，便于日志核对

        await self._update_progress(0, 1, "正在从 Tushare 拉取 ETF 基础信息...")

        try:
            records = tushare.get_fund_basic_etf()
        except Exception as e:
            logger.error(f"拉取 ETF 基础信息失败: {e}")
            raise

        total = len(records)
        logger.info(f"拉取到 {total} 条 ETF 基础信息")
        await self._update_progress(0, total, f"共 {total} 条 ETF 待归类入库")

        for i, record in enumerate(records, 1):
            try:
                ts_code = record.get("ts_code")
                name = record.get("name")

                if not ts_code:
                    failed += 1
                    continue

                benchmark = record.get("benchmark")
                # 归类：宽基精确枚举 + 行业关键词 + other 兜底（不抛异常）
                index_name, category = classify(benchmark, name)
                if category == "other" and len(other_samples) < 20:
                    other_samples.append({"ts_code": ts_code, "name": name,
                                          "benchmark": benchmark})

                list_date = self._parse_date(record.get("list_date"))

                stmt = pg_insert(EtfBasic).values(
                    ts_code=ts_code,
                    name=name,
                    management=record.get("management"),
                    fund_type=record.get("fund_type"),
                    list_date=list_date,
                    benchmark=benchmark,
                    index_name=index_name,
                    category=category,
                    status=record.get("status"),
                    market=record.get("market", "E"),
                )
                update_cols = {
                    "name": stmt.excluded.name,
                    "management": stmt.excluded.management,
                    "fund_type": stmt.excluded.fund_type,
                    "list_date": stmt.excluded.list_date,
                    "benchmark": stmt.excluded.benchmark,
                    "index_name": stmt.excluded.index_name,
                    "category": stmt.excluded.category,
                    "status": stmt.excluded.status,
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ts_code"],
                    set_=update_cols,
                )
                await self.session.execute(stmt)
                added += 1

            except Exception as e:
                failed += 1
                logger.warning(f"写入 ETF 基础信息 {record.get('ts_code')} 失败: {e}")
                continue

            if i % 200 == 0 or i == total:
                await self._update_progress(i, total, f"已处理 {i}/{total} 条 ETF 基础信息")

        await self.session.commit()

        # 可观测性（架构 §8.5）：记录归类失败数与样本
        if other_samples:
            logger.info(
                f"[ETF] 归类失败（category=other）共记录中样本 {len(other_samples)} 条: "
                f"{other_samples[:10]}"
            )

        logger.info(
            f"[ETF] 基础信息同步完成: 总计 {total}, 入库 {added}, 失败 {failed}"
        )
        await self._update_progress(
            total, total,
            f"ETF 基础信息同步完成: 入库 {added}, 失败 {failed}"
        )

        return {
            "added": added,
            "updated": 0,
            "failed": failed,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # sync_etf_daily：当日份额/净值采集 + share_change/net_inflow 计算
    # ------------------------------------------------------------------

    async def sync_etf_daily(self, trade_date: str) -> dict:
        """采集 ETF 当日份额/净值并计算 share_change / net_inflow 落库。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260729'）。

        流程：
        1. 调 get_fund_share(trade_date) 拉当日 ETF 份额（约 700 条）。
        2. 取净值：对当日有份额的 ts_code，**逐只调 get_fund_nav(ts_code)**
           取 nav_date==trade_date 的 unit_nav（fund_nav 按只返回历史，不支持批量）。
        3. 查前一日份额：etf_daily 中 trade_date < 给定日的最大 trade_date 记录的 share。
        4. 计算：share_change = 当日share − 前日share（前日不存在则 null）；
           net_inflow = share_change × unit_nav / 10000（亿元）。
        5. 批量 upsert etf_daily（on_conflict_do_update 覆盖，仿
           collector._update_sector_fund_flow）。
        6. 返回 {processed, added, updated, skipped}。

        change_percent 来源：ETF 二级市场涨跌幅。实测 fund_daily 接口在当前数据源
        返回"Token无效"，首版存 null（TODO，待数据源支持后补取）。
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        target_date = self._parse_trade_date(trade_date)
        # 与 get_fund_nav 的 nav_date 归一化比较用的字符串（YYYYMMDD）
        target_date_str_yyyymmdd = trade_date.replace("-", "")

        processed = 0
        added = 0
        updated = 0
        skipped = 0

        await self._update_progress(0, 1, f"正在拉取 ETF 当日份额 (trade_date={trade_date})...")

        # 1. 拉当日 ETF 份额（fund_share 接口要求 YYYYMMDD 无横杠格式）
        try:
            share_records = tushare.get_fund_share(target_date_str_yyyymmdd)
        except Exception as e:
            logger.error(f"拉取 ETF 份额失败 (trade_date={trade_date}): {e}")
            raise

        total = len(share_records)
        logger.info(f"拉取到 {total} 条 ETF 当日份额 (trade_date={trade_date})")
        await self._update_progress(0, total, f"共 {total} 条 ETF 份额待处理")

        nav_miss_count = 0
        for i, record in enumerate(share_records, 1):
            try:
                ts_code = record.get("ts_code")
                if not ts_code:
                    skipped += 1
                    continue

                fd_share = self._to_decimal(record.get("fd_share"))
                if fd_share is None:
                    skipped += 1
                    continue

                # 2. 逐只取净值，匹配 nav_date == trade_date
                unit_nav = None
                try:
                    nav_records = tushare.get_fund_nav(ts_code)
                    for nav_row in nav_records:
                        nav_date = nav_row.get("nav_date")
                        if self._dates_equal(nav_date, trade_date):
                            unit_nav = self._to_decimal(nav_row.get("unit_nav"))
                            break
                except Exception as e:
                    # 单只净值失败跳过该只净值，net_inflow 存 null（边界场景）
                    logger.warning(f"取 ETF 净值失败 ({ts_code}): {e}")

                if unit_nav is None:
                    nav_miss_count += 1

                # 3. 查前一日份额（trade_date < 给定日的最大 trade_date）
                prev_share = await self._get_prev_share(ts_code, target_date)

                # 4. 计算 share_change / net_inflow
                if prev_share is not None:
                    share_change = fd_share - prev_share
                    if unit_nav is not None:
                        # net_inflow = share_change(万份) × unit_nav / 10000（亿元）
                        net_inflow = (share_change * unit_nav / Decimal("10000"))
                        # 保留 4 位小数与列精度对齐
                        net_inflow = net_inflow.quantize(Decimal("0.0001"))
                    else:
                        net_inflow = None
                else:
                    # 首日（无前日份额）share_change / net_inflow 为 null（架构 §6.1）
                    share_change = None
                    net_inflow = None

                # 5. upsert etf_daily（on_conflict_do_update 覆盖，仿
                #    collector._update_sector_fund_flow）
                stmt = pg_insert(EtfDaily).values(
                    trade_date=target_date,
                    ts_code=ts_code,
                    share=fd_share,
                    unit_nav=unit_nav,
                    share_change=share_change,
                    net_inflow=net_inflow,
                    change_percent=None,  # TODO: fund_daily 接口可用后补取
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_etf_daily_date_code",
                    set_={
                        "share": stmt.excluded.share,
                        "unit_nav": stmt.excluded.unit_nav,
                        "share_change": stmt.excluded.share_change,
                        "net_inflow": stmt.excluded.net_inflow,
                        "change_percent": stmt.excluded.change_percent,
                    },
                )
                await self.session.execute(stmt)
                processed += 1
                added += 1  # upsert 无法精确区分 insert/update，统计为 added

            except Exception as e:
                skipped += 1
                logger.warning(f"处理 ETF 份额记录失败 ({record.get('ts_code')}): {e}")
                continue

            if i % 200 == 0 or i == total:
                await self._update_progress(
                    i, total,
                    f"已处理 {i}/{total} 条 ETF 份额 (净值缺失 {nav_miss_count})"
                )

        await self.session.commit()

        logger.info(
            f"[ETF] 当日份额采集完成 (trade_date={trade_date}): "
            f"处理 {processed}, 跳过 {skipped}, 净值缺失 {nav_miss_count}"
        )
        await self._update_progress(
            total, total,
            f"ETF 当日采集完成: 处理 {processed}, 跳过 {skipped}, 净值缺失 {nav_miss_count}"
        )

        return {
            "processed": processed,
            "added": added,
            "updated": updated,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # backfill_etf_history：按日期范围回填历史（复用 sync_etf_daily 同口径）
    # ------------------------------------------------------------------

    async def backfill_etf_history(self, start_date: str, end_date: str) -> dict:
        """按日期范围回填历史 ETF 数据（ADR-5：复用 sync_etf_daily 同口径）。

        仿 ``init_historical_data_by_date_range``（data_init.py:851）范式：
        日期校验 + 10 年上限 + progress/cancel。

        流程：
        1. 日期校验：start <= end，范围上限 10 年（3650 天）。
        2. 先调 ``self.sync_etf_basic()`` 确保 ETF 基础信息最新（避免回填时缺 etf_basic）。
        3. 用 TradingCalendar 筛选范围内交易日，**按日期升序**逐日循环。
        4. 对每个交易日调用与当日采集**完全相同**的 ``self.sync_etf_daily(trade_date)``
           （含前日份额查询、share_change、net_inflow 计算）。

           **关键：按日期升序保证 share_change 的前日依赖就地满足**——上一日已写入，
           当日 sync_etf_daily 查前日份额（``trade_date < 给定日的最大 trade_date``）
           能命中上一日记录。
        5. 每日处理完调 progress_callback（progress/total），支持 cancel_check。
        6. 某日采集失败计入 failed_days，继续下一日（不中断整体）。

        Args:
            start_date: 起始日期，'YYYY-MM-DD' 或 'YYYYMMDD'。
            end_date: 结束日期，'YYYY-MM-DD' 或 'YYYYMMDD'。

        Returns:
            {"total_days": int, "processed_days": int, "failed_days": int}
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        # 1. 日期校验（仿 init_historical_data_by_date_range）
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if start is None or end is None:
            raise ValueError(f"无效的日期范围: start_date={start_date}, end_date={end_date}")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")

        # 范围上限 10 年（3650 天）
        if (end - start).days > 3650:
            raise ValueError("日期范围不能超过 10 年")

        await self._update_progress(0, 1, "正在同步 ETF 基础信息...")
        # 2. 先同步基础信息，确保回填时 etf_basic 已就绪（ETF 清单 + 指数归类）
        try:
            await self.sync_etf_basic()
        except Exception as e:
            logger.error(f"[ETF] 回填前置 sync_etf_basic 失败，继续尝试逐日回填: {e}")

        # 3. 用交易日历筛选范围内交易日（按日期升序）
        calendar = TradingCalendar()
        trading_days: List[date] = await calendar.get_trading_days_between(start, end)

        total_days = len(trading_days)
        processed_days = 0
        failed_days = 0

        logger.info(
            f"[ETF] 开始历史回填: {start} ~ {end}, 交易日 {total_days} 天"
        )
        await self._update_progress(
            0, max(total_days, 1),
            f"历史回填范围 {start} ~ {end}，共 {total_days} 个交易日"
        )

        if total_days == 0:
            logger.info(f"[ETF] 回填范围 {start} ~ {end} 内无交易日，跳过")
            return {
                "total_days": total_days,
                "processed_days": processed_days,
                "failed_days": failed_days,
            }

        # 4. 按日期升序逐日调 sync_etf_daily（同口径，前日依赖就地满足）
        for i, trade_date in enumerate(trading_days, 1):
            await self._check_cancelled()
            # sync_etf_daily 内部 _parse_trade_date 兼容 YYYYMMDD / YYYY-MM-DD
            trade_date_str = trade_date.isoformat()
            try:
                await self.sync_etf_daily(trade_date_str)
                processed_days += 1
            except asyncio.CancelledError:
                # 取消：已处理日保留，向上抛出
                logger.warning(f"[ETF] 历史回填在 {trade_date_str} 被取消")
                raise
            except Exception as e:
                failed_days += 1
                logger.warning(
                    f"[ETF] 历史回填 {trade_date_str} 失败，跳过该日: {e}"
                )

            await self._update_progress(
                i, total_days,
                f"历史回填进度 {i}/{total_days}（{trade_date_str}）"
            )

        logger.info(
            f"[ETF] 历史回填完成: 总计 {total_days}, 成功 {processed_days}, "
            f"失败 {failed_days}"
        )
        await self._update_progress(
            total_days, total_days,
            f"历史回填完成: 成功 {processed_days}, 失败 {failed_days}"
        )

        return {
            "total_days": total_days,
            "processed_days": processed_days,
            "failed_days": failed_days,
        }

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    async def _get_prev_share(
        self, ts_code: str, target_date: date
    ) -> Optional[Decimal]:
        """查询某 ts_code 在 target_date 之前最近一日的份额。

        子查询语义：SELECT share FROM etf_daily
                   WHERE ts_code=? AND trade_date<? ORDER BY trade_date DESC LIMIT 1

        Returns:
            前一日份额（Decimal）或 None（首日无前日数据）
        """
        stmt = (
            select(EtfDaily.share)
            .where(
                EtfDaily.ts_code == ts_code,
                EtfDaily.trade_date < target_date,
            )
            .order_by(EtfDaily.trade_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        return row[0]

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        """解析日期字符串，兼容 YYYYMMDD 与 YYYY-MM-DD"""
        if value is None:
            return None
        try:
            s = str(value).strip()
            if not s or s == "None":
                return None
            for fmt in ("%Y%m%d", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_trade_date(value: str) -> date:
        """将 trade_date（YYYYMMDD 或 YYYY-MM-DD）转为 date 对象"""
        d = EtfDataInitService._parse_date(value)
        if d is None:
            raise ValueError(f"无效的 trade_date: {value}")
        return d

    @staticmethod
    def _dates_equal(nav_date, trade_date: str) -> bool:
        """比较 fund_nav 返回的 nav_date 与目标 trade_date 是否同一天。

        兼容 YYYYMMDD（如 20260729）与 YYYY-MM-DD（如 2026-07-29）两种格式。
        """
        if nav_date is None:
            return False
        a = str(nav_date).strip().replace("-", "")
        b = str(trade_date).strip().replace("-", "")
        return a == b

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """安全转 Decimal，失败返回 None"""
        if value is None:
            return None
        try:
            f = float(value)
            return Decimal(str(f))
        except (ValueError, TypeError):
            return None
