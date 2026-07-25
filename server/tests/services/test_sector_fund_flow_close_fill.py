"""
SectorFundFlowService._fill_close_snapshot 单元测试

验证查询层收盘点补齐逻辑（修复横轴停在前一档、采不到 15:00 的问题）：
- 历史交易日（已收盘）+ 最后一点早于 15:00 → 补一个 15:00 点，值=最后快照
- 历史交易日 + 已有 ≥15:00 的点 → 不重复补
- 当天且未到 15:00（盘中） → 不补，避免塞伪收盘点
- 当天且 ≥15:00（已收盘） → 补
- 无数据的空分组 → 跳过，不报错

不依赖真实 DB：_fill_close_snapshot 是纯函数（仅读写传入的 grouped dict）。
now 通过 monkeypatch 模块的 datetime 控制。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock

from src.services import sector_fund_flow_service as svc_mod
from src.services.sector_fund_flow_service import SectorFundFlowService

BJ = ZoneInfo("Asia/Shanghai")


def _service():
    return SectorFundFlowFlowStub(MagicMock())


class SectorFundFlowFlowStub(SectorFundFlowService):
    """绕过 __init__ 的 DB 依赖，仅测 _fill_close_snapshot。"""


def _set_now(monkeypatch, y, mo, d, h, mi):
    """冻结模块级 datetime.now(tz) 为固定北京时间。"""
    fixed = datetime(y, mo, d, h, mi, tzinfo=BJ)

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(svc_mod, "datetime", _DT)


def test_history_day_fills_close_point(monkeypatch):
    """历史交易日 + 最后一点早于 15:00 → 补 15:00 点，值=最后快照"""
    _set_now(monkeypatch, 2026, 7, 27, 16, 0)  # 次日 16:00，历史日已收盘
    service = _service()

    grouped = {
        "电网设备": [
            {"sample_time": datetime(2026, 7, 26, 14, 48), "net_inflow": 12.3},
        ]
    }
    service._fill_close_snapshot(grouped, date(2026, 7, 26))

    pts = grouped["电网设备"]
    assert len(pts) == 2
    filled = pts[-1]
    assert filled["sample_time"] == datetime(2026, 7, 26, 15, 0)
    assert filled["net_inflow"] == 12.3  # 复用最后快照
    assert filled["close_filled"] is True


def test_history_day_skip_when_already_at_or_after_close(monkeypatch):
    """已有 ≥15:00 的点 → 不重复补"""
    _set_now(monkeypatch, 2026, 7, 27, 16, 0)
    service = _service()

    grouped = {
        "电网设备": [
            {"sample_time": datetime(2026, 7, 26, 14, 48), "net_inflow": 12.3},
            {"sample_time": datetime(2026, 7, 26, 15, 0), "net_inflow": 13.0},
        ]
    }
    service._fill_close_snapshot(grouped, date(2026, 7, 26))
    assert len(grouped["电网设备"]) == 2  # 未新增


def test_intraday_today_not_filled(monkeypatch):
    """当天且 < 15:00（盘中） → 不补，避免塞伪收盘点"""
    _set_now(monkeypatch, 2026, 7, 26, 14, 50)  # 当天 14:50，盘中
    service = _service()

    grouped = {
        "电网设备": [
            {"sample_time": datetime(2026, 7, 26, 14, 48), "net_inflow": 12.3},
        ]
    }
    service._fill_close_snapshot(grouped, date(2026, 7, 26))
    assert len(grouped["电网设备"]) == 1


def test_today_after_close_filled(monkeypatch):
    """当天且 ≥15:00（已收盘） → 补 15:00 点"""
    _set_now(monkeypatch, 2026, 7, 26, 15, 1)  # 当天 15:01，刚收盘
    service = _service()

    grouped = {
        "电网设备": [
            {"sample_time": datetime(2026, 7, 26, 14, 48), "net_inflow": 12.3},
        ]
    }
    service._fill_close_snapshot(grouped, date(2026, 7, 26))
    assert len(grouped["电网设备"]) == 2
    assert grouped["电网设备"][-1]["sample_time"] == datetime(2026, 7, 26, 15, 0)


def test_empty_group_skipped(monkeypatch):
    """空分组 → 跳过，不报错"""
    _set_now(monkeypatch, 2026, 7, 27, 16, 0)
    service = _service()

    grouped = {"空板块": []}
    service._fill_close_snapshot(grouped, date(2026, 7, 26))
    assert grouped["空板块"] == []


def test_close_time_is_naive_to_match_db(monkeypatch):
    """补点 sample_time 为 naive（与 DB 存储口径一致），避免前端混合时区解析"""
    _set_now(monkeypatch, 2026, 7, 27, 16, 0)
    service = _service()

    grouped = {"电网设备": [{"sample_time": datetime(2026, 7, 26, 14, 48), "net_inflow": 1.0}]}
    service._fill_close_snapshot(grouped, date(2026, 7, 26))
    filled_time = grouped["电网设备"][-1]["sample_time"]
    assert filled_time.tzinfo is None
