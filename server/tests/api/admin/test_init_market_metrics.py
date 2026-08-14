"""市场量价范围同步专用路由测试（第 16 期 plan-05）

覆盖 plan-05 §5 验收标准 AC-10（四类日期校验拒绝且不建任务）、AC-11（require_admin
403 + 互斥拒绝）、合法请求返回 task_id。

tests/api/conftest.py 的 autouse fixture 将 get_current_user 覆盖为 admin，故鉴权默认
通过；403 用例在本测试内再次覆盖为非 admin 用户。
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.deps import get_current_user
from src.models.user import User

ROUTE = "/v1/admin/init/market-metrics"


def _unwrap_fastapi(app_obj):
    """沿 ``.app`` 链解包到持 ``dependency_overrides`` 的 FastAPI 实例。"""
    cur = app_obj
    for _ in range(10):
        if hasattr(cur, "dependency_overrides"):
            return cur
        if hasattr(cur, "app"):
            cur = cur.app
        else:  # pragma: no cover
            break
    return cur


@pytest.fixture
def client():
    return TestClient(app)


def _admin_user():
    return User(
        email="api-test@example.com",
        password_hash="x",
        username="api_test_user",
        is_active=True,
        is_verified=True,
        role="admin",
        permissions=["read", "write", "admin"],
    )


def _non_admin_user():
    return User(
        email="user@example.com",
        password_hash="x",
        username="plain_user",
        is_active=True,
        is_verified=True,
        role="user",
        permissions=["read"],
    )


def _repo_mock(open_count=1, trading_days=None, refresh_raises=False):
    repo = MagicMock()
    if refresh_raises:
        repo.refresh_range = AsyncMock(side_effect=ValueError("日历校验失败"))
    else:
        repo.refresh_range = AsyncMock(return_value=(open_count, 0))
    repo.get_trading_days = AsyncMock(
        return_value=(
            trading_days
            if trading_days is not None
            else [date(2026, 8, 11), date(2026, 8, 12)]
        )
    )
    return repo


class TestInitMarketMetricsRoute:
    """专用路由校验链 / 互斥 / 鉴权测试。"""

    def test_valid_request_creates_task(self, client):
        """合法起止日：返回 task_id（AC-02/AC-11）。"""
        repo = _repo_mock(
            open_count=2, trading_days=[date(2026, 8, 11), date(2026, 8, 12)]
        )
        fake_task = MagicMock()
        fake_task.task_id = "task_abcdef123456"
        with patch(
            "src.api.admin.init_market_metrics.TradingCalendarRepository",
            return_value=repo,
        ), patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
            return_value=fake_task,
        ) as mock_create:
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-11", "end_date": "2026-08-12"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "task_abcdef123456"
        mock_create.assert_awaited_once()

    def test_start_after_end_rejected_no_task(self, client):
        """起止倒置：success=False 且不建任务（AC-10）。"""
        with patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-12", "end_date": "2026-08-11"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "不能晚于结束日期" in data["message"]
        mock_create.assert_not_awaited()

    def test_end_after_today_rejected_no_task(self, client):
        """end>today：success=False 且不建任务（AC-10）。"""
        future = (date.today() + timedelta(days=5)).isoformat()
        today = date.today().isoformat()
        with patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = client.post(
                ROUTE, json={"start_date": today, "end_date": future}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "不能晚于今天" in data["message"]
        mock_create.assert_not_awaited()

    def test_span_over_10_years_rejected_no_task(self, client):
        """跨度>10 年：success=False 且不建任务（AC-10）。"""
        end = date.today()
        start = end - timedelta(days=4000)
        with patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = client.post(
                ROUTE,
                json={"start_date": start.isoformat(), "end_date": end.isoformat()},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "10 年" in data["message"]
        mock_create.assert_not_awaited()

    def test_calendar_refresh_failure_rejected_no_task(self, client):
        """日历刷新失败：success=False 且不建任务（不降级旧行）。"""
        repo = _repo_mock(refresh_raises=True)
        with patch(
            "src.api.admin.init_market_metrics.TradingCalendarRepository",
            return_value=repo,
        ), patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-11", "end_date": "2026-08-12"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "交易日历刷新失败" in data["message"]
        mock_create.assert_not_awaited()

    def test_zero_trading_days_rejected_no_task(self, client):
        """零交易日：success=False 且不建任务（§3.2 分支表）。"""
        repo = _repo_mock(open_count=0, trading_days=[])
        with patch(
            "src.api.admin.init_market_metrics.TradingCalendarRepository",
            return_value=repo,
        ), patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
        ) as mock_create:
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-11", "end_date": "2026-08-12"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "没有交易日" in data["message"]
        mock_create.assert_not_awaited()

    def test_mutex_rejected_when_existing_running(self, client):
        """互斥命中：create_exclusive_task 返回 None → success=False 提示（AC-11）。"""
        repo = _repo_mock(
            open_count=2, trading_days=[date(2026, 8, 11), date(2026, 8, 12)]
        )
        with patch(
            "src.api.admin.init_market_metrics.TradingCalendarRepository",
            return_value=repo,
        ), patch(
            "src.services.task_manager.TaskManager.create_exclusive_task",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-11", "end_date": "2026-08-12"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "正在运行" in data["message"]

    def test_non_admin_returns_403(self, client):
        """非管理员调用专用路由 → 403（AC-11）。"""
        fastapi_app = _unwrap_fastapi(app)
        fastapi_app.dependency_overrides[get_current_user] = _non_admin_user
        try:
            resp = client.post(
                ROUTE,
                json={"start_date": "2026-08-11", "end_date": "2026-08-12"},
            )
        finally:
            # 恢复 conftest autouse 的 admin 覆盖
            fastapi_app.dependency_overrides[get_current_user] = _admin_user
        assert resp.status_code == 403
