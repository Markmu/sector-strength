"""
板块 API 测试

测试板块相关的 API 端点。
"""

import pytest
from httpx import AsyncClient


class TestSectorsList:
    """板块列表 API 测试"""

    @pytest.mark.asyncio
    async def test_get_sectors_success(self, client: AsyncClient):
        """测试获取板块列表 - 成功"""
        response = await client.get("/api/v1/sectors")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]

    @pytest.mark.asyncio
    async def test_get_sectors_with_type_filter(self, client: AsyncClient):
        """测试按类型筛选板块"""
        response = await client.get("/api/v1/sectors?sector_type=concept")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_sectors_with_sorting(self, client: AsyncClient):
        """测试排序功能"""
        response = await client.get("/api/v1/sectors?sort_by=code&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_sectors_with_pagination(self, client: AsyncClient):
        """测试分页功能"""
        response = await client.get("/api/v1/sectors?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_sectors_invalid_page(self, client: AsyncClient):
        """测试无效页码"""
        response = await client.get("/api/v1/sectors?page=0")

        # FastAPI 自动验证，应该返回 422
        assert response.status_code == 422


class TestSectorDetail:
    """板块详情 API 测试"""

    @pytest.mark.asyncio
    async def test_get_sector_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的板块"""
        response = await client.get("/api/v1/sectors/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data


class TestSectorStocks:
    """板块成分股 API 测试"""

    @pytest.mark.asyncio
    async def test_get_sector_stocks_not_found(self, client: AsyncClient):
        """测试获取不存在板块的成分股"""
        response = await client.get("/api/v1/sectors/non-existent-id/stocks")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_sector_stocks_with_sorting(self, client: AsyncClient):
        """测试成分股排序"""
        # 假设存在某个板块
        response = await client.get("/api/v1/sectors/test-sector/stocks?sort_by=symbol&sort_order=asc")

        # 即使板块不存在，也应该返回 404
        # 如果板块存在，应该返回 200
        assert response.status_code in [200, 404]


class TestAPIResponseFormat:
    """API 响应格式测试"""

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, client: AsyncClient):
        """测试响应格式一致性"""
        response = await client.get("/api/v1/sectors")

        assert response.status_code == 200
        data = response.json()

        # 检查必须包含的字段
        assert "success" in data
        assert isinstance(data["success"], bool)
        assert "data" in data

    @pytest.mark.asyncio
    async def test_error_response_format(self, client: AsyncClient):
        """测试错误响应格式"""
        response = await client.get("/api/v1/sectors/non-existent-id")

        assert response.status_code == 404
        data = response.json()

        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
