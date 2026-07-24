"""统一出参日志中间件单元测试

直接构造最小 ASGI app 验证 ResponseLoggingMiddleware 的行为，
不依赖数据库/认证，覆盖：正常响应、大响应截断、敏感字段脱敏、
异常状态码、跳过路径，以及纯函数（mask_sensitive / summarize_body）。
"""
import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.middleware import response_logging as rl
from src.core.middleware.response_logging import (
    ResponseLoggingMiddleware,
    mask_sensitive,
    summarize_body,
    trace_id_var,
)

ACCESS_LOGGER = "api.access"


def _asgi_app(status: int = 200, body: bytes = b"", headers=None):
    """构造一个最小 ASGI app，固定返回 status + body。"""

    async def app(scope, receive, send):
        hdrs = headers or [(b"content-type", b"application/json")]
        await send({"type": "http.response.start", "status": status, "headers": hdrs})
        await send({"type": "http.response.body", "body": body})

    return app


def _wrap(app, **kw):
    return ResponseLoggingMiddleware(app, **kw)


class _MemoryHandler(logging.Handler):
    """捕获指定 logger 的所有记录，供断言读取。"""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: list = []

    def emit(self, record):
        self.records.append(record)

    def text(self) -> str:
        return "\n".join(rec.getMessage() for rec in self.records)


@pytest.fixture
def access_caplog():
    """直接给 api.access logger 挂内存 handler，避免与 caplog 的传播机制耦合。"""
    lg = logging.getLogger(ACCESS_LOGGER)
    prev_level = lg.level
    prev_propagate = lg.propagate
    handler = _MemoryHandler()
    lg.addHandler(handler)
    lg.setLevel(logging.INFO)
    lg.propagate = False  # 隔离，避免污染其它测试/caplog
    try:
        yield handler
    finally:
        lg.removeHandler(handler)
        lg.setLevel(prev_level)
        lg.propagate = prev_propagate


def _access_text(handler) -> str:
    return handler.text()


# ---------------------------------------------------------------------------
# 纯函数
# ---------------------------------------------------------------------------
class TestMaskSensitive:
    def test_masks_token_and_password(self):
        data = {"access_token": "abc", "refresh_token": "xyz", "ok": 1}
        masked = mask_sensitive(data, mask_pii=False)
        assert masked["access_token"] == "***"
        assert masked["refresh_token"] == "***"
        assert masked["ok"] == 1

    def test_password_key_always_masked(self):
        assert mask_sensitive({"password": "p"}, mask_pii=False)["password"] == "***"

    def test_pii_governed_by_flag(self):
        assert mask_sensitive({"email": "a@b.c"}, mask_pii=True)["email"] == "***"
        assert mask_sensitive({"email": "a@b.c"}, mask_pii=False)["email"] == "a@b.c"

    def test_nested_list_and_dict(self):
        data = {"items": [{"api_key": "k1"}, {"email": "x@y.z"}]}
        masked = mask_sensitive(data, mask_pii=True)
        assert masked["items"][0]["api_key"] == "***"
        assert masked["items"][1]["email"] == "***"

    def test_case_insensitive_key(self):
        # 实际字段名带下划线（access_token），大小写不敏感匹配其小写形式
        assert mask_sensitive({"ACCESS_TOKEN": "t"}, mask_pii=False)["ACCESS_TOKEN"] == "***"
        assert mask_sensitive({"Refresh_Token": "t"}, mask_pii=False)["Refresh_Token"] == "***"


class TestSummarizeBody:
    def test_short_body_unchanged(self):
        assert summarize_body("hello", 100) == "hello"

    def test_long_non_json_truncated(self):
        out = summarize_body("x" * 500, 10)
        assert out.startswith("x" * 10)
        assert "truncated" in out

    def test_long_json_list_summarized(self):
        data = {"data": {"items": [{"i": n} for n in range(100)]}}
        out = summarize_body(json.dumps(data), 200)
        # 列表被摘要为 _total + _preview，且总数正确
        assert "_total" in out and "100" in out
        assert len(out) <= 200 or out.endswith("bytes)")


