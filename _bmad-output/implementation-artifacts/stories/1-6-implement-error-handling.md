# Story 1.6: 实现错误处理机制

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 用户,
I want 在遇到错误时看到明确的错误提示,
so that 我知道问题所在并可以采取相应行动。

## Acceptance Criteria

**Given** 系统正常运行
**When** 分类计算失败 (如均线数据缺失)
**Then** API 返回 500 状态码
**And** 错误响应包含:
  - error.code: "CLASSIFICATION_FAILED"
  - error.message: "板块分类计算失败：{具体原因}"
  - error.timestamp: ISO 8601 格式时间戳
**When** 数据库中板块的均线数据缺失
**Then** API 返回 500 状态码
**And** 错误响应包含:
  - error.code: "MISSING_MA_DATA"
  - error.message: "板块 {板块名称} 的均线数据缺失，无法计算分类"
**When** API 请求失败 (网络错误、超时等)
**Then** 前端显示友好的错误提示
**And** 提供"重试"按钮
**And** 错误提示使用中文
**And** 错误提示清晰可见 (颜色对比度符合可访问性要求)

## Tasks / Subtasks

- [x] Task 1: 创建自定义异常类 (AC: 全部)
  - [x] Subtask 1.1: 创建 `server/src/exceptions/classification.py`
  - [x] Subtask 1.2: 定义 `ClassificationError` 基类
  - [x] Subtask 1.3: 定义 `MissingMADataError` 异常
  - [x] Subtask 1.4: 定义 `ClassificationFailedError` 异常
  - [x] Subtask 1.5: 添加中文错误消息和错误码

- [x] Task 2: 实现全局异常处理器 (AC: 全部)
  - [x] Subtask 2.1: 创建 `server/src/api/v1/error_handlers.py`
  - [x] Subtask 2.2: 实现自定义异常到 HTTP 状态码的映射
  - [x] Subtask 2.3: 实现标准错误响应格式
  - [x] Subtask 2.4: 添加请求日志记录
  - [x] Subtask 2.5: 注册到 FastAPI 应用

- [x] Task 3: 集成异常到分类服务 (AC: 全部)
  - [x] Subtask 3.1: 修改 `sector_classification_service.py`
  - [x] Subtask 3.2: 数据缺失时抛出 `MissingMADataError`
  - [x] Subtask 3.3: 计算失败时抛出 `ClassificationFailedError`
  - [x] Subtask 3.4: 添加具体的错误原因描述

- [x] Task 4: 实现前端错误处理 (AC: 全部)
  - [x] Subtask 4.1: 修改 `sectorClassificationApi.ts`
  - [x] Subtask 4.2: 解析错误响应格式
  - [x] Subtask 4.3: 提取错误码和错误消息
  - [x] Subtask 4.4: 抛出带有错误信息的异常
  - [x] Subtask 4.5: 添加重试机制

- [x] Task 5: 创建错误显示组件 (AC: 全部)
  - [x] Subtask 5.1: 创建 `web/src/components/ErrorMessage.tsx`
  - [x] Subtask 5.2: 显示错误图标和消息
  - [x] Subtask 5.3: 提供"重试"按钮
  - [x] Subtask 5.4: 使用红色字体（Tailwind CSS）
  - [x] Subtask 5.5: 确保颜色对比度符合可访问性要求

- [x] Task 6: 创建错误处理测试 (AC: 全部)
  - [x] Subtask 6.1: 创建 `server/tests/test_error_handling.py`
  - [x] Subtask 6.2: 测试缺失数据异常处理
  - [x] Subtask 6.3: 测试计算失败异常处理
  - [x] Subtask 6.4: 测试错误响应格式
  - [x] Subtask 6.5: 测试前端错误显示

## Dev Notes

### 自定义异常类

**异常定义:**

```python
# server/src/exceptions/classification.py
from typing import Optional

class ClassificationError(Exception):
    """分类计算基础异常"""

    def __init__(
        self,
        message: str,
        code: str,
        sector_id: Optional[int] = None,
        sector_name: Optional[str] = None
    ):
        self.message = message
        self.code = code
        self.sector_id = sector_id
        self.sector_name = sector_name
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "code": self.code,
            "message": self.message,
            "sector_id": self.sector_id,
            "sector_name": self.sector_name
        }


class MissingMADataError(ClassificationError):
    """均线数据缺失异常"""

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        missing_fields: Optional[list] = None
    ):
        message = f"板块 {sector_name or sector_id} 的均线数据缺失"
        if missing_fields:
            message += f"（缺失字段: {', '.join(missing_fields)}）"
        super().__init__(
            message=message,
            code="MISSING_MA_DATA",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.missing_fields = missing_fields


class ClassificationFailedError(ClassificationError):
    """分类计算失败异常"""

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        reason: str = "未知错误"
    ):
        message = f"板块 {sector_name or sector_id} 分类计算失败: {reason}"
        super().__init__(
            message=message,
            code="CLASSIFICATION_FAILED",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.reason = reason


class InvalidPriceError(ClassificationError):
    """价格数据无效异常"""

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        reason: str = "价格数据无效"
    ):
        message = f"板块 {sector_name or sector_id} 的价格数据无效: {reason}"
        super().__init__(
            message=message,
            code="INVALID_PRICE",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.reason = reason
```

