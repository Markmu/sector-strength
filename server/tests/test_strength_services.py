"""
强度服务测试套件

测试排名、历史、缓存等服务功能。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ranking_service import RankingService
from src.services.strength_history_service import StrengthHistoryService
from src.services.exceptions import (
    InsufficientDataError,
    CalculationError,
    DataNotFoundError,
    BatchCalculationError,
)
from src.services.cache.strength_cache import StrengthCache
from src.models.strength_score import StrengthScore


# ========== RankingService 测试 ==========

class TestRankingService:
    """排名计算服务测试"""

    @pytest.fixture
    def session(self):
        """创建测试会话"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def ranking_service(self, session):
        """创建排名服务实例"""
        return RankingService(session)

    @pytest.fixture
    def mock_scores(self):
        """创建模拟得分数据"""
        scores = []
        for i in range(5):
            score = MagicMock(spec=StrengthScore)
            score.score = 90 - i * 10  # 90, 80, 70, 60, 50
            score.entity_id = i + 1
            score.symbol = f"TEST{i+1}"
            score.strength_grade = "S" if i < 2 else "A"
            scores.append(score)
        return scores

    @pytest.mark.asyncio
    async def test_calculate_rankings_success(self, ranking_service, session, mock_scores):
        """测试成功计算排名"""
        calc_date = date.today()

        # 模拟数据库查询
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_scores
        session.execute.return_value = mock_result

        result = await ranking_service.calculate_rankings(calc_date, ['stock'])

        # 验证
        assert result["success"] is True
        assert result["date"] == calc_date
        assert result["results"]["stock"]["total"] == 5

        # 验证排名和百分位设置
        for idx, score in enumerate(mock_scores):
            assert score.rank == idx + 1
            assert score.percentile == round((1 - (idx + 1) / 5) * 100, 2)

    @pytest.mark.asyncio
    async def test_calculate_rankings_no_data(self, ranking_service, session):
        """测试无数据情况"""
        calc_date = date.today()

        # 模拟无数据
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        result = await ranking_service.calculate_rankings(calc_date, ['stock'])

        assert result["success"] is True
        assert result["results"]["stock"]["total"] == 0

    @pytest.mark.asyncio
    async def test_get_top_rankings(self, ranking_service, session, mock_scores):
        """测试获取排名前列"""
        calc_date = date.today()

        # 设置排名
        for idx, score in enumerate(mock_scores):
            score.rank = idx + 1
            score.percentile = round((1 - (idx + 1) / 5) * 100, 2)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_scores[:3]
        session.execute.return_value = mock_result

        results = await ranking_service.get_top_rankings('stock', 3, calc_date)

        assert len(results) == 3
        assert results[0]['rank'] == 1
        assert results[0]['score'] == 90

    @pytest.mark.asyncio
    async def test_get_entity_ranking(self, ranking_service, session):
        """测试获取实体排名"""
        calc_date = date.today()

        mock_score = MagicMock(spec=StrengthScore)
        mock_score.entity_id = 1
        mock_score.symbol = "TEST1"
        mock_score.score = 90
        mock_score.rank = 1
        mock_score.percentile = 80.0
        mock_score.strength_grade = "S"
        mock_score.price_position_score = 90
        mock_score.ma_alignment_score = 85
        mock_score.ma_alignment_state = "bullish"
        mock_score.short_term_score = 92
        mock_score.medium_term_score = 88
        mock_score.long_term_score = 85

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_score
        session.execute.return_value = mock_result

        result = await ranking_service.get_entity_ranking(1, 'stock', calc_date)

        assert result is not None
        assert result['entity_id'] == 1
        assert result['score'] == 90
        assert result['rank'] == 1

    @pytest.mark.asyncio
    async def test_get_percentile(self, ranking_service, session):
        """测试计算百分位"""
        calc_date = date.today()

        # 模拟总数=10，低于该得分的有3个
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 10
        mock_lower_result = MagicMock()
        mock_lower_result.scalar.return_value = 3

        session.execute.side_effect = [mock_total_result, mock_lower_result]

        percentile = await ranking_service.get_percentile(85, 'stock', calc_date)

        # (1 - 3/10) * 100 = 70
        assert percentile == 70.0

    @pytest.mark.asyncio
    async def test_get_percentile_no_data(self, ranking_service, session):
        """测试百分位计算无数据"""
        calc_date = date.today()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute.return_value = mock_result

        percentile = await ranking_service.get_percentile(85, 'stock', calc_date)

        assert percentile is None


# ========== StrengthHistoryService 测试 ==========