# ---------------------------------------------------------------------------
# 中间件行为（ASGI 端到端）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestMiddlewareBehavior:
    async def test_normal_response_logged(self, access_caplog):
        body = json.dumps({"success": True, "data": {"id": 1}}).encode()
        app = _wrap(_asgi_app(200, body))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            resp = await ac.get("/api/v1/foo")
        assert resp.status_code == 200
        text = _access_text(access_caplog)
        assert "GET /api/v1/foo" in text
        assert "-> 200" in text
        assert "resp=" in text
        assert "\"id\": 1" in text  # 出参被打出

    async def test_sensitive_fields_masked(self, access_caplog):
        body = json.dumps(
            {"access_token": "super-secret", "data": {"email": "u@e.com"}}
        ).encode()
        app = _wrap(_asgi_app(200, body))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            await ac.post("/api/v1/auth/login")
        text = _access_text(access_caplog)
        assert "super-secret" not in text
        assert "***" in text
        # token 始终脱敏，email 受 mask_pii=True 也脱敏
        assert "u@e.com" not in text

    async def test_email_kept_when_pii_disabled(self, access_caplog):
        body = json.dumps({"email": "keep@me.com", "token": "t"}).encode()
        app = _wrap(_asgi_app(200, body), mask_pii=False)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            await ac.get("/api/v1/profile")
        text = _access_text(access_caplog)
        assert "keep@me.com" in text  # PII 关闭，保留
        assert "***" in text  # token 仍脱敏

    async def test_large_response_truncated(self, access_caplog):
        big = json.dumps({"items": [{"i": n, "name": "x" * 50} for n in range(200)]}).encode()
        app = _wrap(_asgi_app(200, big), max_body_bytes=300)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            resp = await ac.get("/api/v1/sector-fund-flow/rankings")
        assert resp.status_code == 200
        text = _access_text(access_caplog)
        assert "resp=" in text
        # 截断后单条日志不应过长（远小于完整响应）
        line = [ln for ln in text.splitlines() if "rankings" in ln][0]
        assert len(line) < len(big)

    async def test_error_status_still_logged(self, access_caplog):
        body = json.dumps({"success": False, "error": "boom"}).encode()
        app = _wrap(_asgi_app(500, body))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            resp = await ac.get("/api/v1/maybe-fail")
        assert resp.status_code == 500
        text = _access_text(access_caplog)
        assert "-> 500" in text
        assert "boom" in text

    async def test_excluded_path_not_logged(self, access_caplog):
        app = _wrap(_asgi_app(200, b'{"status":"ok"}'))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            await ac.get("/health")
        assert "/health" not in _access_text(access_caplog)

    async def test_custom_skip_path(self, access_caplog):
        app = _wrap(_asgi_app(200, b'{}'), skip_paths={"/metrics"})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            await ac.get("/metrics")
        assert "/metrics" not in _access_text(access_caplog)

    async def test_trace_id_set_during_request(self):
        """请求期间 contextvars trace_id 被设置；结束后被 reset。"""
        captured = {}

        async def inner(scope, receive, send):
            captured["tid_in_request"] = trace_id_var.get()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})

        app = _wrap(inner)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            await ac.get("/api/v1/x")
        assert captured["tid_in_request"] != "-"
        assert len(captured["tid_in_request"]) == 8
        # 请求结束后 reset 回默认
        assert trace_id_var.get() == "-"

    async def test_exception_in_app_does_not_break_logging_and_propagates(self, access_caplog):
        """app 抛异常时，中间件仍应打日志，且异常向上传播。"""

        async def boom(scope, receive, send):
            raise RuntimeError("asgi exploded")

        app = _wrap(boom)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            with pytest.raises(Exception):
                await ac.get("/api/v1/boom")
        # finally 块仍应输出 access log（status 为 None）
        assert "/api/v1/boom" in _access_text(access_caplog)
