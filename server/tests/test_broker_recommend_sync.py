"""
券商月度金股数据同步（plan-01）pytest 测试 — RED 阶段

对应 plan-01 §5 验收标准（AC-08 a~f）+「执行验证」（AC-08-execute-1~4）+
「构建与类型」（import 校验 / pytest 不回归）。

本功能为纯后端数据同步 task handler（无前端 UI），E2E 形态为 pytest
（参照 MEMORY「后端 FEAT E2E 适配 pytest」+ server/tests/test_fund_admin_api.py、
test_task_system.py 既有范式 + conftest.py 的 test_session/admin_client fixture）。

RED 阶段原则（参照 server/tests/test_fund_crowd_api.py red 证据范式）：
- 测试只针对「尚未实现的真实功能」断言：BrokerRecommend 模型、
  TaskType.SYNC_BROKER_RECOMMEND、sync_broker_recommend_task handler、
  BrokerRecommendDataInitService.sync_broker_recommend、
  TushareDataSource.get_broker_recommend、admin 路由 POST /api/v1/admin/init/broker-recommend。
- 失败原因必须是「目标功能尚未实现」（ImportError / AttributeError / 404），
  而不是测试自身错误或环境错误。
- 断言强度不放宽：实现后跑同一组用例应全部通过。
"""

import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from main import app
from src.models.user import User
from src.api.deps import get_current_user, get_session
from src.services.task_executor import TaskRegistry

# app 被 ProcessTimeMiddleware 包装，需要获取底层 FastAPI 实例
_fastapi_app = app.app if hasattr(app, "app") else app


# ============== AC-08a：BrokerRecommend 模型字段与索引齐全 ==============


class TestBrokerRecommendModel:
    """AC-08a — BrokerRecommend 模型字段/索引齐全（month=该月第一天 Date）。

    来源：plan-01 §5 AC-08a、§实现规格 #1。
    red 预期：ImportError（server/src/models/broker_recommend.py 尚未创建）。
    """

    def test_model_importable(self):
        """BrokerRecommend 可从 src.models 导出"""
        from src.models import BrokerRecommend
        assert BrokerRecommend is not None

    def test_model_tablename(self):
        """表名 = broker_recommend"""
        from src.models import BrokerRecommend
        assert BrokerRecommend.__tablename__ == "broker_recommend"

    def test_model_required_fields_exist(self):
        """必要字段齐全：id/month/trade_date/ts_code/symbol/broker/name/reason/created_at/updated_at"""
        from src.models import BrokerRecommend
        cols = {c.name for c in BrokerRecommend.__table__.columns}
        required = {
            "id", "month", "trade_date", "ts_code", "symbol",
            "broker", "name", "reason", "created_at", "updated_at",
        }
        missing = required - cols
        assert not missing, f"BrokerRecommend 缺少字段: {missing}"

    def test_model_indexes_present(self):
        """3 个索引：(symbol, month) + (broker, month) + (month)"""
        from src.models import BrokerRecommend
        index_names = {idx.name for idx in BrokerRecommend.__table__.indexes}
        assert "ix_broker_symbol_month" in index_names
        assert "ix_broker_broker_month" in index_names
        assert "ix_broker_month" in index_names

    def test_month_and_trade_date_are_date_type(self):
        """month 与 trade_date 均为 Date 类型（month=该月第一天，区别于 trade_date）"""
        from sqlalchemy import Date
        from src.models import BrokerRecommend
        assert isinstance(BrokerRecommend.__table__.c.month.type, Date)
        assert isinstance(BrokerRecommend.__table__.c.trade_date.type, Date)


# ============== AC-08c：TaskType.SYNC_BROKER_RECOMMEND 枚举 + handler 注册 ==============


