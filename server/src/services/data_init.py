"""
数据初始化服务

提供系统首次数据初始化功能，包括板块、股票和历史数据获取。
"""

import asyncio
import logging
import inspect
from datetime import date, datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.stock import Stock
from src.models.sector_stock import SectorStock
from src.models.daily_market_data import DailyMarketData
from src.models.stock_daily_market_data import StockDailyMarketData
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.models import A_STOCK_EXCHANGES, StockInfo, SectorInfo, DailyQuote
from src.repositories.symbol_repository import SectorStockRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _safe_nested_tx(session: AsyncSession):
    """
    Use nested transaction when available; fallback to no-op for AsyncMock-based tests.
    """
    begin_nested = getattr(session, "begin_nested", None)
    if begin_nested is None:
        yield
        return
    try:
        tx = begin_nested()
        if inspect.isawaitable(tx):
            tx = await tx
    except Exception:
        yield
        return
    if hasattr(tx, "__aenter__") and hasattr(tx, "__aexit__"):
        async with tx:
            yield
    else:
        yield


class DataInitService:
    """
    数据初始化服务

    负责从数据源获取初始数据并填充数据库。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化数据初始化服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.data_source = DataSourceFactory.create()
        self._progress_callback: Optional[callable] = None
        self._cancelled = False

    def set_progress_callback(self, callback: callable):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，签名为 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    async def _update_progress(self, current: int, total: int, message: str):
        """
        更新进度

        Args:
            current: 当前进度
            total: 总数
            message: 进度消息
        """
        if self._progress_callback:
            try:
                # 直接 await 回调，不使用 create_task
                if asyncio.iscoroutinefunction(self._progress_callback):
                    await self._progress_callback(current, total, message)
                else:
                    self._progress_callback(current, total, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    def cancel(self):
        """取消当前初始化任务"""
        self._cancelled = True
        logger.warning("数据初始化任务已请求取消")

    def _check_cancelled(self):
        """检查是否已取消"""
        if self._cancelled:
            raise InterruptedError("数据初始化任务已被取消")

    async def _cleanup_sector_cascade(self, sector_id: int) -> None:
        """
        级联删除一个 sector 的所有衍生数据。

        删除顺序按依赖从子到父：
          1. strength_scores (entity_type='sector')
          2. moving_average_data (entity_type='sector')
          3. daily_market_data (entity_type='sector')
          4. sectors 本身
        sector_stocks 关联在调用方按 sector_code 批量清理。
        """
        from src.models.strength_score import StrengthScore
        from src.models.moving_average_data import MovingAverageData

        # 通用多态 entity 表
        for model in (StrengthScore, MovingAverageData, DailyMarketData):
            await self.session.execute(
                delete(model).where(
                    and_(
                        model.entity_type == "sector",
                        model.entity_id == sector_id,
                    )
                )
            )
        await self.session.execute(
            delete(Sector).where(Sector.id == sector_id)
        )
        await self.session.flush()

    async def _invalidate_sector_caches(self) -> None:
        """删除/更新板块后清理 sectors 和 strength 相关缓存"""
        try:
            from src.services.cache.cache_manager import get_cache_manager
            cache = get_cache_manager()
            await cache.clear_pattern("sectors:%")
            await cache.clear_pattern("strength:sector:%")
            await cache.clear_pattern("strength:list:sector:%")
            await cache.clear_pattern("heatmap:sectors:%")
        except Exception as e:
            # 缓存清理失败不应该阻塞同步流程
            logger.warning(f"清理板块缓存失败（忽略）: {e}")

    async def init_sectors(self, sector_type: Optional[str] = None) -> dict:
        """
        同步板块数据（幂等模式）

        此方法会：
        1. 从数据源获取板块列表，与数据库中已有板块做集合差集
           - 新增：直接创建
           - 已有：逐字段 diff，更新 name/type/description
           - 数据源已消失：级联删除（包含分类/强度/行情/均线/关联表）
        2. 对每个保留的板块，按 set diff 同步 sector_stocks 关联
           - 数据源新增的成分股 → INSERT
           - 数据源已移除的成分股 → DELETE

        Args:
            sector_type: 板块类型过滤 (industry/concept/region)，None 表示获取所有

        Returns:
            初始化结果字典: {
                "success": bool, "created": int, "updated": int,
                "deleted": int, "skipped": int, "errors": list, "total": int,
                "members_total": int, "members_added": int,
                "members_removed": int, "member_errors": list,
            }
        """
        self._cancelled = False
        logger.info(f"开始同步板块数据 (类型: {sector_type or '全部'})")

        try:
            # ============ Phase 1: 板块实体集合差集同步 ============
            sectors = self.data_source.get_sector_list(sector_type)
            self._check_cancelled()

            source_map: dict[str, SectorInfo] = {s.code: s for s in sectors}
            source_codes = set(source_map.keys())

            # 加载数据库中匹配过滤条件的板块（按 type 对齐快照）
            stmt = select(Sector)
            if sector_type:
                stmt = stmt.where(Sector.type == sector_type)
            db_sectors = list((await self.session.execute(stmt)).scalars().all())
            db_map: dict[str, Sector] = {s.code: s for s in db_sectors}
            db_codes = set(db_map.keys())

            to_insert = source_codes - db_codes
            to_update = source_codes & db_codes
            to_delete = db_codes - source_codes

            created = 0
            updated = 0
            deleted = 0
            skipped = 0
            errors: list[str] = []
            basic_fields = ["name", "type", "description"]

            total_steps = len(sectors) + len(to_delete)
            step = 0

            # --- 1.1 新增 ---
            for code in to_insert:
                self._check_cancelled()
                step += 1
                info = source_map[code]
                await self._update_progress(
                    step, total_steps, f"新增板块: {info.name} ({info.code})"
                )
                try:
                    async with _safe_nested_tx(self.session):
                        self.session.add(Sector(
                            code=info.code,
                            name=info.name,
                            type=info.type,
                            # 与旧实现保持一致：SectorInfo.description 默认 None 时用 type 生成占位
                            description=info.description
                            or f"{info.type} sector from data source",
                        ))
                        created += 1
                        logger.debug(f"新增板块: {info.code} - {info.name}")
                except Exception as e:
                    error_msg = f"新增板块失败 {info.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # --- 1.2 更新（逐字段 diff）---
            for code in to_update:
                self._check_cancelled()
                step += 1
                info = source_map[code]
                existing = db_map[code]
                await self._update_progress(
                    step, total_steps, f"校验板块: {info.name} ({info.code})"
                )
                try:
                    async with _safe_nested_tx(self.session):
                        changed: list[str] = []
                        for field in basic_fields:
                            # description 字段特殊处理：None 时按 type 生成默认值
                            # 这样旧库中的硬编码占位不会被 None 覆盖
                            if field == "description":
                                new_val = (
                                    info.description
                                    or f"{info.type} sector from data source"
                                )
                                old_val = getattr(existing, field, None)
                                if new_val != old_val:
                                    setattr(existing, field, new_val)
                                    changed.append(field)
                                continue
                            new_val = getattr(info, field, None)
                            old_val = getattr(existing, field, None)
                            if new_val != old_val:
                                setattr(existing, field, new_val)
                                changed.append(field)
                        if changed:
                            updated += 1
                            logger.debug(
                                f"更新板块: {info.code} - "
                                f"变更字段: {', '.join(changed)}"
                            )
                        else:
                            skipped += 1
                except Exception as e:
                    error_msg = f"更新板块失败 {info.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # --- 1.3 删除（级联清理）---
            for code in to_delete:
                self._check_cancelled()
                step += 1
                sector = db_map[code]
                await self._update_progress(
                    step, total_steps, f"下线板块: {sector.name} ({sector.code})"
                )
                try:
                    async with _safe_nested_tx(self.session):
                        await self._cleanup_sector_cascade(sector.id)
                        deleted += 1
                        logger.info(
                            f"下线板块: {sector.code} - {sector.name} "
                            f"(级联清理已执行)"
                        )
                except Exception as e:
                    error_msg = f"级联删除板块失败 {sector.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # --- 1.4 清理 sector_stocks 中已下线板块的关联 ---
            if to_delete:
                try:
                    async with _safe_nested_tx(self.session):
                        repo = SectorStockRepository(self.session)
                        removed_relations = await repo.delete_relations_for_sectors(
                            list(to_delete)
                        )
                        logger.info(
                            f"清理 {len(to_delete)} 个下线板块的 "
                            f"{removed_relations} 条成分股关联"
                        )
                except Exception as e:
                    error_msg = f"清理下线板块的成分股关联失败: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            await self.session.commit()
            logger.info(
                f"板块实体同步完成: 新增 {created}, 更新 {updated}, "
                f"跳过 {skipped}, 下线 {deleted}, 错误 {len(errors)}"
            )

            # ============ Phase 2: 成分股 set diff 同步 ============
            member_result = await self._init_sector_members(sector_type)

            # ============ 缓存失效 ============
            if created or updated or deleted or member_result.get(
                "members_added"
            ) or member_result.get("members_removed"):
                await self._invalidate_sector_caches()

            result = {
                "success": True,
                "created": created,
                "updated": updated,
                "deleted": deleted,
                "skipped": skipped,
                "errors": errors,
                "total": len(sectors),
                "members_total": member_result.get("members_total", 0),
                "members_added": member_result.get("members_added", 0),
                "members_removed": member_result.get("members_removed", 0),
                "member_errors": member_result.get("member_errors", []),
            }

            logger.info(
                f"板块同步完成: 新增 {created}, 更新 {updated}, "
                f"下线 {deleted}, 跳过 {skipped}, "
                f"成分股 {member_result.get('members_total', 0)} 只, "
                f"新增关联 {member_result.get('members_added', 0)} 条, "
                f"移除关联 {member_result.get('members_removed', 0)} 条, "
                f"错误 {len(errors)}"
            )
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("板块同步已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"板块同步失败: {e}")
            return {"success": False, "error": str(e)}

    async def _init_sector_members(self, sector_type: Optional[str] = None) -> dict:
        """
        同步板块成分股（set diff 模式）

        遍历数据库中已存在的板块（含本次同步后新插入的），
        与数据源返回的成分股做 set diff：
          - 数据源新增的成分股 → INSERT（ON CONFLICT DO NOTHING）
          - 数据源已移除的成分股 → DELETE

        Args:
            sector_type: 板块类型过滤，None 表示全部

        Returns:
            {"members_total": int, "members_added": int,
             "members_removed": int, "member_errors": list}
        """
        # 查询数据库中的板块（同步后的最新状态）
        stmt = select(Sector)
        if sector_type:
            stmt = stmt.where(Sector.type == sector_type)
        result = await self.session.execute(stmt)
        db_sectors = list(result.scalars().all())

        if not db_sectors:
            logger.info("数据库中无板块记录，跳过成分股同步")
            return {
                "members_total": 0,
                "members_added": 0,
                "members_removed": 0,
                "member_errors": [],
            }

        logger.info(f"开始同步 {len(db_sectors)} 个板块的成分股")
        repo = SectorStockRepository(self.session)

        members_total = 0
        members_added = 0
        members_removed = 0
        member_errors: list[str] = []

        for i, sector in enumerate(db_sectors, 1):
            self._check_cancelled()
            await self._update_progress(
                i, len(db_sectors),
                f"同步成分股: {sector.name} ({sector.type})"
            )

            try:
                # 从数据源获取当前成分股
                member_info = self.data_source.get_sector_members(sector.code)
                source_codes = set(member_info.stock_codes)

                # 查询数据库中已有成分股
                db_stock_codes = set(
                    await repo.get_stock_codes_by_sector(sector.code)
                )

                # set diff: 已下线的成员 → DELETE
                stale = db_stock_codes - source_codes
                if stale:
                    async with _safe_nested_tx(self.session):
                        await repo.delete_relations_except(
                            sector.code, source_codes
                        )
                    members_removed += len(stale)

                # set diff: 新增的成员 → INSERT
                new = source_codes - db_stock_codes
                if new:
                    async with _safe_nested_tx(self.session):
                        relations = [(sector.code, code) for code in new]
                        added = await repo.bulk_upsert_relations(relations)
                    members_added += added

                members_total += len(source_codes)
                logger.debug(
                    f"板块 {sector.code} ({sector.name}): "
                    f"数据源 {len(source_codes)} 只, "
                    f"新增 {len(new)} 只, 移除 {len(stale)} 只"
                )

            except Exception as e:
                error_msg = f"同步成分股失败 {sector.code} ({sector.name}): {e}"
                member_errors.append(error_msg)
                logger.error(error_msg)

        # 提交成分股关联变更
        await self.session.commit()

        logger.info(
            f"成分股同步完成: 共 {members_total} 只, "
            f"新增 {members_added} 条关联, "
            f"移除 {members_removed} 条关联, "
            f"错误 {len(member_errors)}"
        )
        return {
            "members_total": members_total,
            "members_added": members_added,
            "members_removed": members_removed,
            "member_errors": member_errors,
        }

    async def init_stocks(self) -> dict:
        """
        初始化股票数据（A 股 + 港股）

        Returns:
            初始化结果字典
        """
        self._cancelled = False
        logger.info("开始初始化股票数据（A 股 + 港股）")

        try:
            # 从数据源获取 A 股列表
            stocks = self.data_source.get_stock_list()
            self._check_cancelled()

            # 拉取港股列表（失败不阻断 A 股初始化）
            hk_stocks: list = []
            hk_total = 0
            hk_fetch_ok = True
            try:
                await self._update_progress(0, 0, "正在拉取港股基础信息...")
                hk_stocks = self.data_source.get_hk_stock_list()
                hk_total = len(hk_stocks)
                self._check_cancelled()
            except InterruptedError:
                raise
            except Exception as e:
                logger.error(f"拉取港股列表失败（不影响 A 股初始化）: {e}")
                hk_stocks = []
                hk_total = 0
                hk_fetch_ok = False

            all_stocks = stocks + hk_stocks

            created = 0
            updated = 0
            skipped = 0
            hk_created = 0
            errors = []

            # 需要同步的基础字段列表
            _basic_fields = [
                "name", "ts_code", "area", "industry", "fullname", "enname",
                "cnspell", "market", "exchange", "curr_type", "list_status",
                "list_date", "delist_date", "is_hs", "act_name", "act_ent_type",
            ]

            for i, stock_info in enumerate(all_stocks, 1):
                self._check_cancelled()
                is_hk = stock_info.exchange == "HKEX"
                await self._update_progress(i, len(all_stocks), f"正在处理股票: {stock_info.symbol} - {stock_info.name}")

                try:
                    # 使用 savepoint 隔离每个股票的操作
                    async with _safe_nested_tx(self.session):
                        # 检查股票是否已存在
                        result = await self.session.execute(
                            select(Stock).where(Stock.symbol == stock_info.symbol)
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            # 已存在则更新基础字段
                            updated_fields = []
                            for field in _basic_fields:
                                new_val = getattr(stock_info, field, None)
                                old_val = getattr(existing, field, None)
                                if new_val != old_val:
                                    setattr(existing, field, new_val)
                                    updated_fields.append(field)
                            if updated_fields:
                                updated += 1
                                logger.debug(
                                    f"更新股票: {stock_info.symbol} - "
                                    f"变更字段: {', '.join(updated_fields)}"
                                )
                            else:
                                skipped += 1
                        else:
                            # 创建新股票，保存全部基础字段
                            stock = Stock(
                                symbol=stock_info.symbol,
                                name=stock_info.name,
                                ts_code=stock_info.ts_code,
                                area=stock_info.area,
                                industry=stock_info.industry,
                                fullname=stock_info.fullname,
                                enname=stock_info.enname,
                                cnspell=stock_info.cnspell,
                                market=stock_info.market,
                                exchange=stock_info.exchange,
                                curr_type=stock_info.curr_type,
                                list_status=stock_info.list_status,
                                list_date=stock_info.list_date,
                                delist_date=stock_info.delist_date,
                                is_hs=stock_info.is_hs,
                                act_name=stock_info.act_name,
                                act_ent_type=stock_info.act_ent_type,
                                current_price=None,
                                market_cap=None,
                            )
                            self.session.add(stock)
                            created += 1
                            if is_hk:
                                hk_created += 1
                            logger.debug(f"创建股票: {stock_info.symbol} - {stock_info.name}")

                except Exception as e:
                    error_msg = f"处理股票失败 {stock_info.symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # ============ set-diff 清理：删除数据源已消失的股票 ============
            # 港股拉取失败（hk_fetch_ok=False）时不删港股，避免误删全部港股
            cleanup = await self._cleanup_disappeared_stocks(
                a_source_symbols={s.symbol for s in stocks},
                hk_source_symbols={s.symbol for s in hk_stocks} if hk_fetch_ok else None,
            )

            # 提交事务
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "errors": errors,
                "total": len(all_stocks),
                "hk_total": hk_total,
                "hk_created": hk_created,
                "deleted": cleanup["deleted_symbols"],
                "deleted_count": len(cleanup["deleted_symbols"]),
                "cleanup_errors": cleanup["cleanup_errors"],
            }

            logger.info(
                f"股票初始化完成: 创建 {created}(其中港股 {hk_created}), "
                f"更新 {updated}, 跳过 {skipped}, "
                f"删除 {len(cleanup['deleted_symbols'])}, 错误 {len(errors)}"
            )
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("股票初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"股票初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def _cleanup_disappeared_stocks(
        self,
        a_source_symbols: set,
        hk_source_symbols: Optional[set],
    ) -> dict:
        """
        清理数据源已消失的股票（set-diff），级联删衍生数据，带误删防护。

        Args:
            a_source_symbols: 数据源 A 股 symbol 集合
            hk_source_symbols: 数据源港股 symbol 集合；None 表示港股拉取失败，跳过港股清理

        Returns:
            {"deleted_symbols": list, "cleanup_errors": list}
        """
        deleted_symbols: list = []
        cleanup_errors: list = []

        a_deleted, a_err = await self._cleanup_one_market(
            exchanges=A_STOCK_EXCHANGES,
            source_symbols=a_source_symbols,
            label="A 股",
        )
        deleted_symbols.extend(a_deleted)
        cleanup_errors.extend(a_err)

        if hk_source_symbols is not None:
            hk_deleted, hk_err = await self._cleanup_one_market(
                exchanges=("HKEX",),
                source_symbols=hk_source_symbols,
                label="港股",
            )
            deleted_symbols.extend(hk_deleted)
            cleanup_errors.extend(hk_err)

        return {"deleted_symbols": deleted_symbols, "cleanup_errors": cleanup_errors}

    async def _cleanup_one_market(
        self,
        exchanges: tuple,
        source_symbols: set,
        label: str,
    ) -> tuple:
        """对单一市场做 set-diff 清理，带 sanity check 防误删。

        若待删数量超过该市场库存的 5%（且库存 > 100），视为数据源返回不完整，
        拒绝删除以防止误删。
        """
        self._check_cancelled()
        rows = (await self.session.execute(
            select(Stock.id, Stock.symbol).where(Stock.exchange.in_(exchanges))
        )).all()
        db_map = {r.symbol: r.id for r in rows}

        to_delete = set(db_map) - set(source_symbols)
        if not to_delete:
            return [], []

        if len(db_map) > 100 and len(to_delete) > len(db_map) * 0.05:
            err = (
                f"{label}清理中止：待删除 {len(to_delete)}/{len(db_map)} "
                f"超过 5% 阈值，疑似数据源返回不完整，已跳过删除"
            )
            logger.error(err)
            return [], [err]

        deleted_ids = [db_map[s] for s in to_delete]
        deleted_symbols = sorted(to_delete)

        await self._cascade_delete_stock_data(deleted_ids, deleted_symbols)
        logger.info(
            f"{label}清理：删除 {len(deleted_symbols)} 只数据源已消失的股票: "
            f"{deleted_symbols}"
        )
        return deleted_symbols, []

    async def _cascade_delete_stock_data(
        self,
        stock_ids: list,
        symbols: list,
    ) -> None:
        """
        级联删除股票的衍生数据。

        stocks 表无外键约束（衍生表均为软关联），需手动清理避免孤儿：
          - stock_daily_market_data / stock_moving_average_data / stock_strength_scores：按 stock_id（股票独立表）
          - sector_stocks：按 stock_code（symbol）
          - top10_float_holders：按 symbol
          - stocks 本身

        注意：旧表（daily_market_data 等）仅承接板块数据，此处不再清理；
        遗留的旧股票数据保留但不读取（ADR-2）。
        """
        from src.models.stock_moving_average_data import StockMovingAverageData
        from src.models.stock_strength_scores import StockStrengthScore
        from src.models.top10_float_holder import Top10FloatHolder

        # 股票独立三表：按 stock_id 删除（无 entity_type）
        for model in (StockDailyMarketData, StockMovingAverageData, StockStrengthScore):
            await self.session.execute(
                delete(model).where(model.stock_id.in_(stock_ids))
            )
        await self.session.execute(
            delete(SectorStock).where(SectorStock.stock_code.in_(symbols))
        )
        await self.session.execute(
            delete(Top10FloatHolder).where(Top10FloatHolder.symbol.in_(symbols))
        )
        await self.session.execute(
            delete(Stock).where(Stock.id.in_(stock_ids))
        )

    async def init_historical_data(
        self,
        days: int = 60,
        symbol_filter: Optional[list[str]] = None
    ) -> dict:
        """
        初始化历史行情数据

        Args:
            days: 回溯天数（1-365）
            symbol_filter: 股票代码过滤列表，None 表示全部

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 验证参数
        days = max(1, min(365, days))
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"开始初始化历史数据: {start_date} 至 {end_date} ({days} 天)")

        try:
            # 获取需要处理的股票列表
            if symbol_filter:
                # 使用过滤列表
                symbols = symbol_filter
            else:
                # 获取所有股票（仅 A 股，排除港股）
                result = await self.session.execute(
                    select(Stock.symbol).where(
                        Stock.exchange.in_(A_STOCK_EXCHANGES)
                    )
                )
                symbols = [row[0] for row in result.all()]

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []

            for i, symbol in enumerate(symbols, 1):
                self._check_cancelled()
                await self._update_progress(i, len(symbols), f"正在获取历史数据: {symbol}")

                try:
                    # 使用 savepoint 隔离每个股票的操作
                    async with _safe_nested_tx(self.session):
                        # 获取股票ID
                        result = await self.session.execute(
                            select(Stock).where(Stock.symbol == symbol)
                        )
                        stock = result.scalar_one_or_none()

                        if not stock:
                            logger.warning(f"股票不存在，跳过: {symbol}")
                            skipped += 1
                            continue

                        # 从数据源获取历史数据
                        quotes = self.data_source.get_daily_data(symbol, start_date, end_date)

                        for quote in quotes:
                            # 检查数据是否已存在（写入股票独立表 stock_daily_market_data）
                            result = await self.session.execute(
                                select(StockDailyMarketData).where(
                                    StockDailyMarketData.stock_id == stock.id,
                                    StockDailyMarketData.date == quote.trade_date
                                )
                            )
                            existing = result.scalar_one_or_none()

                            if existing:
                                continue

                            # 创建新记录（写入股票独立表，无 entity_type）
                            market_data = StockDailyMarketData(
                                stock_id=stock.id,
                                symbol=stock.symbol,
                                date=quote.trade_date,
                                open=quote.open,
                                high=quote.high,
                                low=quote.low,
                                close=quote.close,
                                volume=quote.volume,
                                turnover=quote.turnover,
                                change=None,
                                change_percent=None
                            )
                            self.session.add(market_data)
                            created += 1

                except Exception as e:
                    error_msg = f"获取历史数据失败 {symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 最终提交
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_symbols": len(symbols)
            }

            logger.info(f"历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_historical_data_by_date_range(
        self,
        start_date: date,
        end_date: date,
        symbol_filter: Optional[list[str]] = None
    ) -> dict:
        """
        根据日期范围初始化历史行情数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol_filter: 股票代码过滤列表，None 表示全部

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 验证日期范围
        if start_date > end_date:
            return {"success": False, "error": "开始日期不能晚于结束日期"}

        # 计算年份差
        years_diff = (end_date.year - start_date.year)
        if end_date.month < start_date.month or (end_date.month == start_date.month and end_date.day < start_date.day):
            years_diff -= 1

        if years_diff > 10:
            return {"success": False, "error": "日期范围不能超过 10 年"}

        days = (end_date - start_date).days + 1
        logger.info(f"开始初始化历史数据: {start_date} 至 {end_date} ({days} 天，约 {years_diff + 1} 年)")

        try:
            # 获取需要处理的股票列表
            if symbol_filter:
                # 使用过滤列表
                symbols = symbol_filter
            else:
                # 获取所有股票（仅 A 股，排除港股）
                result = await self.session.execute(
                    select(Stock.symbol).where(
                        Stock.exchange.in_(A_STOCK_EXCHANGES)
                    )
                )
                symbols = [row[0] for row in result.all()]

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []
            processed_symbols = []  # 记录已处理的股票

            for i, symbol in enumerate(symbols, 1):
                self._check_cancelled()
                await self._update_progress(i, len(symbols), f"正在获取历史数据: {symbol} ({start_date} - {end_date})")

                try:
                    # 获取股票ID
                    result = await self.session.execute(
                        select(Stock).where(Stock.symbol == symbol)
                    )
                    stock = result.scalar_one_or_none()

                    if not stock:
                        logger.warning(f"股票不存在，跳过: {symbol}")
                        skipped += 1
                        continue

                    # 检查这只股票是否已有数据（断点续传支持，查股票独立表）
                    result = await self.session.execute(
                        select(StockDailyMarketData).where(
                            StockDailyMarketData.stock_id == stock.id,
                            StockDailyMarketData.date.between(start_date, end_date)
                        ).limit(1)
                    )
                    has_existing_data = result.scalar_one_or_none() is not None

                    if has_existing_data:
                        logger.info(f"股票 {symbol} 在日期范围内已有数据，跳过")
                        skipped += 1
                        processed_symbols.append(symbol)
                        continue

                    # 从数据源获取历史数据
                    quotes = self.data_source.get_daily_data(symbol, start_date, end_date)

                    symbol_created = 0
                    for quote in quotes:
                        # 检查数据是否已存在（查股票独立表）
                        result = await self.session.execute(
                            select(StockDailyMarketData).where(
                                StockDailyMarketData.stock_id == stock.id,
                                StockDailyMarketData.date == quote.trade_date
                            )
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            continue

                        # 创建新记录（写入股票独立表，无 entity_type）
                        market_data = StockDailyMarketData(
                            stock_id=stock.id,
                            symbol=stock.symbol,
                            date=quote.trade_date,
                            open=quote.open,
                            high=quote.high,
                            low=quote.low,
                            close=quote.close,
                            volume=quote.volume,
                            turnover=quote.turnover,
                            change=None,
                            change_percent=None
                        )
                        self.session.add(market_data)
                        created += 1
                        symbol_created += 1

                    # 每只股票处理完后立即提交
                    await self.session.commit()
                    processed_symbols.append(symbol)
                    logger.debug(f"股票 {symbol} 数据已保存: {symbol_created} 条记录")

                except Exception as e:
                    error_msg = f"获取历史数据失败 {symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    # 发生错误时回滚当前股票的更改
                    await self.session.rollback()
            # 不需要最终提交，因为每只股票都已提交

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_symbols": len(symbols),
                "processed_symbols": len(processed_symbols),
                "date_range": f"{start_date} to {end_date}"
            }

            logger.info(f"历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 已处理 {len(processed_symbols)}/{len(symbols)} 只股票, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_sector_historical_data(
        self,
        days: Optional[int] = None,
        sector_filter: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        初始化板块历史行情数据

        使用数据源接口直接获取板块历史数据。

        Args:
            days: 回溯天数（1-365），如果提供 start_date/end_date 则忽略此参数
            sector_filter: 板块代码过滤列表，None 表示全部
            start_date: 开始日期，如果提供则优先使用
            end_date: 结束日期，如果提供则优先使用

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 确定日期范围
        if start_date and end_date:
            # 使用传入的日期范围
            pass
        elif days is not None:
            # 使用天数计算
            days = max(1, min(365, days))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        else:
            # 默认 60 天
            end_date = date.today()
            start_date = end_date - timedelta(days=60)

        logger.info(f"开始初始化板块历史数据: {start_date} 至 {end_date}")

        try:
            # 获取需要处理的板块列表
            if sector_filter:
                # 使用过滤列表
                result = await self.session.execute(
                    select(Sector).where(Sector.code.in_(sector_filter))
                )
                sectors = result.scalars().all()
            else:
                # 获取所有板块
                result = await self.session.execute(select(Sector))
                sectors = result.scalars().all()

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []

            for i, sector in enumerate(sectors, 1):
                self._check_cancelled()
                await self._update_progress(i, len(sectors), f"正在获取板块历史数据: {sector.name}")

                try:
                    # 使用 savepoint 隔离每个板块的操作
                    async with _safe_nested_tx(self.session):
                        # 从数据源直接获取板块历史数据
                        quotes = self.data_source.get_sector_daily_data(
                            sector.name,
                            sector.type,
                            start_date,
                            end_date,
                        )

                        if not quotes:
                            logger.warning(f"板块 {sector.code} 没有获取到历史数据，跳过")
                            skipped += 1
                            continue

                        sector_created = 0
                        for quote in quotes:
                            # 检查数据是否已存在
                            result = await self.session.execute(
                                select(DailyMarketData).where(
                                    DailyMarketData.entity_type == "sector",
                                    DailyMarketData.entity_id == sector.id,
                                    DailyMarketData.date == quote.trade_date
                                )
                            )
                            existing = result.scalar_one_or_none()

                            if existing:
                                continue

                            # 创建新记录
                            market_data = DailyMarketData(
                                entity_type="sector",
                                entity_id=sector.id,
                                symbol=sector.code,
                                date=quote.trade_date,
                                open=quote.open,
                                high=quote.high,
                                low=quote.low,
                                close=quote.close,
                                volume=quote.volume,
                                turnover=quote.turnover,
                                change=None,
                                change_percent=None
                            )
                            self.session.add(market_data)
                            created += 1
                            sector_created += 1

                        logger.debug(f"板块 {sector.code} 数据已保存: {sector_created} 条记录")

                except Exception as e:
                    error_msg = f"获取板块历史数据失败 {sector.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 最终提交
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_sectors": len(sectors)
            }

            logger.info(f"板块历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("板块历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"板块历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}
