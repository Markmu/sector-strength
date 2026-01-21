"""
错误处理测试

测试自定义异常类和全局异常处理器
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions.classification import (
    ClassificationError,
    MissingMADataError,
    ClassificationFailedError,
    InvalidPriceError
)
from main import app


class TestClassificationError:
    """测试 ClassificationError 基类"""

    def test_classification_error_init(self):
        """测试 ClassificationError 初始化"""
        error = ClassificationError(
            message="测试错误",
            code="TEST_ERROR",
            sector_id=1,
            sector_name="测试板块"
        )

        assert error.message == "测试错误"
        assert error.code == "TEST_ERROR"
        assert error.sector_id == 1
        assert error.sector_name == "测试板块"

    def test_classification_error_to_dict(self):
        """测试 to_dict 方法"""
        error = ClassificationError(
            message="测试错误",
            code="TEST_ERROR",
            sector_id=1,
            sector_name="测试板块"
        )

        result = error.to_dict()

        assert result == {
            "code": "TEST_ERROR",
            "message": "测试错误",
            "sector_id": 1,
            "sector_name": "测试板块"
        }


class TestMissingMADataError:
    """测试 MissingMADataError 异常"""

    def test_missing_ma_data_error_basic(self):
        """测试基本均线数据缺失异常"""
        error = MissingMADataError(
            sector_id=1,
            sector_name="测试板块"
        )

        assert error.code == "MISSING_MA_DATA"
        assert "均线数据缺失" in error.message
        assert error.sector_id == 1
        assert error.sector_name == "测试板块"

    def test_missing_ma_data_error_with_missing_fields(self):
        """测试带缺失字段信息的异常"""
        error = MissingMADataError(
            sector_id=1,
            sector_name="测试板块",
            missing_fields=["ma_5", "ma_10"]
        )

        assert error.code == "MISSING_MA_DATA"
        assert "缺失字段: ma_5, ma_10" in error.message
        assert error.missing_fields == ["ma_5", "ma_10"]

    def test_missing_ma_data_error_to_dict(self):
        """测试 to_dict 方法包含缺失字段"""
        error = MissingMADataError(
            sector_id=1,
            sector_name="测试板块",
            missing_fields=["ma_5", "ma_10"]
        )

        result = error.to_dict()

        assert result["code"] == "MISSING_MA_DATA"
        assert "缺失字段" in result["message"]
        assert result["sector_id"] == 1
        assert result["sector_name"] == "测试板块"


class TestClassificationFailedError:
    """测试 ClassificationFailedError 异常"""

    def test_classification_failed_error_basic(self):
        """测试基本分类失败异常"""
        error = ClassificationFailedError(
            sector_id=1,
            sector_name="测试板块"
        )

        assert error.code == "CLASSIFICATION_FAILED"
        assert "分类计算失败" in error.message
        assert error.sector_id == 1
        assert error.sector_name == "测试板块"

    def test_classification_failed_error_with_reason(self):
        """测试带失败原因的异常"""
        error = ClassificationFailedError(
            sector_id=1,
            sector_name="测试板块",
            reason="价格数据为空"
        )

        assert error.code == "CLASSIFICATION_FAILED"
        assert "价格数据为空" in error.message
        assert error.reason == "价格数据为空"


class TestInvalidPriceError:
    """测试 InvalidPriceError 异常"""

    def test_invalid_price_error_basic(self):
        """测试基本价格无效异常"""
        error = InvalidPriceError(
            sector_id=1,
            sector_name="测试板块"
        )

        assert error.code == "INVALID_PRICE"
        assert "价格数据无效" in error.message
        assert error.sector_id == 1
        assert error.sector_name == "测试板块"

    def test_invalid_price_error_with_reason(self):
        """测试带原因的价格无效异常"""
        error = InvalidPriceError(
            sector_id=1,
            sector_name="测试板块",
            reason="价格为负数"
        )

        assert error.code == "INVALID_PRICE"
        assert "价格为负数" in error.message
        assert error.reason == "价格为负数"


class TestAPIErrorResponses:
    """测试 API 错误响应格式"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_401_response_format(self, client):
        """测试 401 未认证响应格式 - 项目使用自定义错误格式"""
        response = client.get("/api/v1/sector-classifications")

        assert response.status_code == 401

        error_data = response.json()
        # 项目使用自定义错误格式：{'error': {'message': ..., 'status_code': ..., 'type': ...}}
        assert "error" in error_data
        assert "message" in error_data["error"]
        assert "status_code" in error_data["error"]

    def test_classification_error_handler_registered(self, client):
        """测试分类异常处理器已正确注册"""
        from src.api.v1.error_handlers import classification_error_handler
        from src.api.v1.error_handlers import register_classification_exception_handlers

        # 确保函数存在且可调用
        assert callable(classification_error_handler)
        assert callable(register_classification_exception_handlers)

    def test_standard_error_response_format(self):
        """测试标准错误响应格式包含所有必需字段"""
        from src.exceptions.classification import MissingMADataError

        error = MissingMADataError(
            sector_id=1,
            sector_name="测试板块",
            missing_fields=["ma_5"]
        )

        # 验证异常包含所有必需字段
        assert hasattr(error, 'code')
        assert hasattr(error, 'message')
        assert error.code == "MISSING_MA_DATA"
        assert error.message is not None

        # 验证 to_dict 方法返回正确格式
        error_dict = error.to_dict()
        assert "code" in error_dict
        assert "message" in error_dict
        assert "sector_id" in error_dict


