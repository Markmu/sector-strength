"""
异常处理器测试

验证数据库异常处理器与注册函数可用。
（原 classification 相关测试随板块强弱分类功能一并移除。）
"""

from src.api.v1.error_handlers import (
    sqlalchemy_error_handler,
    register_exception_handlers,
)


def test_sqlalchemy_error_handler_exists():
    """测试数据库异常处理器函数存在且可调用"""
    assert callable(sqlalchemy_error_handler)


def test_register_exception_handlers_exists():
    """测试异常处理器注册函数存在且可调用"""
    assert callable(register_exception_handlers)
