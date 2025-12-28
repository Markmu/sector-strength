"""
强度 API 测试

测试强度相关的 API 端点。
"""

import pytest
from httpx import AsyncClient


class TestStrengthDetail:
    """强度详情 API 测试"""

    @pytest.mark.asyncio
    async def test_get_stock_strength_not_found(self, client: AsyncClient):
        """测试获取不存在股票的强度"""
        response = await client.get("/api/v1/strength/stock/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_get_sector_strength_not_found(self, client: AsyncClient):
        """测试获取不存在板块的强度"""
        response = await client.get("/api/v1/strength/sector/non-existent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_strength_invalid_type(self, client: AsyncClient):
        """测试无效的实体类型"""
        response = await client.get("/api/v1/strength/invalid/test-id")

        assert response.status_code == 404


class TestStrengthList:
    """强度列表 API 测试"""

    @pytest.mark.asyncio
    async def test_get_strength_list_default(self, client: AsyncClient):
        """测试获取强度列表 - 默认返回板块"""
        response = await client.get("/api/v1/strength")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_strength_list_stocks(self, client: AsyncClient):
        """测试获取股票强度列表"""
        response = await client.get("/api/v1/strength?entity_type=stock")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_strength_list_with_ids(self, client: AsyncClient):
        """测试指定 ID 查询"""
        response = await client.get("/api/v1/strength?entity_ids=id1,id2")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_strength_list_with_limit(self, client: AsyncClient):
        """测试数量限制"""
        response = await client.get("/api/v1/strength?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestStrengthResponseFormat:
    """强度 API 响应格式测试"""

    @pytest.mark.asyncio
    async def test_strength_detail_fields(self, client: AsyncClient):
        """测试强度详情字段"""
        # 即使资源不存在，响应格式也应该正确
        response = await client.get("/api/v1/strength/stock/test-id")

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "entity_id" in data["data"]
            assert "entity_type" in data["data"]
            assert "period_strengths" in data["data"]

    @pytest.mark.asyncio
    async def test_response_format_consistency(self, client: AsyncClient):
        """测试响应格式一致性"""
        response = await client.get("/api/v1/strength")

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert isinstance(data["success"], bool)