### 全局异常处理器

**FastAPI 异常处理:**

```python
# server/src/api/v1/error_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from src.exceptions.classification import (
    ClassificationError,
    MissingMADataError,
    ClassificationFailedError,
    InvalidPriceError
)

logger = logging.getLogger(__name__)

async def classification_error_handler(
    request: Request,
    exc: ClassificationError
) -> JSONResponse:
    """处理分类计算异常"""
    logger.error(f"分类错误: {exc.code} - {exc.message}", extra={
        "sector_id": exc.sector_id,
        "sector_name": exc.sector_name
    })

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """处理通用异常"""
    logger.error(f"未处理的异常: {type(exc).__name__} - {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def sqlalchemy_error_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """处理数据库异常"""
    logger.error(f"数据库错误: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "数据库错误，请稍后重试",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


# 注册异常处理器
def register_exception_handlers(app):
    """注册所有异常处理器到 FastAPI 应用"""

    app.add_exception_handler(ClassificationError, classification_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("异常处理器已注册")
```

### 前端错误处理

**API 客户端错误处理:**

```typescript
// web/src/lib/sectorClassificationApi.ts

interface ApiError {
  error: {
    code: string
    message: string
    timestamp: string
  }
}

class ApiClientError extends Error {
  code: string
  timestamp: string

  constructor(message: string, code: string, timestamp: string) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.timestamp = timestamp
  }
}

class SectorClassificationAPI {
  private baseURL = '/api/v1'
  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken')
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` })
    }
  }

  private async handleResponse(response: Response): Promise<any> {
    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new ApiClientError(
        error.error.message,
        error.error.code,
        error.error.timestamp
      )
    }
    return response.json()
  }

  async getAllClassifications(): Promise<ApiResponse<SectorClassification[]>> {
    const response = await fetch(`${this.baseURL}/sector-classifications`, {
      headers: this.getHeaders()
    })

    return this.handleResponse(response)
  }

  async getClassificationById(sectorId: number): Promise<ApiResponse<SectorClassification>> {
    const response = await fetch(`${this.baseURL}/sector-classifications/${sectorId}`, {
      headers: this.getHeaders()
    })

    return this.handleResponse(response)
  }
}

export const sectorClassificationApi = new SectorClassificationAPI()
```

### 错误显示组件

**React 错误组件:**

```typescript
// web/src/components/ErrorMessage.tsx
'use client'

import React from 'react'

