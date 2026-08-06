"""申万行业分类数据采集服务

负责从 Tushare 拉取申万行业分类目录与成分股当前快照并写入数据库。
仿 ``LimitDataInitService``（progress/cancel 回调 + delete-then-insert 覆盖）范式。

- ``sync_sw_classify()``：同步申万行业分类目录（L1/L2/L3 共约 511 条）
  - 调 ``get_sw_index_classify(level)`` 逐级拉取
  - delete ``sectors`` 表中 type='sw_industry' 的旧记录 + 批量插入新目录
  - 与同花顺（industry/concept/region）数据完全隔离

- ``sync_sw_members()``：同步申万行业成分股当前快照（约 5889 股 × 3 层级 ≈ 17667 条）
  - 调 ``get_sw_index_member_all()`` 拉取 is_new='Y' 的当前快照
  - 查库内现有申万 sector codes，仅删除这些 code 的成分关联（不动同花顺）
  - 每只股票写 3 条到 ``sector_stocks``（l1_code / l2_code / l3_code 各一条）

两操作均按 delete + insert 全量覆盖，保证幂等可重跑。
"""

import logging
import asyncio
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.sector_types import (
    SW_LEVELS,
    SW_SECTOR_TYPE,
    SW_SRC,
)

logger = logging.getLogger(__name__)


