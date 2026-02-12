"""AkShare 数据源 THS 板块接口测试。"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.services.data_acquisition.akshare_client import AkShareDataSource
from src.services.data_acquisition.exceptions import RetryExhaustedError


def _make_source() -> AkShareDataSource:
    source = AkShareDataSource()
    source._execute_with_retry = lambda func, *args, **kwargs: func(*args, **kwargs)  # type: ignore[method-assign]
    return source


def test_get_sector_list_uses_ths_endpoints_and_maps_fields():
    source = _make_source()
    ak = MagicMock()
    ak.stock_board_industry_name_ths.return_value = pd.DataFrame(
        [{"name": "半导体", "code": "881121"}]
    )
    ak.stock_board_concept_name_ths.return_value = pd.DataFrame(
        [{"名称": "AI算力", "代码": "885976"}]
    )

    with patch.object(source, "_get_akshare", return_value=ak):
        sectors = source.get_sector_list()

    assert len(sectors) == 2
    assert sectors[0].type == "industry"
    assert sectors[0].code == "881121"
    assert sectors[1].type == "concept"
    assert sectors[1].code == "885976"


def test_get_sector_daily_data_routes_industry_to_ths_industry_api():
    source = _make_source()
    ak = MagicMock()
    ak.stock_board_industry_index_ths.return_value = pd.DataFrame(
        [
            {
                "日期": "2026-01-01",
                "开盘价": 10.0,
                "最高价": 11.0,
                "最低价": 9.5,
                "收盘价": 10.5,
                "成交量": 100,
                "成交额": 2000,
            }
        ]
    )

    with patch.object(source, "_get_akshare", return_value=ak):
        quotes = source.get_sector_daily_data(
            sector_code="881121",
            sector_type="industry",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )

    assert len(quotes) == 1
    ak.stock_board_industry_index_ths.assert_called_once()
    ak.stock_board_concept_index_ths.assert_not_called()


def test_get_sector_daily_data_routes_concept_to_ths_concept_api():
    source = _make_source()
    ak = MagicMock()
    ak.stock_board_concept_index_ths.return_value = pd.DataFrame(
        [
            {
                "日期": "2026-01-02",
                "开盘": 12.0,
                "最高": 12.5,
                "最低": 11.8,
                "收盘": 12.1,
                "成交量": 220,
                "成交额": 3300,
            }
        ]
    )

    with patch.object(source, "_get_akshare", return_value=ak):
        quotes = source.get_sector_daily_data(
            sector_code="885976",
            sector_type="concept",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )

    assert len(quotes) == 1
    ak.stock_board_concept_index_ths.assert_called_once()
    ak.stock_board_industry_index_ths.assert_not_called()


def test_get_sector_daily_data_rejects_invalid_sector_type():
    source = _make_source()

    with pytest.raises(ValueError, match="无效的板块类型"):
        source.get_sector_daily_data(
            sector_code="x",
            sector_type="invalid",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )


def test_get_sector_daily_data_returns_empty_list_on_empty_dataframe():
    source = _make_source()
    ak = MagicMock()
    ak.stock_board_industry_index_ths.return_value = pd.DataFrame()

    with patch.object(source, "_get_akshare", return_value=ak):
        quotes = source.get_sector_daily_data(
            sector_code="881121",
            sector_type="industry",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )

    assert quotes == []


def test_get_sector_list_skips_nan_rows():
    source = _make_source()
    ak = MagicMock()
    ak.stock_board_industry_name_ths.return_value = pd.DataFrame(
        [{"name": float("nan"), "code": float("nan")}]
    )
    ak.stock_board_concept_name_ths.return_value = pd.DataFrame(
        [{"name": "有效概念", "code": "885001"}]
    )

    with patch.object(source, "_get_akshare", return_value=ak):
        sectors = source.get_sector_list()

    assert len(sectors) == 1
    assert sectors[0].code == "885001"


def test_get_sector_daily_data_rejects_none_sector_type():
    source = _make_source()

    with pytest.raises(ValueError, match="板块类型不能为空"):
        source.get_sector_daily_data(
            sector_code="x",
            sector_type=None,  # type: ignore[arg-type]
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )


def test_get_sector_daily_data_propagates_retry_exhausted():
    source = AkShareDataSource()
    source._execute_with_retry = MagicMock(
        side_effect=RetryExhaustedError("重试耗尽", source="AkShare", attempts=3)
    )

    with patch.object(source, "_get_akshare", return_value=MagicMock()):
        with pytest.raises(RetryExhaustedError):
            source.get_sector_daily_data(
                sector_code="881121",
                sector_type="industry",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 10),
            )
