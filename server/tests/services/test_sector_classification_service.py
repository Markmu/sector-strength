"""
测试 SectorClassificationService

测试板块分类服务的核心功能。
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.sector_classification_service import (
    SectorClassificationService,
    ClassificationResult,
    calculate_classification_level,
    calculate_state,
)
from src.exceptions.classification import (
    MissingMADataError,
    InvalidPriceError,
    ClassificationFailedError,
)


class TestCalculateClassificationLevel:
    """测试分类级别计算函数"""

    def test_level_9_all_above(self):
        """测试第9类：当前价格 > 所有均线"""
        ma_values = {
            'ma_5': 100, 'ma_10': 95, 'ma_20': 90, 'ma_30': 85,
            'ma_60': 80, 'ma_90': 75, 'ma_120': 70, 'ma_240': 65
        }
        assert calculate_classification_level(110, ma_values) == 9

    def test_level_8_conquered_240(self):
        """测试第8类：攻克240日线"""
        ma_values = {
            'ma_5': 100, 'ma_10': 95, 'ma_20': 90, 'ma_30': 85,
            'ma_60': 80, 'ma_90': 75, 'ma_120': 70, 'ma_240': 65
        }
        assert calculate_classification_level(95, ma_values) == 8

    def test_level_1_all_below(self):
        """测试第1类：价格在所有均线下方"""
        ma_values = {
            'ma_5': 100, 'ma_10': 95, 'ma_20': 90, 'ma_30': 85,
            'ma_60': 80, 'ma_90': 75, 'ma_120': 70, 'ma_240': 65
        }
        assert calculate_classification_level(50, ma_values) == 1

    def test_missing_ma_data(self):
        """测试缺少均线数据时抛出异常"""
        ma_values = {
            'ma_5': 100, 'ma_10': 95, 'ma_20': 90, 'ma_30': 85,
            'ma_60': 80, 'ma_90': 75, 'ma_120': 70
            # 缺少 ma_240
        }
        with pytest.raises(MissingMADataError):
            calculate_classification_level(110, ma_values)


class TestCalculateState:
    """测试状态计算函数"""

    def test_bounce_state(self):
        """测试反弹状态"""
        assert calculate_state(110, 100) == '反弹'

    def test_adjust_state(self):
        """测试调整状态"""
        assert calculate_state(100, 110) == '调整'

    def test_equal_prices(self):
        """测试价格相等时返回调整"""
        assert calculate_state(100, 100) == '调整'


class TestSectorClassificationService:
    """测试板块分类服务"""

    @pytest.fixture
    def mock_session(self):
        """创建mock数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def service(self, mock_session):
        """创建服务实例"""
        return SectorClassificationService(mock_session)

    @pytest.fixture
    def mock_ma_data(self):
        """创建模拟均线数据"""
        return {
            'ma_5': 100.0, 'ma_10': 95.0, 'ma_20': 90.0, 'ma_30': 85.0,
            'ma_60': 80.0, 'ma_90': 75.0, 'ma_120': 70.0, 'ma_240': 65.0
        }

    @pytest.mark.asyncio
    async def test_get_ma_data_success(self, service, mock_session):
        """测试成功获取均线数据"""
        from src.models.moving_average_data import MovingAverageData
        from sqlalchemy import select

        # 创建mock结果
        mock_result = MagicMock()
        mock_ma = MagicMock()
        mock_ma.ma_value = 100.0
        mock_result.scalar_one_or_none.return_value = mock_ma

        mock_session.execute.return_value = mock_result

        result = await service.get_ma_data(1, date.today())

        assert result['ma_5'] == 100.0
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_get_ma_data_missing(self, service, mock_session):
        """测试均线数据缺失"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(MissingMADataError):
            await service.get_ma_data(1, date.today())

    @pytest.mark.asyncio
    async def test_calculate_classification_success(self, service, mock_session, mock_ma_data):
        """测试成功计算分类"""
        from src.models.sector import Sector

        # Mock sector查询
        mock_sector = MagicMock()
        mock_sector.id = 1
        mock_sector.name = "测试板块"
        mock_sector.code = "TEST"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_sector
        mock_session.execute.return_value = mock_result

        # Mock get_ma_data
        with patch.object(service, 'get_ma_data', return_value=mock_ma_data):
            # Mock get_price_data
            with patch.object(service, 'get_price_data', return_value=(110.0, 100.0)):
                result = await service.calculate_classification(1, date.today())

        assert result.sector_id == 1
        assert result.sector_name == "测试板块"
        assert result.symbol == "TEST"
        assert result.classification_level == 9
        assert result.state == '反弹'

    @pytest.mark.asyncio
    async def test_get_classification_status(self, service, mock_session):
        """测试获取分类状态"""
        from sqlalchemy import func

        # 创建一系列mock结果
        call_count = [0]

        async def mock_execute(stmt):
            call_count[0] += 1
            mock_result = MagicMock()

            if call_count[0] == 1:  # 最新日期
                mock_result.scalar.return_value = date.today()
            elif call_count[0] == 2:  # 总数
                mock_result.scalar.return_value = 10
            elif call_count[0] == 3:  # 按级别统计
                mock_result.all.return_value = [(9, 5), (8, 3), (7, 2)]
            else:  # 按状态统计
                mock_result.all.return_value = [('反弹', 6), ('调整', 4)]

            return mock_result

        mock_session.execute.side_effect = mock_execute

        status = await service.get_classification_status()

        assert status['total_sectors'] == 10
        assert status['by_level'][9] == 5
        assert status['by_state']['反弹'] == 6


@pytest.mark.asyncio
async def test_initialize_classifications_basic():
    """测试初始化分类数据的基本流程"""
    # 这个测试需要更多的mock设置，这里提供基本框架
    from src.services.sector_classification_service import SectorClassificationService

    mock_session = AsyncMock(spec=AsyncSession)
    service = SectorClassificationService(mock_session)

    # 设置进度回调mock
    progress_mock = AsyncMock()
    service.set_progress_callback(progress_mock)

    # 这里应该mock所有必要的数据库查询
    # 实际测试中需要完整设置所有依赖

    # 基本验证：服务可以被实例化
    assert service is not None
    assert service._progress_callback == progress_mock


class TestClassificationResult:
    """测试分类结果数据类"""

    def test_create_result(self):
        """测试创建分类结果"""
        result = ClassificationResult(
            sector_id=1,
            sector_name="测试板块",
            symbol="TEST",
            classification_level=9,
            state="反弹",
            current_price=110.0,
            ma_values={'ma_5': 100.0},
            price_5_days_ago=100.0,
            classification_date=date.today()
        )

        assert result.sector_id == 1
        assert result.classification_level == 9
        assert result.state == "反弹"
