"""市场量价查询 API 路由（第 16 期 plan-06）

端点：
- GET  /api/v1/market-metrics/trend  — 全市场量价趋势（AC-05 30/90/250 裁剪、AC-06 缺口 null）

复用声明：
- 路由 + helper 范式：src/api/v1/index_monitor.py（_serialize_value / _dict_to_camel /
  {success,data} 包裹 / Depends(get_current_user)）
- 2 个模型：src/models/trading_calendar_day.py（TradingCalendarDay）、
  src/models/market_daily_metric.py（MarketDailyMetric）

契约（架构 §6.4.2、§7.2、§7.3 + plan-06 §3）：
- 路径：router prefix /market-metrics + v1 主路由 prefix /v1 = /api/v1/market-metrics/*
- query 参数名 ``range``（单词无 snake/camel 歧义），仅允许 30/90/250，非法值 422
- 响应：``{ success: bool, data: {...} }`` 包裹，data 内字段经 _dict_to_camel 转 camelCase，
  Decimal → float（不得输出字符串，§7.3）、date → ISO 字符串
- 输出契约 = 架构 §7.2 ``MarketMetricsTrendData``：
  ``{ latest: MarketMetricPoint | null, points: MarketMetricPoint[], range, hasMissingDates }``

GET 读路径硬约束（架构 §4.2 模块 4、ADR-6、§8.6）：
- 零 Provider 调用：禁止实例化 TradingCalendar（缓存未命中会实时访问 Provider）、
  禁止调用 DataSourceFactory / Tushare —— 本文件不 import 任何 Provider 侧模块
- 缺失日输出 null（不补 0 / 前值）；latest 取最近"有结果"日（不伪装今天）
"""

import logging
import time
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_session
from src.models import MarketDailyMetric, TradingCalendarDay
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-metrics", tags=["MarketMetrics"])


# ============== Helper（复制自 index_monitor.py，与 etf_monitor 同源惯例）==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型（与 index_monitor.py 一致）"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _dict_to_camel(d: dict) -> dict:
    """将字典的 snake_case 键转为 camelCase（递归处理嵌套 dict / list）"""
    result = {}
    for k, v in d.items():
        camel_key = to_camel(k)
        if isinstance(v, dict):
            result[camel_key] = _dict_to_camel(v)
        elif isinstance(v, list):
            result[camel_key] = [
                _dict_to_camel(item) if isinstance(item, dict) else _serialize_value(item)
                for item in v
            ]
        else:
            result[camel_key] = _serialize_value(v)
    return result


def _to_point(cal: date, metric: MarketDailyMetric | None) -> dict:
    """构造单个交易日点（snake_case，后续统一经 _dict_to_camel 转 camelCase）。

    缺失日（无 market_daily_metrics 行）五项指标全 null —— 不补 0 / 前值（AC-06）。
    """
    if metric is None:
        return {
            "trade_date": cal,
            "volume_shares": None,
            "amount_yuan": None,
            "average_price": None,
            "final_stock_count": None,
            "suspended_stock_count": None,
        }
    return {
        "trade_date": cal,
        "volume_shares": metric.volume_shares,
        "amount_yuan": metric.amount_yuan,
        "average_price": metric.average_price,
        "final_stock_count": metric.final_stock_count,
        "suspended_stock_count": metric.suspended_stock_count,
    }


# ============== Endpoints ==============


