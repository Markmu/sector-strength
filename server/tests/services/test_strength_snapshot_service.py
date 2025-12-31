"""
强度快照服务测试 (Story 10.5 - Task 1)
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.strength_snapshot_service import StrengthSnapshotService


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def snapshot_service(mock_session):
    """创建快照服务实例"""
    return StrengthSnapshotService(mock_session)


@pytest.fixture
def mock_stocks():
    """模拟股票数据"""
    return [
        MagicMock(id=1, symbol="600519", name="贵州茅台"),
        MagicMock(id=2, symbol="000858", name="五粮液"),
        MagicMock(id=3, symbol="600036", name="招商银行"),
    ]


@pytest.fixture
def mock_sectors():
    """模拟板块数据"""
    return [
        MagicMock(id=1, code="BK0426", name="半导体"),
        MagicMock(id=2, code="BK0473", name="白酒"),
    ]


class TestStrengthSnapshotService:
    """快照服务基础测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        service = StrengthSnapshotService(mock_session)
        assert service.session == mock_session
        assert service.strength_service is not None

    def test_set_progress_callback(self, snapshot_service):
        """测试设置进度回调"""
        callback = AsyncMock()
        snapshot_service.set_progress_callback(callback)
        assert snapshot_service._progress_callback == callback


class TestCreateDailySnapshot:
    """创建每日快照测试"""

    @pytest.mark.asyncio
    async def test_create_daily_snapshot_success(
        self, snapshot_service, mock_stocks, mock_sectors
    ):
        """测试成功创建每日快照"""
        test_date = date.today()
        stock_ids = [s.id for s in mock_stocks]
        sector_ids = [s.id for s in mock_sectors]

        # 模拟强度计算成功
        snapshot_service.strength_service.calculate_stock_strength = AsyncMock(
            return_value={
                "success": True,
                "result": {"composite_score": 85.0}
            }
        )
        snapshot_service.strength_service.calculate_sector_strength = AsyncMock(
            return_value={
                "success": True,
                "result": {"composite_score": 75.0}
            }
        )

        # 模拟排名更新
        snapshot_service._update_ranks_and_percentiles = AsyncMock()

        # 模拟 session.execute 返回股票 ID
        stock_result = MagicMock()
        stock_row = MagicMock()
        stock_row.__getitem__ = lambda self, key: stock_ids[key] if key < len(stock_ids) else None
        stock_result.all.return_value = [(id,) for id in stock_ids]

        sector_result = MagicMock()
        sector_result.all.return_value = [(id,) for id in sector_ids]

        # 设置 execute mock
        execute_results = [stock_result, sector_result]

        async def mock_execute(stmt):
            return execute_results.pop(0) if execute_results else MagicMock()

        snapshot_service.session.execute = mock_execute

        result = await snapshot_service.create_daily_snapshot(test_date)

        assert result["date"] == test_date
        assert result["stocks"]["success"] == len(stock_ids)
        assert result["sectors"]["success"] == len(sector_ids)
        assert result["summary"]["total_entities"] == len(stock_ids) + len(sector_ids)
        assert result["summary"]["total_success"] == len(stock_ids) + len(sector_ids)
        assert result["summary"]["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_create_daily_snapshot_with_errors(
        self, snapshot_service, mock_stocks
    ):
        """测试包含错误的快照创建"""
        test_date = date.today()
        stock_ids = [s.id for s in mock_stocks]

        # 模拟第一个成功，第二个失败，第三个成功
        call_count = [0]

        async def mock_calculate(stock_id, calc_date):
            call_count[0] += 1
            if call_count[0] == 2:
                return {"success": False, "error": "数据不足"}
            return {
                "success": True,
                "result": {"composite_score": 80.0}
            }

        snapshot_service.strength_service.calculate_stock_strength = mock_calculate
        snapshot_service.strength_service.calculate_sector_strength = AsyncMock(
            return_value={"success": True, "result": {"composite_score": 70.0}}
        )
        snapshot_service._update_ranks_and_percentiles = AsyncMock()

        # 模拟 session.execute
        stock_result = MagicMock()
        stock_result.all.return_value = [(id,) for id in stock_ids]

        sector_result = MagicMock()
        sector_result.all.return_value = []

        execute_results = [stock_result, sector_result]

        async def mock_execute(stmt):
            return execute_results.pop(0) if execute_results else MagicMock()

        snapshot_service.session.execute = mock_execute

        result = await snapshot_service.create_daily_snapshot(test_date)

        assert result["stocks"]["success"] == 2
        assert result["stocks"]["error"] == 1
        assert result["summary"]["total_success"] == 2  # 2股票 + 0板块
        assert result["summary"]["total_error"] == 1