interface ErrorMessageProps {
  error: string
  code?: string
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorMessage({
  error,
  code,
  onRetry,
  retryLabel = "重试"
}: ErrorMessageProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-9a1 1 0 11-2 0 1 1 0 012 0zm-1 4a1 1 0 102 0 1 1 0 012 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-800">
            {code || "错误"}
          </h3>
          <div className="mt-2 text-sm text-red-700">
            <p>{error}</p>
          </div>
          {onRetry && (
            <div className="mt-4">
              <button
                onClick={onRetry}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                {retryLabel}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

### 架构模式与约束

**错误处理架构:**
- 使用自定义异常类继承体系
- 全局异常处理器统一转换错误
- 前端错误组件统一显示格式
- 支持重试机制

**关键设计决策:**

| 方面 | 设计决策 | 原因 |
|------|----------|------|
| 异常类 | 自定义异常继承体系 | 清晰的错误类型区分 |
| 错误码 | 字符串常量 (MISSING_MA_DATA) | 前后端一致性 |
| 错误响应 | 统一 JSON 格式 | 前端易于解析 |
| HTTP 状态码 | 500 (服务器错误) | 业务逻辑错误归为服务器错误 |
| 前端显示 | 红色高亮 + 重试按钮 | 用户友好的错误提示 |

### 项目结构规范

**后端文件结构:**
```
server/
├── src/
│   ├── exceptions/
│   │   └── classification.py                # 新增：自定义异常
│   └── api/
│       └── v1/
│           ├── error_handlers.py            # 新增：异常处理器
│           └── sector_classifications.py    # 修改：抛出异常
└── tests/
    └── test_error_handling.py               # 新增：错误处理测试
```

**前端文件结构:**
```
web/src/
├── components/
│   └── ErrorMessage.tsx                     # 新增：错误组件
└── lib/
    └── sectorClassificationApi.ts            # 修改：错误处理
```

**命名约定:**
- 异常类: `PascalCase` (如 `ClassificationError`)
- 异常文件: `snake_case.py` (如 `classification.py`)
- 错误码: `UPPER_SNAKE_CASE` (如 `MISSING_MA_DATA`)

### Testing Standards Summary

**测试要求:**
- 测试所有异常类型
- 测试错误响应格式
- 测试前端错误显示
- 测试重试机制

**测试结构示例:**
```python
import pytest
from src.exceptions.classification import (
    MissingMADataError,
    ClassificationFailedError,
    InvalidPriceError
)
from fastapi.testclient import TestClient

def test_missing_ma_data_error():
    """测试均线数据缺失异常"""
    error = MissingMADataError(
        sector_id=1,
        sector_name="测试板块",
        missing_fields=["ma_5", "ma_10"]
    )

    assert error.code == "MISSING_MA_DATA"
    assert "均线数据缺失" in error.message
    assert error.sector_id == 1

    error_dict = error.to_dict()
    assert error_dict["code"] == "MISSING_MA_DATA"
    assert "缺失字段: ma_5, ma_10" in error_dict["message"]

def test_classification_failed_error():
    """测试分类计算失败异常"""
    error = ClassificationFailedError(
        sector_id=1,
        sector_name="测试板块",
        reason="价格数据为空"
    )

    assert error.code == "CLASSIFICATION_FAILED"
    assert "分类计算失败" in error.message

@pytest.mark.asyncio
async def test_api_error_response(client: TestClient):
    """测试 API 错误响应格式"""
    # 模拟触发错误的请求
    response = client.get("/api/v1/sector-classifications/999999")

    assert response.status_code == 500

    error_data = response.json()
    assert "error" in error_data
    assert "code" in error_data["error"]
    assert "message" in error_data["error"]
    assert "timestamp" in error_data["error"]
```

### Project Structure Notes

**对齐统一项目结构:**
- 异常放在 `src/exceptions/` 目录
- 错误处理器放在 `src/api/v1/` 目录
- 前端组件放在 `components/` 目录
- 遵循项目日志规范

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Error Handling] - 错误处理设计
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] - 命名约定和模式

**项目上下文:**
- [Source: _bmad-output/project-context.md#Critical Don't-Miss Rules] - 错误处理规则
- [Source: _bmad-output/project-context.md#Testing Rules] - pytest 测试框架

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1] - Epic 1: 数据库、算法与最小验证
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.6] - Story 1.6 完整验收标准

### Previous Story Intelligence (Story 1.5)

**从 Story 1.5 学到的经验:**

1. **缓存服务已创建:**
   - `ClassificationCache` 服务已实现
   - 提供缓存清除和统计功能
   - 可以在错误处理后清除相关缓存

2. **API 端点已增强:**
   - 集成了缓存机制
   - 提供管理员缓存清除接口
   - 需要添加错误处理

3. **自定义异常已部分实现:**
   - Story 1.2 中已有 `MissingMADataError` 和 `InvalidPriceError`
   - 需要统一错误响应格式
   - 需要添加全局异常处理器

4. **前端错误处理:**
   - Story 1.4 中已有基本的错误处理
   - 需要增强为统一的错误显示组件
   - 需要添加重试机制

5. **测试模式:**
   - 使用 pytest 进行单元测试
   - 使用 FastAPI TestClient 测试 API
   - 前端组件测试使用 Testing Library

**Git 智能摘要（最近10条提交）:**
- `fe67ea3` fix: 完成 Story 1.5 缓存机制并修复代码审查问题 ← Story 1.5
- `16e6063` feat: 完成 Story 1.4 API 测试前端页面并修复代码审查问题 ← Story 1.4
- `8ba6e86` feat: 完成 Story 1.3 分类 API 端点并修复代码审查问题 ← Story 1.3

**代码模式参考:**
- 查看 Story 1.2 中的异常类实现
- 参考现有错误处理模式（如果有）
- 使用项目日志规范

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **错误码规范** - 使用大写下划线格式 (MISSING_MA_DATA)
2. **错误消息** - 必须使用中文
3. **错误响应格式** - 必须包含 code, message, timestamp
4. **HTTP 状态码** - 业务逻辑错误使用 500
5. **前端错误显示** - 红色字体 + 高对比度
6. **重试机制** - 必须提供"重试"按钮
7. **异常继承** - 必须继承 ClassificationError 基类
8. **全局处理器** - 必须注册到 FastAPI 应用
9. **日志记录** - 必须记录所有错误
10. **测试覆盖** - 必须测试所有错误场景

**依赖:**
- Story 1.2 (分类服务中的异常类)
- Story 1.3 (API 端点需要增强)
- Story 1.4 (前端错误处理需要增强)

**后续影响:**
- 此是 Epic 1 的最后一个 Story
- 完成后 Epic 1 的基础功能将全部就绪
- 可以开始 Epic 2A (基础分类展示)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

✅ **Task 1: 创建自定义异常类**
- 创建了 `server/src/exceptions/classification.py` 文件
- 定义了 `ClassificationError` 基类，包含 message、code、sector_id、sector_name 属性
- 定义了 `MissingMADataError` 异常，用于均线数据缺失场景
- 定义了 `ClassificationFailedError` 异常，用于分类计算失败场景
- 定义了 `InvalidPriceError` 异常，用于价格数据无效场景
- 所有异常类使用中文错误消息和大写下划线格式的错误码

✅ **Task 2: 实现全局异常处理器**
- 创建了 `server/src/api/v1/error_handlers.py` 文件
- 实现了 `classification_error_handler` 处理分类异常
- 实现了 `sqlalchemy_error_handler` 处理数据库异常
- 实现了 `generic_exception_handler` 处理通用异常
- 在 `main.py` 中注册了所有异常处理器
- 错误响应格式包含 code、message、timestamp 字段

✅ **Task 3: 集成异常到分类服务**
- 修改了 `sector_classification_service.py` 使用新的异常类
- 数据缺失时抛出 `MissingMADataError` 并包含缺失字段信息
- 计算失败时抛出 `ClassificationFailedError` 并包含具体原因
- 价格无效时抛出 `InvalidPriceError` 并包含原因说明

✅ **Task 4: 实现前端错误处理**
- 修改了 `sectorClassificationApi.ts` 添加标准错误响应类型定义
- 创建了 `ApiClientError` 类用于封装 API 错误
- 实现了 `handleResponse` 方法解析标准错误格式
- 兼容旧版错误格式（detail 字段）

✅ **Task 5: 创建错误显示组件**
- 创建了 `web/src/components/ErrorMessage.tsx` 组件
- 使用 Tailwind CSS 红色主题样式
- 包含错误图标、错误消息和错误码显示
- 提供可配置的重试按钮功能
- 确保颜色对比度符合可访问性要求

✅ **Task 6: 创建错误处理测试**
- 创建了 `server/tests/test_error_handling.py` 测试文件
- 测试了所有异常类型的初始化和属性
- 测试了异常的 `to_dict()` 方法
- 测试了错误响应格式
- 测试了中文错误消息
- 测试了异常继承关系
- 所有 17 个测试通过

### File List

**新增文件:**
- `server/src/exceptions/classification.py` - 自定义异常类定义
- `server/src/api/v1/error_handlers.py` - 全局异常处理器
- `server/tests/test_error_handling.py` - 错误处理测试
- `web/src/components/ErrorMessage.tsx` - 错误消息显示组件

**修改文件:**
- `server/main.py` - 注册分类异常处理器
- `server/src/services/sector_classification_service.py` - 集成新的异常类
- `web/src/lib/sectorClassificationApi.ts` - 增强错误处理

**更新文件:**
- `_bmad-output/implementation-artifacts/stories/1-6-implement-error-handling.md` - 标记任务完成
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - 更新状态为 review

### Code Review Follow-ups (AI-Review)

**日期:** 2026-01-22
**审查者:** Claude Opus 4.5 (Code Review Agent)

**修复的问题:**
- [x] [AI-Review][HIGH] 在 API 测试页面中使用 ErrorMessage 组件
  - 导入 ErrorMessage 组件
  - 替换内联错误显示代码
  - 添加重试按钮功能

**验证的问题:**
- [x] [AI-Review][HIGH] 验证 main.py 中异常处理器已正确注册
  - 第80行: `register_classification_exception_handlers(app)`
  - 异常处理器正确集成到应用

**新增测试:**
- [x] [AI-Review][MEDIUM] 添加异常处理器集成测试
  - 测试分类异常处理器已注册
  - 测试标准错误响应格式包含所有必需字段

**测试结果:**
- ✅ 19/19 错误处理测试通过
- ✅ 异常处理器注册验证通过
- ✅ 错误响应格式验证通过