class TestErrorHandlers:
    """测试异常处理器函数"""

    def test_classification_error_handler_registers(self):
        """测试分类异常处理器已注册"""
        from src.api.v1.error_handlers import classification_error_handler
        from src.api.v1.error_handlers import register_classification_exception_handlers

        # 确保函数存在
        assert callable(classification_error_handler)
        assert callable(register_classification_exception_handlers)

    def test_sqlalchemy_error_handler_registers(self):
        """测试数据库异常处理器已注册"""
        from src.api.v1.error_handlers import sqlalchemy_error_handler

        # 确保函数存在
        assert callable(sqlalchemy_error_handler)


class TestErrorMessages:
    """测试错误消息中文显示"""

    def test_missing_ma_data_error_chinese_message(self):
        """测试均线数据缺失错误使用中文"""
        error = MissingMADataError(
            sector_id=1,
            sector_name="科技板块"
        )

        assert "均线数据缺失" in error.message
        assert "科技板块" in error.message

    def test_classification_failed_error_chinese_message(self):
        """测试分类失败错误使用中文"""
        error = ClassificationFailedError(
            sector_id=1,
            sector_name="科技板块",
            reason="数据不足"
        )

        assert "分类计算失败" in error.message
        assert "科技板块" in error.message
        assert "数据不足" in error.message

    def test_invalid_price_error_chinese_message(self):
        """测试价格无效错误使用中文"""
        error = InvalidPriceError(
            sector_id=1,
            sector_name="科技板块",
            reason="价格为空"
        )

        assert "价格数据无效" in error.message
        assert "科技板块" in error.message
        assert "价格为空" in error.message


class TestErrorInheritance:
    """测试异常继承关系"""

    def test_all_errors_inherit_from_classification_error(self):
        """测试所有异常都继承自 ClassificationError"""
        missing_ma_error = MissingMADataError(sector_id=1)
        classification_failed_error = ClassificationFailedError(sector_id=1)
        invalid_price_error = InvalidPriceError(sector_id=1)

        assert isinstance(missing_ma_error, ClassificationError)
        assert isinstance(classification_failed_error, ClassificationError)
        assert isinstance(invalid_price_error, ClassificationError)

    def test_all_errors_are_exceptions(self):
        """测试所有异常都是 Exception 实例"""
        errors = [
            ClassificationError(message="测试", code="TEST"),
            MissingMADataError(sector_id=1),
            ClassificationFailedError(sector_id=1),
            InvalidPriceError(sector_id=1)
        ]

        for error in errors:
            assert isinstance(error, Exception)