@router.get("/trend")
async def get_trend(
    # 仅允许 30/90/250，非法值由 Query pattern 校验拒绝（422）。
    # 注：query 原文到达时是字符串，Pydantic 2.12 禁止对 int schema 应用 pattern、
    # 也不支持 Literal[int] 的隐式 str→int 强转（两者均 422/500），因此声明为
    # pattern 约束的 str 后在端点内转 int —— 线上契约不变：?range=30 整数串、
    # 默认 30、非法值 422（plan-06 §3 意图不变）。
    range: str = Query("30", description="趋势交易日数（30/90/250）", pattern="^(30|90|250)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    全市场量价趋势（AC-05 / AC-06）。

    流程（架构 §6.4.2、ADR-6）：
    1. 本地 trading_calendar_days 取最近 N 个开市日（DESC LIMIT N 后反转为升序，
       ≤250 点，走 idx_trading_calendar_days_cal_date_is_open）；
    2. 日历无任何开市日 → success=False + "未初始化" message（不得用自然日/工作日伪造）；
    3. 开市日轴 LEFT JOIN market_daily_metrics（参数化 IN，升序）；
    4. points 逐日构造，缺结果日五项指标全 null（不补 0/前值）；
    5. latest = points 自尾向头第一个有值点（展示最近成功结果日，不伪装今天）；
    6. hasMissingDates = 任一点 volume_shares 为 null。

    返回 { success, data: { latest, points, range, hasMissingDates } }（camelCase）。
    GET 路径零 Provider 调用（不 import TradingCalendar / DataSourceFactory / Tushare）。
    """
    # ``range`` 为 Python 内建名，端点内转 int 并改用 range_days，避免遮蔽（plan-06 风险备注）
    range_days = int(range)

    try:
        db_start = time.perf_counter()

        # 1. 最近 N 个开市日（DESC LIMIT N，走 cal_date+is_open 索引）
        cal_res = await session.execute(
            select(TradingCalendarDay.cal_date)
            .where(TradingCalendarDay.is_open.is_(True))
            .order_by(TradingCalendarDay.cal_date.desc())
            .limit(range_days)
        )
        dates = [row[0] for row in cal_res.all()]
        dates.reverse()  # 反转为升序

        # 2. 日历空表 → 明确"未初始化"，不猜测日期
        if not dates:
            logger.warning(
                "market-metrics trend: 交易日历未初始化（trading_calendar_days 无开市日），"
                "range=%d", range_days,
            )
            return {
                "success": False,
                "data": None,
                "message": "交易日历未初始化，请先执行市场量价同步",
            }

        # 3. 开市日轴 LEFT JOIN 指标（参数化 IN，升序；缺失日 m 为 None）
        metric_res = await session.execute(
            select(TradingCalendarDay.cal_date, MarketDailyMetric)
            .outerjoin(
                MarketDailyMetric,
                MarketDailyMetric.trade_date == TradingCalendarDay.cal_date,
            )
            .where(
                TradingCalendarDay.cal_date.in_(dates),
                TradingCalendarDay.is_open.is_(True),
            )
            .order_by(TradingCalendarDay.cal_date.asc())
        )
        metric_map = {cal: m for cal, m in metric_res.all() if m is not None}

        # 4. points 逐日构造（缺失日全 null，不补 0/前值）
        points = [_to_point(d, metric_map.get(d)) for d in dates]

        # 5. latest：自尾向头第一个有值点；全空 → null
        latest = None
        for p in reversed(points):
            if p["volume_shares"] is not None:
                latest = p
                break

        # 6. hasMissingDates：任一点 volume_shares 为 null
        missing_count = sum(1 for p in points if p["volume_shares"] is None)
        has_missing_dates = missing_count > 0

        # 可观测性（架构 §8.5）：range/points/missing_count/db_duration_ms；
        # 无 Provider 调用可记录（GET 路径天然零调用）
        db_duration_ms = (time.perf_counter() - db_start) * 1000
        logger.info(
            "market-metrics trend: range=%d, points=%d, missing_count=%d, "
            "db_duration_ms=%.1f",
            range_days,
            len(points),
            missing_count,
            db_duration_ms,
        )

        return {
            "success": True,
            "data": _dict_to_camel(
                {
                    "latest": latest,
                    "points": points,
                    "range": range_days,
                    "has_missing_dates": has_missing_dates,
                }
            ),
        }
    except Exception:
        logger.exception("market-metrics get_trend error, range=%s", range)
        raise
