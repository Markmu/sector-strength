"""统一日志初始化

收敛原本散落在 main.py 与 email_queue.py 的 logging.basicConfig 调用，
通过 dictConfig 提供单一初始化点，并：

- 注入 trace_id 字段（由 TraceIdFilter 从 contextvars 取值），使所有 logger
  输出的日志都带 [trace_id]，业务层日志与 access log 可串联。
- 补齐缺失的 FileHandler（settings.LOG_FILE 之前配置了但未启用），使用
  RotatingFileHandler 防止日志文件无限增长。
- 保留原有控制台输出与人类可读格式。

注意：本模块被 main.py 在最早阶段调用，import 链上不要触发业务模块的副作用。
"""
import logging
import logging.config
import os
from typing import Optional

from .middleware.response_logging import trace_id_var


class TraceIdFilter(logging.Filter):
    """把 contextvars 里的 trace_id 注入到每条 LogRecord 上。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


_DEFAULT_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s"
)


def setup_logging(level: str = "DEBUG", log_file: Optional[str] = None) -> None:
    """初始化全局日志配置。

    Args:
        level: 日志级别字符串（DEBUG/INFO/WARNING/...），不区分大小写。
        log_file: 日志文件路径；为空或所在目录不可写则仅保留控制台输出。
    """
    # 规范化级别（容错：非法值回落到 INFO）
    lvl = str(level).upper()
    if not hasattr(logging, lvl):
        lvl = "INFO"
    numeric_level = getattr(logging, lvl)

    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["trace_id"],
        }
    }

    use_file = False
    if log_file:
        log_dir = os.path.dirname(log_file)
        try:
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            # 触发一次可写性检查（RotatingFileHandler 延迟到首次 emit 才打开文件）
            file_dir = log_dir if log_dir else "."
            test_path = os.path.join(file_dir, ".log_writable_test")
            with open(test_path, "a", encoding="utf-8"):
                pass
            os.remove(test_path)
            use_file = True
        except OSError:
            # 目录不可写（如只读容器、权限受限）时安全降级为仅控制台
            use_file = False

    if use_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "default",
            "filters": ["trace_id"],
        }

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "trace_id": {"()": TraceIdFilter},
        },
        "formatters": {
            "default": {"format": _DEFAULT_FORMAT},
        },
        "handlers": handlers,
        "root": {
            "level": numeric_level,
            "handlers": list(handlers.keys()),
        },
    }
    logging.config.dictConfig(config)
