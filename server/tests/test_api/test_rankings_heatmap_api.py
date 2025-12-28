"""
排名和热力图 API 测试

测试排名和热力图相关的 API 端点。
"""

import pytest
from httpx import AsyncClient


class TestRankings:
    """排名 API 测试"""

    @pytest.mark.asyncio
    async def test_get_sector_rankings(self, client: AsyncClient):
        """测试获取板块排名"""
        response = await client.get("/api/v1/rankings/sectors")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data
        assert "top_n" in data

    @pytest.mark.asyncio
    async def test_get_sector_rankings_with_top_n(self, client: AsyncClient):
        """测试指定返回数量"""
        response = await client.get("/api/v1/rankings/sectors?top_n=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["top_n"] <= 10

    @pytest.mark.asyncio
    async def test_get_sector_rankings_ascending(self, client: AsyncClient):
        """测试升序排名（弱势优先）"""
        response = await client.get("/api/v1/rankings/sectors?order=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_stock_rankings(self, client: AsyncClient):
        """测试获取个股排名"""
        response = await client.get("/api/v1/rankings/stocks")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_stock_rankings_with_sector(self, client: AsyncClient):
        """测试按板块筛选个股排名"""
        response = await client.get("/api/v1/rankings/stocks?sector_id=test-sector")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestHeatmap:
    """热力图 API 测试"""

    @pytest.mark.asyncio
    async def test_get_heatmap_data(self, client: AsyncClient):
        """测试获取热力图数据"""
        response = await client.get("/api/v1/heatmap")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "sectors" in data["data"]
        assert isinstance(data["data"]["sectors"], list)
        assert "timestamp" in data["data"]

    @pytest.mark.asyncio
    async def test_get_heatmap_data_with_type_filter(self, client: AsyncClient):
        """测试按类型筛选热力图数据"""
        response = await client.get("/api/v1/heatmap?sector_type=concept")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_heatmap_sector_fields(self, client: AsyncClient):
        """测试热力图板块字段"""
        response = await client.get("/api/v1/heatmap")

        assert response.status_code == 200
        data = response.json()

        if len(data["data"]["sectors"]) > 0:
            sector = data["data"]["sectors"][0]
            assert "id" in sector
            assert "name" in sector
            assert "value" in sector
            assert "color" in sector


class TestRankingsHeatmapResponseFormat:
    """排名和热力图响应格式测试"""

    @pytest.mark.asyncio
    async def test_ranking_item_fields(self, client: AsyncClient):
        """测试排名项字段"""
        response = await client.get("/api/v1/rankings/sectors")

        assert response.status_code == 200
        data = response.json()

        if len(data["data"]) > 0:
            item = data["data"][0]
            assert "id" in item
            assert "name" in item
            assert "code" in item
            assert "strength_score" in item
            assert "rank" in item

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, client: AsyncClient):
        """测试响应格式一致性"""
        response = await client.get("/api/v1/heatmap")

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert isinstance(data["success"], bool)