class TestBatchCreateSnapshots:
    """批量快照测试"""

    @pytest.mark.asyncio
    async def test_batch_create_invalid_range(self, snapshot_service):
        """测试无效日期范围"""
        start = date(2024, 1, 10)
        end = date(2024, 1, 1)

        result = await snapshot_service.batch_create_snapshots(start, end)

        assert result["success"] is False
        assert "开始日期不能晚于结束日期" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_too_many_days(self, snapshot_service):
        """测试超过最大天数限制"""
        start = date(2023, 1, 1)
        end = date(2024, 1, 2)  # 超过365天

        result = await snapshot_service.batch_create_snapshots(start, end)

        assert result["success"] is False
        assert "最多支持365天" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_create_success(self, snapshot_service):
        """测试批量创建成功"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)  # 3天

        # 模拟每日快照创建
        snapshot_service.create_daily_snapshot = AsyncMock(
            return_value={
                "date": start,
                "summary": {
                    "total_entities": 10,
                    "total_success": 10,
                    "total_error": 0
                }
            }
        )

        result = await snapshot_service.batch_create_snapshots(start, end)

        assert result["success"] is True
        assert result["total_days"] == 3
        assert len(result["daily_results"]) == 3
        assert result["summary"]["total_success"] == 30  # 10 * 3

    @pytest.mark.asyncio
    async def test_batch_create_single_day(self, snapshot_service):
        """测试单日批量创建"""
        test_date = date.today()

        snapshot_service.create_daily_snapshot = AsyncMock(
            return_value={
                "date": test_date,
                "summary": {
                    "total_entities": 5,
                    "total_success": 5,
                    "total_error": 0
                }
            }
        )

        result = await snapshot_service.batch_create_snapshots(test_date, test_date)

        assert result["success"] is True
        assert result["total_days"] == 1
        assert snapshot_service.create_daily_snapshot.call_count == 1


class TestUpdateRanksAndPercentiles:
    """排名和百分位更新测试"""

    @pytest.mark.asyncio
    async def test_update_stock_ranks(self, snapshot_service):
        """测试更新股票排名"""
        test_date = date.today()

        # 模拟股票分数数据
        mock_scores = [
            MagicMock(id=1, score=95),
            MagicMock(id=2, score=85),
            MagicMock(id=3, score=75),
        ]

        stock_result = MagicMock()
        stock_result.scalars.return_value.all.return_value = mock_scores

        sector_result = MagicMock()
        sector_result.scalars.return_value.all.return_value = []

        # 模拟 session.execute
        execute_results = [stock_result, sector_result]

        async def mock_execute(stmt):
            return execute_results.pop(0) if execute_results else MagicMock()

        snapshot_service.session.execute = mock_execute

        await snapshot_service._update_ranks_and_percentiles(test_date)

        # 验证排名设置
        assert mock_scores[0].rank == 1
        assert mock_scores[1].rank == 2
        assert mock_scores[2].rank == 3

        # 验证百分位设置
        assert mock_scores[0].percentile == 100.0
        assert mock_scores[1].percentile == pytest.approx(66.67, rel=1e-2)
        assert mock_scores[2].percentile == pytest.approx(33.33, rel=1e-2)


class TestGetSnapshotStatus:
    """快照状态查询测试"""

    @pytest.mark.asyncio
    async def test_get_snapshot_status_complete(self, snapshot_service):
        """测试完整快照状态"""
        test_date = date.today()

        # 模拟计数查询结果
        stock_count_result = MagicMock()
        stock_count_result.scalar.return_value = 100

        sector_count_result = MagicMock()
        sector_count_result.scalar.return_value = 50

        total_stock_result = MagicMock()
        total_stock_result.scalar.return_value = 100

        total_sector_result = MagicMock()
        total_sector_result.scalar.return_value = 50

        execute_results = [
            stock_count_result,
            sector_count_result,
            total_stock_result,
            total_sector_result,
        ]

        async def mock_execute(stmt):
            return execute_results.pop(0) if execute_results else MagicMock()

        snapshot_service.session.execute = mock_execute

        status = await snapshot_service.get_snapshot_status(test_date)

        assert status["date"] == test_date
        assert status["stocks"]["total"] == 100
        assert status["stocks"]["snapshotted"] == 100
        assert status["stocks"]["coverage"] == 100.0
        assert status["sectors"]["total"] == 50
        assert status["sectors"]["snapshotted"] == 50
        assert status["is_complete"] is True

    @pytest.mark.asyncio
    async def test_get_snapshot_status_partial(self, snapshot_service):
        """测试部分快照状态"""
        test_date = date.today()

        # 模拟部分快照
        stock_count_result = MagicMock()
        stock_count_result.scalar.return_value = 80  # 100个股票只快照了80个

        sector_count_result = MagicMock()
        sector_count_result.scalar.return_value = 50

        total_stock_result = MagicMock()
        total_stock_result.scalar.return_value = 100

        total_sector_result = MagicMock()
        total_sector_result.scalar.return_value = 50

        execute_results = [
            stock_count_result,
            sector_count_result,
            total_stock_result,
            total_sector_result,
        ]

        async def mock_execute(stmt):
            return execute_results.pop(0) if execute_results else MagicMock()

        snapshot_service.session.execute = mock_execute

        status = await snapshot_service.get_snapshot_status(test_date)

        assert status["stocks"]["total"] == 100
        assert status["stocks"]["snapshotted"] == 80
        assert status["stocks"]["missing"] == 20
        assert status["stocks"]["coverage"] == 80.0
        assert status["is_complete"] is False


@pytest.mark.integration
class TestSnapshotServiceIntegration:
    """快照服务集成测试（需要真实数据库）"""

    @pytest.mark.asyncio
    async def test_end_to_end_snapshot_flow(self, snapshot_service):
        """端到端快照流程测试"""
        # 注意：此测试需要真实的数据库连接
        # 在 CI/CD 环境中使用测试数据库运行

        test_date = date.today() - timedelta(days=1)  # 使用昨天避免冲突

        # 测试流程：创建快照 → 验证状态 → 验证数据

        # 1. 创建快照
        result = await snapshot_service.create_daily_snapshot(test_date)

        # 2. 验证结果结构
        assert "date" in result
        assert "stocks" in result
        assert "sectors" in result
        assert "summary" in result

        # 3. 获取状态
        status = await snapshot_service.get_snapshot_status(test_date)
        assert "stocks" in status
        assert "sectors" in status

        # 4. 验证覆盖率合理（实际有数据时应该 > 0）
        if status["stocks"]["total"] > 0:
            assert status["stocks"]["coverage"] >= 0
            assert status["stocks"]["coverage"] <= 100

    @pytest.mark.asyncio
    async def test_batch_snapshots_performance(self, snapshot_service):
        """测试批量快照性能"""
        # 测试 3 天的批量快照
        start_date = date.today() - timedelta(days=3)
        end_date = date.today() - timedelta(days=1)

        import time
        start_time = time.time()

        result = await snapshot_service.batch_create_snapshots(
            start_date,
            end_date,
            update_ranks=True
        )

        elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

        # 验证结果
        assert result["success"] is True
        assert result["total_days"] == 3

        # 记录性能
        print(f"批量快照 (3天) 耗时: {elapsed:.2f}ms")

        # 性能基准：应该能在合理时间内完成
        # 注意：此基准依赖于数据量，仅作参考
        if result["summary"]["total_entities_processed"] > 0:
            avg_time_per_entity = elapsed / result["summary"]["total_entities_processed"]
            print(f"平均每实体耗时: {avg_time_per_entity:.2f}ms")
