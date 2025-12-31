"""
板块散点图分析 API 测试
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_sector_scatter_data_default(async_client: AsyncClient):
    """测试默认参数获取散点图数据"""
    response = await async_client.get("/api/v1/analysis/sector-scatter")

    # API 可能返回空数据，但响应结构应该正确
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data

    result = data["data"]
    assert "scatter_data" in result
    assert "total_count" in result
    assert "returned_count" in result
    assert "filters_applied" in result
    assert "cache_status" in result

    # 验证散点图数据结构
    scatter_data = result["scatter_data"]
    assert "industry" in scatter_data
    assert "concept" in scatter_data
    assert isinstance(scatter_data["industry"], list)
    assert isinstance(scatter_data["concept"], list)


@pytest.mark.asyncio
async def test_get_sector_scatter_data_with_filters(async_client: AsyncClient):
    """测试带筛选参数的散点图数据获取"""
    response = await async_client.get("/api/v1/analysis/sector-scatter", params={
        "x_axis": "long",
        "y_axis": "composite",
        "sector_type": "industry",
        "min_grade": "B",
        "max_grade": "S",
        "offset": 0,
        "limit": 50,
    })

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    result = data["data"]

    # 验证筛选条件被应用
    filters = result["filters_applied"]
    assert filters["sector_type"] == "industry"
    assert filters["grade_range"] == ["B", "S"]
    assert filters["axes"] == ["long", "composite"]
    assert filters["pagination"]["offset"] == 0
    assert filters["pagination"]["limit"] == 50

    # 验证返回数量不超过 limit
    scatter_data = result["scatter_data"]
    assert len(scatter_data["industry"]) + len(scatter_data["concept"]) <= 50


@pytest.mark.asyncio
async def test_get_sector_scatter_data_invalid_axis(async_client: AsyncClient):
    """测试无效的轴参数（应使用默认值）"""
    response = await async_client.get("/api/v1/analysis/sector-scatter", params={
        "x_axis": "invalid",  # 无效值，应使用默认值
        "y_axis": "medium",
    })

    # 请求应该成功（使用默认轴值）
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_sector_scatter_data_pagination(async_client: AsyncClient):
    """测试分页功能"""
    # 第一页
    response1 = await async_client.get("/api/v1/analysis/sector-scatter", params={
        "offset": 0,
        "limit": 10,
    })

    assert response1.status_code == 200
    data1 = response1.json()
    result1 = data1["data"]
    assert result1["returned_count"] <= 10

    # 第二页
    response2 = await async_client.get("/api/v1/analysis/sector-scatter", params={
        "offset": 10,
        "limit": 10,
    })

    assert response2.status_code == 200
    data2 = response2.json()
    result2 = data2["data"]
    assert result2["returned_count"] <= 10


@pytest.mark.asyncio
async def test_get_sector_scatter_data_grade_filter(async_client: AsyncClient):
    """测试强度等级筛选"""
    response = await async_client.get("/api/v1/analysis/sector-scatter", params={
        "min_grade": "A",
        "max_grade": "S",
    })

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    # 验证等级筛选被应用
    assert result["filters_applied"]["grade_range"] == ["A", "S"]