class TestTaskRegistration:
    """AC-08c — TaskType.SYNC_BROKER_RECOMMEND 存在且 handler 被 TaskRegistry.register 注册。

    来源：plan-01 §5 AC-08c、§实现规格 #5。
    red 预期：AttributeError（枚举成员不存在）/ handler 未注册（get_handler 返回 None）。
    """

    def test_task_type_enum_exists(self):
        """TaskType.SYNC_BROKER_RECOMMEND 在枚举中存在"""
        from src.services.task_handlers import TaskType
        assert hasattr(TaskType, "SYNC_BROKER_RECOMMEND")
        assert TaskType.SYNC_BROKER_RECOMMEND.value == "sync_broker_recommend"

    def test_handler_registered(self):
        """sync_broker_recommend handler 已被 TaskRegistry.register 注册"""
        registered = TaskRegistry.list_registered_tasks()
        assert "sync_broker_recommend" in registered
        handler = TaskRegistry.get_handler("sync_broker_recommend")
        assert handler is not None
        assert callable(handler)


# ============== AC-08d：Tushare 客户端 get_broker_recommend(month) ==============


class TestTushareClientExtension:
    """AC-08d — TushareDataSource.get_broker_recommend(month)（接口原生支持 month 入参）。

    来源：plan-01 §5 AC-08d、§实现规格 #3。
    red 预期：AttributeError（TushareDataSource 无 get_broker_recommend 方法）。
    """

    def test_method_exists(self):
        """TushareDataSource 拥有 get_broker_recommend 方法"""
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert hasattr(TushareDataSource, "get_broker_recommend")

    def test_method_is_coroutine(self):
        """get_broker_recommend 是 async 方法"""
        import inspect
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert inspect.iscoroutinefunction(TushareDataSource.get_broker_recommend)


# ============== AC-08b / AC-08-execute-1：admin 同步 API ==============


# ---- User fixtures（参照 test_fund_admin_api.py）----


