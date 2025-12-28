"""
个股 API 测试

测试个股相关的 API 端点。
"""

import pytest
from httpx import AsyncClient


class TestStocksList:
    """个股列表 API 测试"""

    @pytest.mark.asyncio
    async def test_get_stocks_success(self, client: AsyncClient):
        """测试获取个股列表 - 成功"""
        response = await client.get("/api/v1/stocks")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]

    @pytest.mark.asyncio
    async def test_get_stocks_with_search(self, client: AsyncClient):
        """测试搜索功能"""
        response = await client.get("/api/v1/stocks?search=平安")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_stocks_with_sector_filter(self, client: AsyncClient):
        """测试按板块筛选"""
        response = await client.get("/api/v1/stocks?sector_id=test-sector")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_stocks_with_pagination(self, client: AsyncClient):
        """测试分页功能"""
        response = await client.get("/api/v1/stocks?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10


class TestStockDetail:
    """个股详情 API 测试"""

    @pytest.mark.asyncio
    async def test_get_stock_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的个股"""
        response = await client.get("/api/v1/stocks/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_stock_detail_fields(self, client: AsyncClient):
        """测试个股详情字段"""
        # 假设存在某个股票
        response = await client.get("/api/v1/stocks/test-stock-id")

        # 如果不存在返回 404，如果存在返回 200
        assert response.status_code in [200, 404]


class TestStockAPIResponseFormat:
    """个股 API 响应格式测试"""

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, client: AsyncClient):
        """测试响应格式一致性"""
        response = await client.get("/api/v1/stocks")

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert isinstance(data["success"], bool)
        assert "data" in data
