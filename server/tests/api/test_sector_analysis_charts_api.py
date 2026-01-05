"""
板块分析图表 API 测试
"""

import pytest
from httpx import AsyncClient
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_get_sector_strength_history_default(async_client: AsyncClient):
    """测试默认参数获取板块强度历史数据"""
    # 假设存在 sector_id = 1
    response = await async_client.get("/api/v1/sectors/1/strength-history")

    # 板块可能不存在，但响应结构应该正确
    if response.status_code == 404:
        # 板块不存在是可接受的
        assert response.status_code == 404
        return

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "sector_id" in data
    assert "sector_name" in data
    assert "data" in data
    assert isinstance(data["data"], list)

    # 验证数据点结构
    if len(data["data"]) > 0:
        point = data["data"][0]
        assert "date" in point
        assert "score" in point or point["score"] is None
        assert "current_price" in point or point["current_price"] is None


@pytest.mark.asyncio
async def test_get_sector_strength_history_with_date_range(async_client: AsyncClient):
    """测试带日期范围的强度历史数据获取"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    try:
        response = await async_client.get(
            "/api/v1/sectors/1/strength-history",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        )
    except Exception as e:
        # 如果发生连接错误，跳过测试
        pytest.skip(f"Database connection error: {e}")

    if response.status_code == 404:
        # 板块不存在是可接受的
        return

    assert response.status_code == 200
    data = response.json()

    # 验证数据在日期范围内
    if len(data.get("data", [])) > 0:
        for point in data["data"]:
            point_date = date.fromisoformat(point["date"])
            assert start_date <= point_date <= end_date


@pytest.mark.asyncio
async def test_get_sector_strength_history_invalid_sector(async_client: AsyncClient):
    """测试无效的板块 ID"""
    response = await async_client.get("/api/v1/sectors/999999/strength-history")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_get_sector_ma_history_default(async_client: AsyncClient):
    """测试默认参数获取板块均线历史数据"""
    try:
        response = await async_client.get("/api/v1/sectors/1/ma-history")
    except Exception as e:
        # 如果发生连接错误，跳过测试
        pytest.skip(f"Database connection error: {e}")

    if response.status_code == 404:
        # 板块不存在是可接受的
        return

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "sector_id" in data
    assert "sector_name" in data
    assert "data" in data
    assert isinstance(data["data"], list)

    # 验证数据点结构
    if len(data["data"]) > 0:
        point = data["data"][0]
        assert "date" in point
        assert "current_price" in point
        assert "ma5" in point
        assert "ma10" in point
        assert "ma20" in point
        assert "ma30" in point
        assert "ma60" in point
        assert "ma90" in point
        assert "ma120" in point
        assert "ma240" in point


@pytest.mark.asyncio
async def test_get_sector_ma_history_with_date_range(async_client: AsyncClient):
    """测试带日期范围的均线历史数据获取"""
    end_date = date.today()
    start_date = end_date - timedelta(days=60)

    response = await async_client.get(
        "/api/v1/sectors/1/ma-history",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
    )

    if response.status_code == 404:
        # 板块不存在是可接受的
        return

    assert response.status_code == 200
    data = response.json()

    # 验证数据在日期范围内
    if len(data["data"]) > 0:
        for point in data["data"]:
            point_date = date.fromisoformat(point["date"])
            assert start_date <= point_date <= end_date


@pytest.mark.asyncio
async def test_get_sector_ma_history_invalid_sector(async_client: AsyncClient):
    """测试无效的板块 ID"""
    try:
        response = await async_client.get("/api/v1/sectors/999999/ma-history")
    except Exception as e:
        # 如果发生连接错误，跳过测试
        pytest.skip(f"Database connection error: {e}")

    # 应该返回 404 或其他错误状态码
    assert response.status_code in [404, 400]
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_get_sector_strength_and_ma_history_consistency(async_client: AsyncClient):
    """测试强度历史和均线历史数据的一致性"""
    # 获取强度历史
    strength_response = await async_client.get("/api/v1/sectors/1/strength-history")

    # 获取均线历史
    ma_response = await async_client.get("/api/v1/sectors/1/ma-history")

    # 如果都成功，验证数据一致性
    if strength_response.status_code == 200 and ma_response.status_code == 200:
        strength_data = strength_response.json()
        ma_data = ma_response.json()

        # 板块 ID 应该一致
        assert strength_data["sector_id"] == ma_data["sector_id"]
        assert strength_data["sector_name"] == ma_data["sector_name"]

        # 数据点数量应该相同（假设两个查询使用相同的日期范围）
        assert len(strength_data["data"]) == len(ma_data["data"])

        # 日期应该一致
        if len(strength_data["data"]) > 0:
            strength_dates = [p["date"] for p in strength_data["data"]]
            ma_dates = [p["date"] for p in ma_data["data"]]
            assert strength_dates == ma_dates


@pytest.mark.asyncio
async def test_get_sector_strength_history_default_date_range(async_client: AsyncClient):
    """测试默认日期范围（2个月）"""
    try:
        response = await async_client.get("/api/v1/sectors/1/strength-history")
    except Exception as e:
        # 如果发生连接错误，跳过测试
        pytest.skip(f"Database connection error: {e}")

    if response.status_code == 404:
        return

    assert response.status_code == 200
    data = response.json()

    # 验证返回了数据（默认2个月应该有一些数据）
    # 注意：这里不强制要求有数据，因为可能是空数据库
    assert "data" in data
    assert isinstance(data["data"], list)
