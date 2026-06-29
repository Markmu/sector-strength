"""
券商月度金股数据同步服务

负责从 Tushare 按月拉取券商金股数据并写入数据库。
按 (ts_code, broker) 去重保留最新 trade_date，先删后写保证幂等性，逐批 commit。
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.broker_recommend import BrokerRecommend
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.tushare_client import TushareDataSource

logger = logging.getLogger(__name__)


class BrokerRecommendDataInitService:
    """
    券商月度金股数据同步服务

    从 Tushare 按月拉取券商金股数据，按 (ts_code, broker) 去重保留最新 trade_date，
    先删后写保证幂等性，逐批 commit 确保部分成功不丢失。
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

    async def sync_broker_recommend(self, month: str) -> dict:
        """
        同步券商月度金股数据

        Args:
            month: 月份，YYYYMM 格式（如 "202605"）

        Returns:
            {"added": int, "failed": int}
        """
        # 1. 月初 date（month 比较键，ADR-1）
        month_date = datetime.strptime(f"{month}01", "%Y%m%d").date()

        # 2. 拉取该月全部券商推荐记录（ADR-2，接口原生支持 month 入参）
        records = await self.tushare.get_broker_recommend(month)

        # 3. 空数据：正常返回，任务正常完成
        if not records:
            logger.warning(f"券商金股数据为空 (month={month})，该月可能尚未发布")
            await self._update_progress(0, 0, f"券商金股数据为空 (month={month})")
            return {"added": 0, "failed": 0}

        # 4. 按 (ts_code, broker) 去重，保留 trade_date 最新一条（ADR-2 护栏）
        # 注意：trade_date 可能为空（部分记录缺失），空值视为最早，不覆盖已有的有效 trade_date
        deduped = {}
        for record in records:
            ts_code = record.get("ts_code")
            broker = record.get("broker")
            if not ts_code or not broker:
                continue
            key = (ts_code, broker)
            existing = deduped.get(key)
            if existing is None:
                deduped[key] = record
            else:
                # trade_date 为 YYYYMMDD 字符串或空，字典序与日期序一致；空串视为最早
                old_td = existing.get("trade_date") or ""
                new_td = record.get("trade_date") or ""
                if new_td > old_td:
                    deduped[key] = record
        records_to_write = list(deduped.values())

        total = len(records_to_write)
        await self._update_progress(
            0, total, f"共 {total} 条券商金股待写入 (month={month})"
        )

        # 5. 先删后写（ADR-1 幂等）：DELETE WHERE month
        await self._check_cancelled()
        del_stmt = delete(BrokerRecommend).where(
            BrokerRecommend.month == month_date
        )
        await self.session.execute(del_stmt)

        # 6. 逐条解析，分批 add_all + flush + commit
        batch_size = 500
        added = 0
        failed = 0
        instances = []
        for record in records_to_write:
            try:
                inst = self._parse_record(record, month_date)
                if inst is not None:
                    instances.append(inst)
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.warning(
                    f"解析券商金股记录失败 ({record.get('ts_code')}/"
                    f"{record.get('broker')}): {e}"
                )

        # 分批写入
        for i in range(0, len(instances), batch_size):
            batch = instances[i : i + batch_size]
            if not batch:
                continue
            await self._check_cancelled()
            try:
                self.session.add_all(batch)
                await self.session.flush()
                await self.session.commit()
                added += len(batch)
                await self._update_progress(
                    min(i + batch_size, total), total,
                    f"已写入 {added}/{total} 条券商金股 (month={month})"
                )
            except Exception as e:
                failed += len(batch)
                logger.warning(
                    f"券商金股批量写入失败 (month={month}, batch={i}-{i + len(batch)}): {e}"
                )
                try:
                    await self.session.rollback()
                except Exception:
                    pass

        msg = (
            f"券商金股同步完成 (month={month}): "
            f"新增 {added} 条, 失败 {failed} 条"
        )
        await self._update_progress(total, total, msg)
        logger.info(msg)

        return {"added": added, "failed": failed}

    @staticmethod
    def _parse_record(record: dict, month_date: date) -> Optional[BrokerRecommend]:
        """
        解析单条券商金股记录为 BrokerRecommend 实例

        字段映射（doc 267 已核实）：ts_code/trade_date/name/broker/reason
        - symbol = ts_code 的数字部分（如 600519.SH → 600519）
        - 缺失必要字段（broker/ts_code）→ 返回 None 跳过
        """
        ts_code = record.get("ts_code")
        broker = record.get("broker")
        if not ts_code or not broker:
            return None

        # 从 ts_code 提取纯数字代码（范式参照 data_init_top10_holder.py line 177-181）
        symbol = ts_code.split(".")[0] if "." in ts_code else ts_code

        trade_date_str = record.get("trade_date")
        trade_date = None
        if trade_date_str:
            try:
                trade_date = datetime.strptime(
                    str(trade_date_str).strip(), "%Y%m%d"
                ).date()
            except (ValueError, TypeError):
                trade_date = None

        return BrokerRecommend(
            month=month_date,
            trade_date=trade_date,
            ts_code=ts_code,
            symbol=symbol,
            broker=broker,
            name=record.get("name"),
            reason=record.get("reason"),
        )