@pytest_asyncio.fixture
async def admin_user(test_session):
    user = User(
        email="admin_broker@example.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(test_session):
    user = User(
        email="user_broker@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, test_session, admin_user):
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return admin_user

    _fastapi_app.dependency_overrides[get_session] = _override_get_session
    _fastapi_app.dependency_overrides[get_current_user] = _override_current_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def normal_client(client: AsyncClient, test_session, normal_user):
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return normal_user

    _fastapi_app.dependency_overrides[get_session] = _override_get_session
    _fastapi_app.dependency_overrides[get_current_user] = _override_current_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
def mock_task_manager():
    """Mock TaskManager 类（init_broker_recommend.py 中延迟导入）"""
    mock_task = MagicMock()
    mock_task.task_id = "task_broker_test_001"

    mock_instance = MagicMock()
    mock_instance.create_task = AsyncMock(return_value=mock_task)

    with patch("src.services.task_manager.TaskManager", return_value=mock_instance):
        yield mock_instance


@pytest_asyncio.fixture
async def running_broker_recommend_task(test_session):
    """预置一个 running 状态的 SYNC_BROKER_RECOMMEND 任务（并发保护测试用）"""
    from src.models.async_task import AsyncTask
    from src.services.task_handlers import TaskType

    task = AsyncTask(
        task_id="task_existing_broker",
        task_type=TaskType.SYNC_BROKER_RECOMMEND.value,
        status="running",
    )
    test_session.add(task)
    await test_session.commit()
    yield task


class TestAdminInitBrokerRecommend:
    """AC-08b / AC-08-execute-1 — POST /api/v1/admin/init/broker-recommend。

    来源：plan-01 §5 AC-08b、AC-08-execute-1、§实现规格 #6。
    red 预期：路由未注册 → 404 Not Found（参照 08 plan-01 red 范式）。
    """

    @pytest.mark.asyncio
    async def test_init_success_returns_task_id(self, admin_client, mock_task_manager):
        """管理员触发同步 → success=true, data.task_id 非空（AC-08b / execute-1）"""
        resp = await admin_client.post(
            "/api/v1/admin/init/broker-recommend",
            json={"month": "202605"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["task_id"] is not None
        # 验证 create_task 用了正确 task_type 与 params
        mock_task_manager.create_task.assert_called_once()
        call_kwargs = mock_task_manager.create_task.call_args[1]
        assert call_kwargs["task_type"] == "sync_broker_recommend"
        assert call_kwargs["params"] == {"month": "202605"}

    @pytest.mark.asyncio
    async def test_init_concurrent_protection(
        self, admin_client, admin_user, running_broker_recommend_task
    ):
        """已有同类 running 任务 → success=false 并发保护提示（AC-08b）"""
        resp = await admin_client.post(
            "/api/v1/admin/init/broker-recommend",
            json={"month": "202605"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["data"] is None
        assert "运行" in body["message"]

    @pytest.mark.asyncio
    async def test_init_rejects_invalid_month_format(self, admin_client):
        """month 格式校验：非 6 位数字 → 422（pattern=^\\d{6}$）"""
        resp = await admin_client.post(
            "/api/v1/admin/init/broker-recommend",
            json={"month": "20260501"},  # 8 位应被拒
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_init_requires_admin(self, normal_client):
        """普通用户访问 → 401/403"""
        resp = await normal_client.post(
            "/api/v1/admin/init/broker-recommend",
            json={"month": "202605"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_init_requires_auth(self, client):
        """未认证 → 401"""
        resp = await client.post(
            "/api/v1/admin/init/broker-recommend",
            json={"month": "202605"},
        )
        assert resp.status_code == 401


# ============== AC-08d/e/f + execute-2/3/4：同步服务核心逻辑 ==============


def _make_service():
    """构造 BrokerRecommendDataInitService（session mock，tushare mock 在用例内注入）"""
    from src.services.data_init_broker_recommend import BrokerRecommendDataInitService
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.add_all = MagicMock()
    return BrokerRecommendDataInitService(session), session


def _broker_record(ts_code, trade_date, broker, name=None, reason=None):
    return {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "name": name,
        "broker": broker,
        "reason": reason,
    }


class TestSyncServiceDataWrite:
    """AC-08-execute-2/3 — sync_broker_recommend(month) 写入数据。

    来源：plan-01 §5 AC-08d、execute-2/3、§实现规格 #4。
    red 预期：ImportError（data_init_broker_recommend 模块尚未创建）。
    """

    @pytest.mark.asyncio
    async def test_service_importable(self):
        """BrokerRecommendDataInitService 可导入"""
        service, _ = _make_service()
        assert service is not None
        assert hasattr(service, "sync_broker_recommend")

    @pytest.mark.asyncio
    async def test_writes_records_for_month(self):
        """AC-08-execute-2/3：拉取该月数据后写入 broker_recommend 表（added>0）"""
        service, session = _make_service()
        records = [
            _broker_record("600519.SH", "20260531", "中信证券",
                           name="贵州茅台", reason="业绩稳健"),
            _broker_record("000001.SZ", "20260515", "海通证券",
                           name="平安银行", reason="分红稳定"),
        ]
        service.tushare.get_broker_recommend = AsyncMock(return_value=records)

        result = await service.sync_broker_recommend("202605")

        assert result["added"] == 2
        assert result["failed"] == 0
        # 确认写入发生
        session.add_all.assert_called()

    @pytest.mark.asyncio
    async def test_empty_records_returns_zero(self):
        """接口返回空（该月未发布）→ added=0，任务正常完成"""
        service, _ = _make_service()
        service.tushare.get_broker_recommend = AsyncMock(return_value=[])

        result = await service.sync_broker_recommend("202605")
        assert result["added"] == 0


class TestSyncServiceIdempotency:
    """AC-08e — 先删后写幂等：重复调用同月不堆积。

    来源：plan-01 §5 AC-08e、§实现规格 #4 step 5、边界场景表。
    red 预期：ImportError（service 未创建）。
    """

    @pytest.mark.asyncio
    async def test_delete_before_write(self):
        """先删后写：写入前执行 DELETE WHERE month = :month_date"""
        service, session = _make_service()
        service.tushare.get_broker_recommend = AsyncMock(return_value=[
            _broker_record("600519.SH", "20260531", "中信证券"),
        ])

        await service.sync_broker_recommend("202605")

        # 至少一次 execute 用于 DELETE（先删）
        execute_calls = session.execute.call_args_list
        assert len(execute_calls) >= 1, "应先执行 DELETE 再写入"


class TestSyncServiceDedup:
    """AC-08f — 按 (ts_code, broker) 去重保留最新 trade_date，不堆积。

    来源：plan-01 §5 AC-08f、§实现规格 #4 step 4、边界场景表。
    red 预期：ImportError（service 未创建）。
    """

    @pytest.mark.asyncio
    async def test_dedup_keeps_latest_trade_date(self):
        """同券商对同股当月多次推荐 → 仅保留 trade_date 最新一条"""
        service, session = _make_service()
        # 同 (600519.SH, 中信证券) 推荐两次，trade_date 不同
        records = [
            _broker_record("600519.SH", "20260510", "中信证券", name="贵州茅台"),
            _broker_record("600519.SH", "20260531", "中信证券", name="贵州茅台"),
        ]
        service.tushare.get_broker_recommend = AsyncMock(return_value=records)

        result = await service.sync_broker_recommend("202605")

        # 去重后应只剩 1 条
        assert result["added"] == 1
        add_call = session.add_all.call_args
        written = add_call.args[0] if add_call else []
        assert len(written) == 1
        assert written[0].trade_date == date(2026, 5, 31)

    @pytest.mark.asyncio
    async def test_different_brokers_not_deduped(self):
        """同股不同券商不去重（分别保留）"""
        service, session = _make_service()
        records = [
            _broker_record("600519.SH", "20260531", "中信证券"),
            _broker_record("600519.SH", "20260531", "海通证券"),
        ]
        service.tushare.get_broker_recommend = AsyncMock(return_value=records)

        result = await service.sync_broker_recommend("202605")
        assert result["added"] == 2


class TestParseRecord:
    """AC-08a / execute-3 — _parse_record 字段映射（symbol=纯数字、month=月初）。

    来源：plan-01 §5 AC-08a、execute-3、§实现规格 #4 _parse_record。
    red 预期：ImportError（service 未创建）。
    """

    @pytest.mark.asyncio
    async def test_parse_symbol_is_digits(self):
        """symbol 为 ts_code 的纯数字部分（600519.SH → 600519）"""
        service, _ = _make_service()
        month_date = date(2026, 5, 1)
        rec = _broker_record("600519.SH", "20260531", "中信证券",
                             name="贵州茅台", reason="稳健")
        parsed = service._parse_record(rec, month_date)
        assert parsed is not None
        assert parsed.symbol == "600519"
        assert parsed.ts_code == "600519.SH"

    @pytest.mark.asyncio
    async def test_parse_month_is_first_day(self):
        """month 解析为该月第一天（202605 → 2026-05-01）"""
        service, _ = _make_service()
        month_date = date(2026, 5, 1)
        rec = _broker_record("600519.SH", "20260515", "中信证券")
        parsed = service._parse_record(rec, month_date)
        assert parsed is not None
        assert parsed.month == date(2026, 5, 1)
        assert parsed.trade_date == date(2026, 5, 15)

    @pytest.mark.asyncio
    async def test_parse_missing_broker_returns_none(self):
        """缺失必要字段（broker）→ 返回 None 跳过"""
        service, _ = _make_service()
        month_date = date(2026, 5, 1)
        rec = {"ts_code": "600519.SH", "trade_date": "20260515"}  # 无 broker
        parsed = service._parse_record(rec, month_date)
        assert parsed is None
