"""申万行业成分股同步服务测试

重点验证 SwSectorDataInitService.sync_sw_members 对 stock_code 后缀的剥离：
数据源返回的 ts_code 形如 "600850.SH" / "002796.SZ" / "430047.BJ"，
写入 SectorStock 时应只保留数字代码，以对齐 stocks.symbol（项目全程用短码）。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.data_init_sw_sector import SwSectorDataInitService
from src.models.sector_stock import SectorStock


@pytest.fixture
def mock_session():
    """模拟数据库会话（纯 mock，不连真实 PG）"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


def _sector_codes_result(codes):
    """模拟 select(Sector.code) 结果，支持 [row[0] for row in result] 解包。"""
    return [(c,) for c in codes]


@pytest.mark.asyncio
class TestSwSectorMembersSync:
    """sync_sw_members 的 stock_code 后缀剥离逻辑"""

    async def test_strips_exchange_suffix_from_stock_code(self, mock_session):
        """SH / SZ / BJ 三类后缀都应被剥离为纯数字代码"""
        records = [
            {"ts_code": "600850.SH", "l1_code": "801010.SI",
             "l2_code": "801011.SI", "l3_code": "801011.SI"},
            {"ts_code": "002796.SZ", "l1_code": "801010.SI",
             "l2_code": "801012.SI", "l3_code": "801012.SI"},
            {"ts_code": "430047.BJ", "l1_code": "801010.SI",
             "l2_code": "801013.SI", "l3_code": "801013.SI"},
        ]
        mock_source = MagicMock()
        mock_source.get_sw_index_member_all.return_value = records

        sector_codes = ["801010.SI", "801011.SI", "801012.SI", "801013.SI"]
        mock_session.execute = AsyncMock(
            side_effect=[_sector_codes_result(sector_codes), MagicMock()]
        )

        with patch(
            "src.services.data_init_sw_sector.DataSourceFactory"
        ) as mock_factory:
            mock_factory.create.return_value = mock_source
            service = SwSectorDataInitService(mock_session)
            result = await service.sync_sw_members()

        assert result["stocks"] == 3
        assert result["links"] == 9  # 3 股 × 3 层级

        added = [call.args[0] for call in mock_session.add.call_args_list]
        assert len(added) == 9
        stock_codes = {s.stock_code for s in added}
        assert stock_codes == {"600850", "002796", "430047"}
        # 关键断言：写入的代码绝不含交易所后缀
        assert all("." not in c for c in stock_codes)

    async def test_handles_code_without_suffix(self, mock_session):
        """无后缀的 ts_code 应原样保留（split 的兜底分支）"""
        records = [
            {"ts_code": "300750", "l1_code": "801010.SI",
             "l2_code": None, "l3_code": None},
        ]
        mock_source = MagicMock()
        mock_source.get_sw_index_member_all.return_value = records

        mock_session.execute = AsyncMock(
            side_effect=[_sector_codes_result(["801010.SI"]), MagicMock()]
        )

        with patch(
            "src.services.data_init_sw_sector.DataSourceFactory"
        ) as mock_factory:
            mock_factory.create.return_value = mock_source
            service = SwSectorDataInitService(mock_session)
            result = await service.sync_sw_members()

        assert result["stocks"] == 1
        assert result["links"] == 1  # 仅 l1（l2/l3 为 None 被跳过）
        added = [call.args[0] for call in mock_session.add.call_args_list]
        assert added[0].stock_code == "300750"
