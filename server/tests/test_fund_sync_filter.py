"""
基金同步退市过滤单元测试

覆盖 ``FundDataInitService.sync_fund_basic`` 的退市基金过滤逻辑：
- ``delist_date`` 非空 → 跳过 + 计入 ``skipped``
- ``status == "E"`` → 跳过 + 计入 ``skipped``
- 已存在表中的退市基金被 ``_cleanup_delisted_funds`` 清理
"""

import pytest
import pytest_asyncio
from datetime import date
from typing import List
from unittest.mock import MagicMock, AsyncMock

from src.models.fund import Fund
from src.services.data_init_fund import FundDataInitService


def _make_fund_record(
    ts_code: str,
    name: str,
    *,
    market: str = "O",
    delist_date: str | None = None,
    status: str = "D",
) -> dict:
    """构造一条 Tushare fund_basic 原始记录"""
    return {
        "ts_code": ts_code,
        "name": name,
        "management": "Test Management",
        "custodian": "Test Custodian",
        "fund_type": "股票型",
        "invest_type": "主动",
        "benchmark": None,
        "market": market,
        "found_date": "20200101",
        "list_date": None,
        "delist_date": delist_date,
        "status": status,
    }


@pytest_asyncio.fixture
async def service(test_session):
    """构造一个 ``FundDataInitService``，使用 conftest 的 test_session"""
    return FundDataInitService(test_session)


@pytest_asyncio.fixture
async def existing_funds(test_session):
    """预先在 funds 表里写入 3 条基金，含 2 条"已退市"记录"""
    funds = [
        Fund(
            ts_code="000001.OF",
            name="存量活跃基金",
            market="O",
            status="D",
            delist_date=None,
        ),
        Fund(
            ts_code="000002.OF",
            name="存量带退市日期基金(退市)",
            market="O",
            status="D",
            delist_date=date(2024, 5, 1),
        ),
        Fund(
            ts_code="000003.OF",
            name="存量已到期基金(退市)",
            market="O",
            status="E",
            delist_date=None,
        ),
    ]
    for f in funds:
        test_session.add(f)
    await test_session.commit()
    return funds


def _patch_tushare(monkeypatch, records: List[dict]):
    """替换 DataSourceFactory 让其返回固定 records"""
    from src.services.data_acquisition import DataSourceFactory

    mock_client = MagicMock()
    mock_client.get_fund_list = MagicMock(side_effect=lambda market: list(records))
    monkeypatch.setattr(DataSourceFactory, "create", staticmethod(lambda: mock_client))
    return mock_client


class TestSyncFundBasicDelistFilter:
    """sync_fund_basic 的退市过滤测试"""

    @pytest.mark.asyncio
    async def test_skip_fund_with_delist_date(self, monkeypatch, service, test_session):
        """delist_date 非空的基金应被跳过，不写入 funds 表

        sync_fund_basic 会按 market=E 和 market=O 拉两次（合一次 sync 触发两次调用），
        两条 record 都被返回两次，所以 skipped/active 数量都 ×2。
        """
        records = [
            _make_fund_record("150001.OF", "活跃基金A", delist_date=None, status="D"),
            _make_fund_record("150002.OF", "已退市基金B", delist_date="20240601", status="D"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        # E + O 各拉一次，每次都拿到 2 条 → skipped 应为 2
        assert result["skipped"] == 2
        assert result["failed"] == 0
        # 退市基金不应入库（E/O 各 1 次，共 2 次 upsert，但 ON CONFLICT 去重）
        from sqlalchemy import select
        rows = (await test_session.execute(select(Fund))).scalars().all()
        codes = {f.ts_code for f in rows}
        assert "150001.OF" in codes
        assert "150002.OF" not in codes

    @pytest.mark.asyncio
    async def test_skip_fund_with_status_E(self, monkeypatch, service, test_session):
        """status == 'E'（已到期）的基金应被跳过"""
        records = [
            _make_fund_record("150010.OF", "活跃基金C", delist_date=None, status="D"),
            _make_fund_record("150011.OF", "已到期基金D", delist_date=None, status="E"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        assert result["skipped"] == 2  # E + O 各 1 次
        from sqlalchemy import select
        rows = (await test_session.execute(select(Fund))).scalars().all()
        codes = {f.ts_code for f in rows}
        assert "150011.OF" not in codes

    @pytest.mark.asyncio
    async def test_skip_count_aggregates_both_conditions(
        self, monkeypatch, service, test_session
    ):
        """两种退市条件同时触发时 skipped 应累加

        E + O 各拉一次：3 条退市 × 2 = skipped 6；活跃 1 条 × 2 = 活跃 2。
        """
        records = [
            _make_fund_record("150020.OF", "退市日期触发", delist_date="20231231", status="D"),
            _make_fund_record("150021.OF", "status=E触发", delist_date=None, status="E"),
            _make_fund_record("150022.OF", "两者都触发", delist_date="20231231", status="E"),
            _make_fund_record("150023.OF", "活跃基金", delist_date=None, status="D"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        assert result["skipped"] == 6
        from sqlalchemy import select
        rows = (await test_session.execute(select(Fund))).scalars().all()
        codes = {f.ts_code for f in rows}
        # E/O 各 upsert 一次，ON CONFLICT 去重，最终只剩 1 条
        assert codes == {"150023.OF"}

    @pytest.mark.asyncio
    async def test_cleanup_removes_existing_delisted_funds(
        self, monkeypatch, service, test_session, existing_funds
    ):
        """sync 完成后应自动清理已存在的退市基金（delist_date 非空 或 status='E'）"""
        # 本次同步只拉回 1 条活跃基金
        records = [
            _make_fund_record("999999.OF", "新增活跃基金", delist_date=None, status="D"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        # 同步本身未跳过任何东西（records 里没有退市的）
        assert result["skipped"] == 0
        # 但清理步骤应删除存量表中的 2 条退市基金
        assert result["cleaned"] == 2

        from sqlalchemy import select
        rows = (await test_session.execute(select(Fund))).scalars().all()
        codes = {f.ts_code for f in rows}
        # 退市的 000002 / 000003 应被清理
        assert "000002.OF" not in codes
        assert "000003.OF" not in codes
        # 活跃的 000001 应保留，新增的 999999 应入库
        assert "000001.OF" in codes
        assert "999999.OF" in codes

    @pytest.mark.asyncio
    async def test_cleanup_zero_when_no_existing_delisted(
        self, monkeypatch, service, test_session
    ):
        """没有存量退市基金时，cleaned 应为 0"""
        records = [
            _make_fund_record("150100.OF", "全部活跃", delist_date=None, status="D"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_issued_status_I_is_not_filtered(self, monkeypatch, service, test_session):
        """status='I'（发行中）不应被过滤"""
        records = [
            _make_fund_record("150200.OF", "发行中基金", delist_date=None, status="I"),
        ]
        _patch_tushare(monkeypatch, records)

        result = await service.sync_fund_basic()

        assert result["skipped"] == 0
        from sqlalchemy import select
        rows = (await test_session.execute(select(Fund))).scalars().all()
        assert any(f.ts_code == "150200.OF" for f in rows)