class TestStrengthHistoryService:
    """历史数据服务测试"""

    @pytest.fixture
    def session(self):
        """创建测试会话"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def history_service(self, session):
        """创建历史服务实例"""
        return StrengthHistoryService(session)

    @pytest.fixture
    def mock_history_scores(self):
        """创建模拟历史数据"""
        scores = []
        for i in range(5):
            score = MagicMock(spec=StrengthScore)
            score.date = date.today() - timedelta(days=4-i)
            score.score = 80 + i * 2
            score.rank = 10 - i
            score.percentile = 80 + i * 2
            score.strength_grade = "A"
            score.price_position_score = 75 + i
            score.ma_alignment_score = 85 + i
            score.ma_alignment_state = "bullish"
            score.short_term_score = 88 + i
            score.medium_term_score = 82 + i
            score.long_term_score = 80 + i
            score.current_price = 100 + i
            scores.append(score)
        return scores

    @pytest.mark.asyncio
    async def test_get_stock_history(self, history_service, session, mock_history_scores):
        """测试获取个股历史"""
        end_date = date.today()
        days = 5

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history_scores
        session.execute.return_value = mock_result

        history = await history_service.get_stock_history(1, days, end_date)

        assert len(history) == 5
        assert history[0]['date'] == end_date - timedelta(days=4)
        assert history[0]['score'] == 80

    @pytest.mark.asyncio
    async def test_get_sector_history(self, history_service, session, mock_history_scores):
        """测试获取板块历史"""
        end_date = date.today()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history_scores
        session.execute.return_value = mock_result

        history = await history_service.get_sector_history(1, 5, end_date)

        assert len(history) == 5
        assert 'score' in history[0]
        assert 'date' in history[0]

    @pytest.mark.asyncio
    async def test_get_history_stats(self, history_service, session, mock_history_scores):
        """测试获取历史统计"""
        end_date = date.today()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_history_scores
        session.execute.return_value = mock_result

        stats = await history_service.get_history_stats('stock', 1, 5, end_date)

        assert stats['entity_id'] == 1
        assert stats['data_count'] == 5
        assert stats['max_score'] == 88
        assert stats['min_score'] == 80
        assert stats['avg_score'] == 84.0
        assert 'up_days' in stats
        assert 'down_days' in stats
        assert 'flat_days' in stats
        assert 'grade_distribution' in stats

    @pytest.mark.asyncio
    async def test_get_history_stats_no_data(self, history_service, session):
        """测试无数据统计"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        stats = await history_service.get_history_stats('stock', 1, 5)

        assert stats['data_count'] == 0
        assert 'error' in stats

    @pytest.mark.asyncio
    async def test_get_latest_score(self, history_service, session):
        """测试获取最新得分"""
        mock_score = MagicMock(spec=StrengthScore)
        mock_score.date = date.today()
        mock_score.score = 90
        mock_score.rank = 1
        mock_score.percentile = 95
        mock_score.strength_grade = "S"
        mock_score.price_position_score = 92
        mock_score.ma_alignment_score = 88
        mock_score.current_price = 150

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_score
        session.execute.return_value = mock_result

        latest = await history_service.get_latest_score('stock', 1)

        assert latest is not None
        assert latest['score'] == 90
        assert latest['date'] == date.today()

    @pytest.mark.asyncio
    async def test_get_latest_score_not_found(self, history_service, session):
        """测试获取最新得分-不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        latest = await history_service.get_latest_score('stock', 999)

        assert latest is None


# ========== Exceptions 测试 ==========

class TestExceptions:
    """异常类测试"""

    def test_insufficient_data_error(self):
        """测试数据不足异常"""
        error = InsufficientDataError(1, 'stock', 10, 60)

        assert error.entity_id == 1
        assert error.entity_type == 'stock'
        assert error.available_days == 10
        assert error.required_days == 60
        assert 'stock' in str(error)
        assert '10' in str(error)
        assert '60' in str(error)

    def test_calculation_error(self):
        """测试计算失败异常"""
        error = CalculationError(1, 'sector', '无效的价格数据')

        assert error.entity_id == 1
        assert error.entity_type == 'sector'
        assert error.reason == '无效的价格数据'
        assert 'sector' in str(error)
        assert '无效的价格数据' in str(error)

    def test_data_not_found_error(self):
        """测试数据不存在异常"""
        test_date = date.today()
        error = DataNotFoundError(1, 'stock', test_date)

        assert error.entity_id == 1
        assert error.entity_type == 'stock'
        assert error.date == test_date
        assert 'stock' in str(error)
        assert str(test_date) in str(error)

    def test_batch_calculation_error(self):
        """测试批量计算异常"""
        errors = [
            {'entity_id': 1, 'error': 'Error 1'},
            {'entity_id': 2, 'error': 'Error 2'},
        ]
        error = BatchCalculationError(10, 8, 2, errors)

        assert error.total_count == 10
        assert error.success_count == 8
        assert error.error_count == 2
        assert error.errors == errors
        assert '8/10' in str(error)


# ========== StrengthCache 测试 ==========

class TestStrengthCache:
    """强度缓存服务测试"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return StrengthCache()

    @pytest.fixture
    def mock_cache_manager(self):
        """模拟缓存管理器"""
        with patch('src.services.cache.strength_cache.get_cache_manager') as mock:
            manager = AsyncMock()
            manager.get.return_value = None
            manager.set.return_value = True
            manager.delete.return_value = True
            manager.clear_pattern.return_value = 5
            manager.get_many.return_value = {}
            manager.cleanup_expired.return_value = 10
            mock.return_value = manager
            yield manager

    def test_generate_key(self, cache):
        """测试缓存键生成"""
        key = cache._generate_key('stock', 1, date(2025, 1, 1))

        assert key == "strength:stock:1:2025-01-01"

    def test_generate_ranking_key(self, cache):
        """测试排名缓存键生成"""
        key = cache._generate_ranking_key('stock', date(2025, 1, 1))

        assert key == "ranking:stock:2025-01-01"

    def test_generate_history_key(self, cache):
        """测试历史缓存键生成"""
        key = cache._generate_history_key('sector', 1, 30, date(2025, 1, 1))

        assert key == "history:sector:1:30:2025-01-01"

    def test_memory_cache_fifo(self, cache):
        """测试内存缓存FIFO淘汰"""
        cache._memory_cache_max = 3

        # 添加3个元素
        cache._set_memory_cache('key1', 'value1')
        cache._set_memory_cache('key2', 'value2')
        cache._set_memory_cache('key3', 'value3')

        assert cache.get_memory_cache_size() == 3

        # 添加第4个元素，应该淘汰key1
        cache._set_memory_cache('key4', 'value4')

        assert cache.get_memory_cache_size() == 3
        assert cache._get_memory_cache('key1') is None
        assert cache._get_memory_cache('key2') == 'value2'
        assert cache._get_memory_cache('key4') == 'value4'

    def test_memory_cache_update(self, cache):
        """测试内存缓存更新"""
        cache._set_memory_cache('key1', 'value1')
        cache._set_memory_cache('key1', 'value2')

        assert cache.get_memory_cache_size() == 1
        assert cache._get_memory_cache('key1') == 'value2'

    @pytest.mark.asyncio
    async def test_get_strength_from_memory(self, cache):
        """测试从内存缓存获取强度数据"""
        test_data = {'score': 90, 'rank': 1}
        cache._set_memory_cache('strength:stock:1:2025-01-01', test_data)

        result = await cache.get_strength('stock', 1, date(2025, 1, 1))

        assert result == test_data

    @pytest.mark.asyncio
    async def test_get_strength_cache_miss(self, cache, mock_cache_manager):
        """测试缓存未命中"""
        mock_cache_manager.get.return_value = None

        result = await cache.get_strength('stock', 1, date(2025, 1, 1))

        assert result is None

    @pytest.mark.asyncio
    async def test_set_strength(self, cache, mock_cache_manager):
        """测试设置强度缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        test_data = {'score': 90, 'rank': 1}

        result = await cache.set_strength('stock', 1, date(2025, 1, 1), test_data)

        assert result is True
        assert cache.get_memory_cache_size() == 1
        mock_cache_manager.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_strength(self, cache, mock_cache_manager):
        """测试删除强度缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        # 先设置
        cache._set_memory_cache('strength:stock:1:2025-01-01', {'score': 90})

        result = await cache.delete_strength('stock', 1, date(2025, 1, 1))

        assert result is True
        assert cache._get_memory_cache('strength:stock:1:2025-01-01') is None
        mock_cache_manager.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ranking_from_memory(self, cache):
        """测试从内存获取排名"""
        test_data = {'total': 100, 'ranked': 95}
        cache._set_memory_cache('ranking:stock:2025-01-01', test_data)

        result = await cache.get_ranking('stock', date(2025, 1, 1))

        assert result == test_data

    @pytest.mark.asyncio
    async def test_set_ranking(self, cache, mock_cache_manager):
        """测试设置排名缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        test_data = {'total': 100, 'ranked': 95}

        result = await cache.set_ranking('stock', date(2025, 1, 1), test_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_history_from_memory(self, cache):
        """测试从内存获取历史数据"""
        test_data = [{'date': date(2025, 1, 1), 'score': 90}]
        cache._set_memory_cache('history:stock:1:30:2025-01-01', test_data)

        result = await cache.get_history('stock', 1, 30, date(2025, 1, 1))

        assert result == test_data

    @pytest.mark.asyncio
    async def test_set_history(self, cache, mock_cache_manager):
        """测试设置历史缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        test_data = [{'date': date(2025, 1, 1), 'score': 90}]

        result = await cache.set_history('stock', 1, 30, date(2025, 1, 1), test_data)

        assert result is True

    @pytest.mark.asyncio
    async def test_clear_all_strength_cache(self, cache, mock_cache_manager):
        """测试清除所有强度缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        # 先添加一些内存缓存
        cache._set_memory_cache('strength:stock:1:2025-01-01', {'score': 90})
        cache._set_memory_cache('ranking:stock:2025-01-01', {'total': 100})

        result = await cache.clear_all_strength_cache()

        assert result >= 0
        assert cache.get_memory_cache_size() == 0

    def test_clear_memory_cache(self, cache):
        """测试清除内存缓存"""
        cache._set_memory_cache('key1', 'value1')
        cache._set_memory_cache('key2', 'value2')

        assert cache.get_memory_cache_size() == 2

        cache.clear_memory_cache()

        assert cache.get_memory_cache_size() == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache, mock_cache_manager):
        """测试清理过期缓存"""
        # 注入mock manager
        cache._cache_manager = mock_cache_manager
        count = await cache.cleanup_expired()

        assert count == 10
        mock_cache_manager.cleanup_expired.assert_called_once()

    def test_get_cache_size_info(self, cache):
        """测试获取缓存大小信息"""
        cache._set_memory_cache('key1', 'value1')
        cache._set_memory_cache('key2', 'value2')

        assert cache.get_memory_cache_size() == 2
        assert cache.get_memory_cache_max_size() == IN_MEMORY_CACHE_SIZE


# ========== 变化率计算测试 ==========

class TestChangeRateCalculation:
    """变化率计算测试"""

    def test_calculate_change_rate_1d_normal(self):
        """测试正常1日变化率计算"""
        from src.services.strength_service_v2 import StrengthServiceV2

        # 正常增长
        result = StrengthServiceV2.calculate_change_rate_1d(110, 100)
        assert result == 10.0

        # 正常下降
        result = StrengthServiceV2.calculate_change_rate_1d(90, 100)
        assert result == -10.0

    def test_calculate_change_rate_1d_edge_cases(self):
        """测试1日变化率边界情况"""
        from src.services.strength_service_v2 import StrengthServiceV2

        # 当前得分为None
        result = StrengthServiceV2.calculate_change_rate_1d(None, 100)
        assert result is None

        # 前一日得分为None
        result = StrengthServiceV2.calculate_change_rate_1d(100, None)
        assert result is None

        # 前一日得分为0
        result = StrengthServiceV2.calculate_change_rate_1d(100, 0)
        assert result is None

        # 两者都为0
        result = StrengthServiceV2.calculate_change_rate_1d(0, 0)
        assert result is None

    def test_calculate_change_rate_5d_normal(self):
        """测试正常5日变化率计算"""
        from src.services.strength_service_v2 import StrengthServiceV2

        # 平均增长
        current = 110
        scores_5d = [100, 102, 104, 106, 108]  # 平均104
        result = StrengthServiceV2.calculate_change_rate_5d(current, scores_5d)
        expected = round(((110 - 104) / 104) * 100, 2)
        assert result == expected

    def test_calculate_change_rate_5d_with_nulls(self):
        """测试5日变化率含空值情况"""
        from src.services.strength_service_v2 import StrengthServiceV2

        current = 110
        scores_5d = [100, None, 104, None, 108]  # 有效值：100, 104, 108，平均104
        result = StrengthServiceV2.calculate_change_rate_5d(current, scores_5d)
        expected = round(((110 - 104) / 104) * 100, 2)
        assert result == expected

    def test_calculate_change_rate_5d_edge_cases(self):
        """测试5日变化率边界情况"""
        from src.services.strength_service_v2 import StrengthServiceV2

        # 当前得分为None
        result = StrengthServiceV2.calculate_change_rate_5d(None, [100, 102, 104])
        assert result is None

        # 空列表
        result = StrengthServiceV2.calculate_change_rate_5d(100, [])
        assert result is None

        # 全为None
        result = StrengthServiceV2.calculate_change_rate_5d(100, [None, None, None])
        assert result is None

        # 平均为0
        result = StrengthServiceV2.calculate_change_rate_5d(100, [0, 0, 0])
        assert result is None


# 常量引用
IN_MEMORY_CACHE_SIZE = 1000
