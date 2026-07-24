"""统一出参日志中间件

纯 ASGI 实现，在 send_wrapper 中拦截响应体，对每个 HTTP 请求打印一条 access log：
    METHOD path -> status duration_ms resp=<出参(截断+脱敏)>

同时维护请求级 trace_id（contextvars），供 logging_config 的 TraceIdFilter 注入，
使业务层 logger.exception 等与 access log 串联。

设计要点：
- 沿用项目既有 ProcessTimeMiddleware 的纯 ASGI 范式，避免 BaseHTTPMiddleware
  的事件循环冲突（见 main.py 注释）。
- 大响应体双保险：累加阶段设 max_body_bytes*8 硬上限防内存爆炸，组装阶段再按
  max_body_bytes 截断/摘要。
- json.dumps(..., default=str) 处理 Decimal/datetime（项目无统一序列化器）。
- try/finally 保证异常路径也能打出 status_code 与耗时（异常已被 handler 转成
  JSONResponse，中间件照常捕获）。
"""
import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Iterable, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 请求级上下文：trace_id
# ---------------------------------------------------------------------------
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    """生成 8 位短 trace_id"""
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# 脱敏
# ---------------------------------------------------------------------------
# 始终脱敏的敏感字段（小写匹配 key）
SENSITIVE_KEYS: Set[str] = {
    "access_token",
    "refresh_token",
    "token",
    "password",
    "password_hash",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "authorization",
}
# 受 mask_pii 开关控制的 PII 字段
PII_KEYS: Set[str] = {"email", "phone", "mobile"}


def mask_sensitive(obj: Any, mask_pii: bool = True) -> Any:
    """递归脱敏 dict/list 中的敏感字段，值替换为 '***'。

    dict 的 key 按小写匹配；list 逐元素递归；其他类型原样返回。
    """
    if isinstance(obj, dict):
        masked: dict = {}
        for k, v in obj.items():
            key_lower = k.lower() if isinstance(k, str) else k
            if key_lower in SENSITIVE_KEYS:
                masked[k] = "***"
            elif mask_pii and key_lower in PII_KEYS:
                masked[k] = "***"
            else:
                masked[k] = mask_sensitive(v, mask_pii)
        return masked
    if isinstance(obj, list):
        return [mask_sensitive(x, mask_pii) for x in obj]
    return obj


# ---------------------------------------------------------------------------
# 截断 / 摘要
# ---------------------------------------------------------------------------
def summarize_body(body_str: str, max_bytes: int) -> str:
    """超长响应体截断。

    优先尝试 json 解析后对深层 list 做摘要（_total + _preview 前 3 条），
    再按 max_bytes 截断并追加 (...truncated, N bytes) 标记；非 JSON 则直接按字节截断。
    """
    if len(body_str) <= max_bytes:
        return body_str
    # 尝试结构化摘要
    try:
        data = json.loads(body_str)
    except (ValueError, TypeError):
        return body_str[:max_bytes] + f"...(truncated, {len(body_str)} bytes)"

    def _trim(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: _trim(v) for k, v in node.items()}
        if isinstance(node, list):
            return {"_total": len(node), "_preview": node[:3]}
        return node

    trimmed = json.dumps(_trim(data), ensure_ascii=False, default=str)
    if len(trimmed) <= max_bytes:
        return trimmed
    return trimmed[:max_bytes] + f"...(truncated, {len(body_str)} bytes)"


# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------
DEFAULT_EXCLUDE_PATHS: Tuple[str, ...] = (
    "/",
    "/health",
    "/health/db",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/openapi.json",
)

logger = logging.getLogger("api.access")


class ResponseLoggingMiddleware:
    """统一出参日志 ASGI 中间件。

    用法::

        app = ResponseLoggingMiddleware(ProcessTimeMiddleware(app))

    即放在洋葱圈最外层（最先收到请求、最后拿到完整响应体）。
    """

    def __init__(
        self,
        app,
        *,
        max_body_bytes: int = 2048,
        mask_pii: bool = True,
        exclude_paths: Optional[Iterable[str]] = None,
        skip_paths: Optional[Iterable[str]] = None,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.mask_pii = mask_pii
        # 累加阶段的硬上限：超过则不再缓存 body，仅记 truncated 标记（防内存爆炸）
        self._collect_limit = max_body_bytes * 8
        excludes = set(exclude_paths) if exclude_paths is not None else set(DEFAULT_EXCLUDE_PATHS)
        self.exclude_paths: Set[str] = excludes | set(skip_paths or [])

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "")

        # 注入 trace_id，使本请求内所有日志（含业务层）可串联
        tid = new_trace_id()
        token = trace_id_var.set(tid)
        start_time = time.time()

        # 健康检查 / 文档路径不打 access log
        if path in self.exclude_paths:
            try:
                await self.app(scope, receive, send)
            finally:
                trace_id_var.reset(token)
            return

        status_code: Optional[int] = None
        body_chunks: List[bytes] = []
        body_total = 0
        truncated = False

        async def send_wrapper(message):
            nonlocal status_code, body_total, truncated
            mtype = message.get("type")
            if mtype == "http.response.start":
                status_code = message.get("status", 0)
            elif mtype == "http.response.body":
                chunk = message.get("body", b"") or b""
                if not truncated and body_total + len(chunk) <= self._collect_limit:
                    body_chunks.append(chunk)
                    body_total += len(chunk)
                else:
                    truncated = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            try:
                duration_ms = (time.time() - start_time) * 1000
                resp_repr = self._render_body(body_chunks, body_total, truncated)
                logger.info(
                    "%s %s -> %s %.1fms resp=%s",
                    method,
                    path,
                    status_code,
                    duration_ms,
                    resp_repr,
                )
            except Exception:  # noqa: BLE001 日志本身绝不能影响请求
                logger.debug("access log render failed", exc_info=True)
            trace_id_var.reset(token)

    def _render_body(
        self, body_chunks: List[bytes], body_total: int, truncated: bool
    ) -> str:
        """把缓存到的响应体渲染为日志友好的字符串。"""
        if truncated:
            return f"<large response, {body_total}+ bytes, truncated>"
        if not body_chunks:
            return "<empty>"
        raw = b"".join(body_chunks).decode("utf-8", errors="replace")
        # 尝试 JSON 路径：解析 → 脱敏 → 重新序列化（default=str 防 Decimal/datetime）
        try:
            parsed = json.loads(raw)
            masked = mask_sensitive(parsed, self.mask_pii)
            rendered = json.dumps(masked, ensure_ascii=False, default=str)
        except (ValueError, TypeError):
            rendered = raw  # 非 JSON，原样（后续按字节截断）
        return summarize_body(rendered, self.max_body_bytes)
