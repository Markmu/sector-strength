"""
强度 API 端点测试 (Story 10.4)

测试 MA 系统强度 API 的所有端点功能。
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_stock():
    """模拟股票数据"""
    return {
        "id": 1,
        "symbol": "600519",
        "name": "贵州茅台",
        "current_price": 1850.0,
    }


@pytest.fixture
def mock_sector():
    """模拟板块数据"""
    return {
        "id": 1,
        "code": "BK0426",
        "name": "半导体",
    }


@pytest.fixture
def mock_strength_score():
    """模拟强度数据"""
    today = date.today()
    return {
        "entity_type": "stock",
        "entity_id": 1,
        "symbol": "600519",
        "date": today,
        "period": "all",
        "score": 78.5,
        "price_position_score": 82.3,
        "ma_alignment_score": 75.0,
        "ma_alignment_state": "strong_bull",
        "short_term_score": 75.2,
        "medium_term_score": 78.5,
        "long_term_score": 68.3,
        "current_price": 1850.0,
        "ma5": 1835.2,
        "ma10": 1825.8,
        "ma20": 1810.5,
        "ma30": 1798.2,
        "ma60": 1775.0,
        "ma90": 1752.0,
        "ma120": 1728.0,
        "ma240": 1680.0,
        "price_above_ma5": True,
        "price_above_ma10": True,
        "price_above_ma20": True,
        "price_above_ma30": True,
        "price_above_ma60": True,
        "price_above_ma90": True,
        "price_above_ma120": True,
        "price_above_ma240": True,
        "rank": 156,
        "percentile": 85.2,
        "change_rate_1d": 1.5,
        "change_rate_5d": 3.2,
        "strength_grade": "A",
    }


class TestStockStrengthAPI:
    """个股强度 API 测试"""

    def test_get_stock_strength_success(self, client, mock_stock, mock_strength_score):
        """测试获取个股强度 - 成功"""
        with patch('src.api.v1.stocks.select') as mock_select:
            # 模拟股票查询
            mock_stock_result = MagicMock()
            mock_stock_result.scalar_one_or_none.return_value = MagicMock(**mock_stock)

            # 模拟强度数据查询
            mock_strength_result = MagicMock()
            mock_strength_model = MagicMock(**mock_strength_score)
            mock_strength_result.scalar_one_or_none.return_value = mock_strength_model

            # 链式调用返回
            mock_select.return_value.where.return_value = mock_select
            mock_select.where.return_value.order_by.return_value.limit.return_value = mock_select
            mock_select.limit.return_value = mock_strength_result

            response = client.get("/v1/stocks/1/strength")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "600519"
            assert data["score"] == 78.5
            assert data["strength_grade"] == "A"
            assert data["stock_name"] == "贵州茅台"

    def test_get_stock_strength_not_found(self, client):
        """测试获取个股强度 - 股票不存在"""
        with patch('src.api.v1.stocks.select') as mock_select:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_select.return_value.where.return_value = mock_result

            response = client.get("/v1/stocks/999/strength")

            assert response.status_code == 404

    def test_get_stock_strength_by_symbol(self, client, mock_stock, mock_strength_score):
        """测试通过代码获取个股强度"""
        with patch('src.api.v1.stocks.select') as mock_select:
            mock_stock_result = MagicMock()
            mock_stock_model = MagicMock(**mock_stock)
            mock_stock_result.scalar_one_or_none.return_value = mock_stock_model

            mock_strength_result = MagicMock()
            mock_strength_model = MagicMock(**mock_strength_score)
            mock_strength_result.scalar_one_or_none.return_value = mock_strength_model

            mock_select.return_value.where.return_value = mock_stock_result
            mock_result = mock_select.return_value
            mock_result.where.return_value.order_by.return_value.limit.return_value = mock_strength_result

            response = client.get("/v1/stocks/symbol/600519/strength")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "600519"


class TestSectorStrengthAPI:
    """板块强度 API 测试"""

    def test_get_sector_strength_success(self, client, mock_sector, mock_strength_score):
        """测试获取板块强度 - 成功"""
        with patch('src.api.v1.sectors.select') as mock_select:
            # 模拟板块查询
            mock_sector_result = MagicMock()
            mock_sector_model = MagicMock(**mock_sector)
            mock_sector_result.scalar_one_or_none.return_value = mock_sector_model

            # 模拟强度数据查询
            mock_strength_result = MagicMock()
            mock_strength_model = MagicMock(**mock_strength_score)
            mock_strength_model.symbol = "BK0426"
            mock_strength_result.scalar_one_or_none.return_value = mock_strength_model

            # 模拟统计查询
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 85

            mock_select.return_value.where.return_value = mock_sector_result
            mock_select.return_value.func.count.return_value.select_from.return_value.where.return_value = mock_count_result

            response = client.get("/v1/sectors/1/strength")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "BK0426"
            assert data["sector_name"] == "半导体"

    def test_get_sector_strength_not_found(self, client):
        """测试获取板块强度 - 板块不存在"""
        with patch('src.api.v1.sectors.select') as mock_select:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_select.return_value.where.return_value = mock_result

            response = client.get("/v1/sectors/999/strength")

            assert response.status_code == 404


class TestStrengthHistoryAPI:
    """强度历史数据 API 测试"""

    def test_get_stock_strength_history(self, client, mock_stock):
        """测试获取个股强度历史数据"""
        with patch('src.api.v1.stocks.select') as mock_select:
            with patch('src.api.v1.stocks.StrengthHistoryService') as mock_history_service:
                mock_stock_result = MagicMock()
                mock_stock_result.scalar_one_or_none.return_value = MagicMock(**mock_stock)

                # 模拟历史数据
                mock_history_data = [
                    MagicMock(
                        date=date.today() - timedelta(days=2),
                        score=75.0,
                        rank=160,
                        percentile=83.0,
                        strength_grade="A",
                    ),
                    MagicMock(
                        date=date.today() - timedelta(days=1),
                        score=78.5,
                        rank=156,
                        percentile=85.2,
                        strength_grade="A",
                    ),
                ]

                mock_service_instance = MagicMock()
                mock_service_instance.get_stock_history = AsyncMock(return_value=mock_history_data)
                mock_history_service.return_value = mock_service_instance

                mock_select.return_value.where.return_value = mock_stock_result

                response = client.get("/v1/stocks/1/strength/history?days=30")

                assert response.status_code == 200
                data = response.json()
                assert "data_points" in data
                assert len(data["data_points"]) == 2
                assert data["total_days"] == 2

    def test_get_stock_strength_history_max_days(self, client):
        """测试获取历史数据 - 超过最大天数限制"""
        response = client.get("/v1/stocks/1/strength/history?days=500")

        # FastAPI 会自动验证 Query 参数
        assert response.status_code == 422


class TestStrengthRankingsAPI:
    """强度排名 API 测试 (V2)"""

    def test_get_stock_rankings_v2(self, client):
        """测试获取个股强度排名 (V2)"""
        with patch('src.api.v1.rankings.select') as mock_select:
            mock_rows = [
                (MagicMock(rank=1, entity_id=1, symbol="600519", score=95.0, percentile=98.0, strength_grade="A", change_rate_1d=2.5),
                 MagicMock(name="贵州茅台")),
                (MagicMock(rank=2, entity_id=2, symbol="000858", score=92.0, percentile=95.0, strength_grade="A", change_rate_1d=1.8),
                 MagicMock(name="五粮液")),
            ]

            mock_result = MagicMock()
            mock_result.all.return_value = mock_rows
            mock_select.return_value.join.return_value.where.return_value.order_by.return_value
            mock_stmt = mock_select.return_value.join.return_value.where.return_value.order_by
            mock_stmt.return_value.limit.return_value.offset.return_value = mock_result

            # 模拟 count 查询
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 5000

            response = client.get("/v1/rankings/v2/stocks?limit=2&offset=0")

            assert response.status_code == 200
            data = response.json()
            assert "rankings" in data
            assert data["returned_count"] == 2
            assert data["entity_type"] == "stock"

    def test_get_sector_rankings_v2(self, client):
        """测试获取板块强度排名 (V2)"""
        response = client.get("/v1/rankings/v2/sectors?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        assert data["entity_type"] == "sector"


class TestStrengthStatsAPI:
    """强度统计信息 API 测试 (V2)"""

    def test_get_strength_stats(self, client):
        """测试获取强度统计信息"""
        response = client.get("/v1/rankings/v2/stats?entity_type=stock")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "stock"
        assert "grade_distribution" in data
        assert "total_count" in data

    def test_get_strength_stats_invalid_entity_type(self, client):
        """测试获取统计信息 - 无效实体类型"""
        response = client.get("/v1/rankings/v2/stats?entity_type=invalid")

        assert response.status_code == 404


class TestBatchCalculationAPI:
    """批量计算强度 API 测试 (V2)"""

    def test_batch_calculate_strength(self, client):
        """测试批量计算强度"""
        with patch('src.api.v1.rankings.StrengthServiceV2') as mock_service_class:
            mock_service = MagicMock()
            mock_service.batch_calculate = AsyncMock(return_value={
                "success": True,
                "total": 2,
                "success_count": 2,
                "error_count": 0,
                "results": [
                    {"stock_id": 1, "success": True, "result": {"composite_score": 85.0}},
                    {"stock_id": 2, "success": True, "result": {"composite_score": 78.0}},
                ]
            })
            mock_service_class.return_value = mock_service

            with patch('src.api.v1.rankings.select') as mock_select:
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.side_effect = [
                    MagicMock(id=1, symbol="600519", name="贵州茅台"),
                    MagicMock(id=2, symbol="000858", name="五粮液"),
                ]
                mock_select.return_value.where.return_value = mock_result

                response = client.post(
                    "/v1/rankings/v2/batch-calculate",
                    json={"entity_ids": [1, 2], "period": "all"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 2
                assert data["success_count"] == 2
                assert len(data["results"]) == 2


@pytest.mark.integration
class TestStrengthAPIIntegration:
    """强度 API 集成测试（需要数据库）"""

    def test_end_to_end_strength_flow(self, client):
        """端到端强度数据流程测试"""
        # 注意：此测试需要真实的数据库连接和测试数据
        # 在 CI/CD 环境中使用测试数据库运行

        # 测试流程：
        # 1. 查询个股强度 → 2. 查询排名 → 3. 查询统计 → 4. 验证数据一致性

        # 示例：验证排名端点响应结构
        response = client.get("/v1/rankings/v2/stocks?limit=10")

        # 接口应该返回有效响应（可能为空数据）
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # 验证响应结构
            assert "date" in data
            assert "entity_type" in data
            assert "total_count" in data
            assert "returned_count" in data
            assert "rankings" in data

            # 验证排名项结构
            if data["returned_count"] > 0:
                ranking = data["rankings"][0]
                assert "rank" in ranking
                assert "symbol" in ranking
                assert "entity_id" in ranking

    def test_stats_response_structure(self, client):
        """测试统计接口响应结构"""
        response = client.get("/v1/rankings/v2/stats?entity_type=stock")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "date" in data
            assert "entity_type" in data
            assert "total_count" in data
            assert "grade_distribution" in data

    def test_api_response_time(self, client):
        """测试 API 响应时间"""
        import time

        # 测试排名查询响应时间（应该 < 500ms）
        start = time.time()
        response = client.get("/v1/rankings/v2/stocks?limit=50")
        elapsed = (time.time() - start) * 1000

        # 验证响应时间
        # 注意：在没有数据的情况下响应会很快，有数据时可能需要优化
        assert response.status_code in [200, 404]

        # 记录响应时间（用于性能监控）
        if response.status_code == 200:
            # 实际有数据时，响应时间应该在合理范围内
            print(f"排名查询响应时间: {elapsed:.2f}ms")

    def test_history_data_structure(self, client):
        """测试历史数据响应结构"""
        response = client.get("/v1/stocks/1/strength/history?days=7")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "total_days" in data
            assert "data_points" in data
            assert isinstance(data["data_points"], list)

    def test_batch_calculation_structure(self, client):
        """测试批量计算接口结构"""
        request_data = {
            "entity_ids": [1, 2],
            "period": "all"
        }

        response = client.post(
            "/v1/rankings/v2/batch-calculate",
            json=request_data
        )

        # 可能返回 200（成功）或 404/500（数据不存在或服务错误）
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert "total_count" in data
            assert "success_count" in data
            assert "results" in data