class SwSectorDataInitService:
    """申万行业分类数据采集服务

    提供申万行业分类目录同步（sync_sw_classify）与成分股快照同步（sync_sw_members）。
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
    # sync_sw_classify：申万行业分类目录同步（删旧插新，幂等可重跑）
    # ------------------------------------------------------------------

    async def sync_sw_classify(self) -> dict:
        """同步申万行业分类目录（L1/L2/L3）。

        流程：
        1. 逐级调 get_sw_index_classify(level) 拉取分类（L1→L2→L3）
        2. delete sectors 表中 type='sw_industry' 的旧记录（仅申万，不动同花顺）
        3. 批量插入新分类目录

        Returns:
            {"L1": int, "L2": int, "L3": int, "total": int}
        """
        if self.session is None:
            raise RuntimeError("SwSectorDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        result = {"L1": 0, "L2": 0, "L3": 0, "total": 0}

        await self._update_progress(0, 4, "开始同步申万行业分类目录")

        # 1. 逐级拉取分类（先全部拉到内存，再删旧插新，避免中间态）
        all_records = []
        for i, level in enumerate(SW_LEVELS, 1):
            await self._check_cancelled()
            await self._update_progress(
                i, 4, f"正在拉取申万{level}行业分类 (index_classify)..."
            )
            try:
                records = tushare.get_sw_index_classify(level, src=SW_SRC)
            except Exception as e:
                logger.error(f"拉取申万{level}行业分类失败: {e}")
                raise

            for record in records:
                index_code = record.get("index_code")
                if not index_code:
                    continue
                parent_code = self._to_str(record.get("parent_code"))
                # 一级行业 parent_code 为 '0'，转 None
                if parent_code == "0":
                    parent_code = None
                all_records.append(
                    {
                        "index_code": index_code,
                        "industry_name": self._to_str(record.get("industry_name")),
                        "level": level,
                        "parent_code": parent_code,
                    }
                )
            result[level] = len(records)
            logger.info(f"[SW] 申万{level}行业分类拉取到 {len(records)} 条")

        # 2. 删旧：仅删除申万行业分类（type='sw_industry'），不动同花顺数据
        await self._check_cancelled()
        await self._update_progress(4, 4, "正在写入申万行业分类目录...")
        await self.session.execute(
            delete(Sector).where(Sector.type == SW_SECTOR_TYPE)
        )

        # 3. 插新
        inserted = 0
        for rec in all_records:
            self.session.add(
                Sector(
                    code=rec["index_code"],
                    name=rec["industry_name"],
                    type=SW_SECTOR_TYPE,
                    level=rec["level"],
                    parent_code=rec["parent_code"],
                )
            )
            inserted += 1
        result["total"] = inserted

        await self.session.commit()

        logger.info(
            f"[SW] 申万行业分类目录同步完成: "
            f"L1={result['L1']}, L2={result['L2']}, L3={result['L3']}, "
            f"入库={inserted}"
        )
        await self._update_progress(
            4, 4,
            f"申万行业分类目录同步完成: 一级 {result['L1']} 条, "
            f"二级 {result['L2']} 条, 三级 {result['L3']} 条",
        )

        return result

    # ------------------------------------------------------------------
    # sync_sw_members：申万行业成分股当前快照同步（删旧插新，幂等可重跑）
    # ------------------------------------------------------------------

    async def sync_sw_members(self) -> dict:
        """同步申万行业成分股当前快照（is_new='Y'）。

        流程：
        1. 调 get_sw_index_member_all() 拉取当前快照（约 5889 条）
        2. 查库内现有申万 sector codes 集合
        3. delete sector_stocks 表中 sector_code IN (申万 codes) 的旧关联（仅申万）
        4. 每只股票写 3 条（l1_code / l2_code / l3_code 各一条）

        Returns:
            {"stocks": int, "links": int}
            - stocks：成分股只数（去重后）
            - links：sector_stocks 关联条数（stocks × 3）
        """
        if self.session is None:
            raise RuntimeError("SwSectorDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        result = {"stocks": 0, "links": 0}

        await self._update_progress(0, 3, "开始同步申万行业成分股")

        # 1. 拉取成分股当前快照
        await self._check_cancelled()
        await self._update_progress(1, 3, "正在拉取申万行业成分股 (index_member_all)...")
        try:
            records = tushare.get_sw_index_member_all(src=SW_SRC)
        except Exception as e:
            logger.error(f"拉取申万行业成分股失败: {e}")
            raise

        total = len(records)
        logger.info(f"[SW] 拉取到 {total} 条申万行业成分股记录")
        await self._update_progress(1, 3, f"共 {total} 条成分股记录待处理")

        # 2. 查库内现有申万 sector codes 集合（用于精准删旧）
        sw_codes_result = await self.session.execute(
            select(Sector.code).where(Sector.type == SW_SECTOR_TYPE)
        )
        sw_codes = [row[0] for row in sw_codes_result]
        if not sw_codes:
            raise RuntimeError(
                "申万行业分类目录为空，请先执行「申万分类同步」再同步成分股"
            )
        logger.info(f"[SW] 库内现有申万行业分类 {len(sw_codes)} 条")

        # 3. 删旧：仅删除申万相关的成分关联（不动同花顺）
        #    申万 index_code 统一以 .SI 结尾（如 801010.SI），以此特征精准清理，
        #    既能覆盖当前目录，也能清理历史孤儿数据（sector_code 已不在 sectors 表）。
        await self._check_cancelled()
        await self._update_progress(2, 3, "正在清理旧成分关联...")
        await self.session.execute(
            delete(SectorStock).where(SectorStock.sector_code.like("%.SI"))
        )

        # 4. 插新：每只股票写 3 条（l1/l2/l3 各一条）
        await self._update_progress(3, 3, "正在写入成分股关联...")
        stocks_seen = set()
        links = 0
        for record in records:
            ts_code = self._to_str(record.get("ts_code"))
            if not ts_code:
                continue
            stocks_seen.add(ts_code)

            for code_key in ("l1_code", "l2_code", "l3_code"):
                sector_code = self._to_str(record.get(code_key))
                if not sector_code:
                    continue
                self.session.add(
                    SectorStock(
                        sector_code=sector_code,
                        stock_code=ts_code,
                    )
                )
                links += 1

        result["stocks"] = len(stocks_seen)
        result["links"] = links

        await self.session.commit()

        logger.info(
            f"[SW] 申万行业成分股同步完成: "
            f"成分股 {result['stocks']} 只, 关联 {result['links']} 条"
        )
        await self._update_progress(
            3, 3,
            f"申万行业成分股同步完成: {result['stocks']} 只股票, "
            f"{result['links']} 条关联",
        )

        return result

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_str(val):
        """安全转 str，None/NaN 保留为 None（不转成 'None'）"""
        if val is None:
            return None
        s = str(val).strip()
        return s if s and s.lower() != "nan" else None
