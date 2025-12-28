# Story 3.1: AkShare 数据源集成

Status: done

## Story

作为一名 系统开发者，
我需要 集成 AkShare 数据源以获取股票和板块数据，
以便 为强度计算提供实时市场数据。

## Acceptance Criteria

1. ✅ 能够成功连接到 AkShare 数据源
2. ✅ 实现获取股票列表的接口（`get_stock_list`）
3. ✅ 实现获取板块列表的接口（`get_sector_list`）
4. ✅ 实现获取日线行情数据的接口（`get_daily_data`）
5. ✅ 实现获取板块成分股的接口（`get_sector_stocks`）
6. ✅ 所有数据获取操作包含错误处理和重试机制
7. ✅ 数据格式符合系统数据模型要求
8. ✅ 添加单元测试覆盖所有数据获取函数

## Tasks / Subtasks

- [x] 数据源服务层架构设计 (AC: 1)
  - [x] 创建 `server/src/services/data_acquisition/` 目录结构
  - [x] 设计数据获取服务抽象接口
  - [x] 定义数据模型转换层（AkShare 格式 → 系统格式）

- [x] AkShare 集成实现 (AC: 1, 2, 3, 4, 5)
  - [x] 安装并配置 akshare 依赖包（requirements.txt）
  - [x] 实现 `AkShareDataSource` 基类
  - [x] 实现 `get_stock_list()` - 获取 A 股股票列表
  - [x] 实现 `get_sector_list()` - 获取行业板块和概念板块
  - [x] 实现 `get_daily_data(symbol, start_date, end_date)` - 获取日线数据
  - [x] 实现 `get_sector_stocks(sector_code)` - 获取板块成分股
  - [x] 实现数据格式转换（DataFrame → Pydantic 模型）

- [x] 错误处理和容错机制 (AC: 6)
  - [x] 实现网络请求重试逻辑（指数退避）
  - [x] 实现超时处理机制
  - [x] 实现数据源不可用时的降级策略
  - [x] 添加详细的日志记录
  - [x] 定义自定义异常类（`DataSourceError`, `DataFetchError`）

- [x] 数据验证 (AC: 7)
  - [x] 创建 Pydantic 数据验证模型
  - [x] 实现股票列表数据验证
  - [x] 实现板块列表数据验证
  - [x] 实现行情数据验证（检查必需字段：open, high, low, close, volume）
  - [x] 实现数据清洗逻辑（处理 NaN、异常值）

- [x] 测试 (AC: 8)
  - [x] 创建 `server/tests/test_data_acquisition.py`
  - [x] Mock AkShare 响应进行单元测试
  - [x] 测试错误重试机制
  - [x] 测试数据验证逻辑
  - [x] 测试数据格式转换正确性

## Dev Notes

### 故事依赖关系

**前置依赖**:
- Story 1-3: Backend API Framework（提供 FastAPI 基础框架）

**被以下故事依赖**:
- Story 3-2: 数据模型和数据库设置（使用本故事获取的数据填充数据库）
- Story 3-3: 强度得分计算引擎（使用本故事的行情数据作为计算输入）
- Story 3-5: 数据缓存和定时更新机制（调用本故事的数据采集服务）

### 相关架构模式和约束

- **服务层架构**: 创建独立的数据获取服务模块，遵循单一职责原则
- **异步支持**: 使用 `aiohttp` + `asyncio` 实现异步数据获取（虽然 AkShare 是同步的，但需要为未来扩展做准备）
- **错误处理**: 采用重试模式，最多 3 次重试，使用指数退避策略

### 源树组件需要修改

```
server/
├── src/
│   ├── services/
│   │   └── data_acquisition/
│   │       ├── __init__.py
│   │       ├── base.py          # 抽象数据源接口
│   │       ├── akshare_client.py # AkShare 具体实现
│   │       ├── models.py         # 数据传输对象
│   │       └── exceptions.py     # 自定义异常
│   └── models/
│       └── market_data.py       # 市场数据模型（已存在，需扩展）
├── tests/
│   └── test_data_acquisition.py
└── requirements.txt             # 需添加 akshare
```

### 测试标准摘要

- 使用 `pytest` 作为测试框架
- 使用 `pytest-mock` 模拟 AkShare 调用
- 目标测试覆盖率: > 85%
- 测试应包括正常流程、异常流程、边界条件

### 项目结构注意事项

- **对齐统一项目结构**: 服务模块放在 `server/src/services/` 下
- **命名约定**: Python 函数使用 `snake_case`（如 `get_stock_list`）
- **类型注解**: 所有函数必须包含类型注解
- **文档字符串**: 所有公共方法需要 Google 风格的 docstring

### 检测到的冲突或差异（附带理由）

无冲突 - 本故事是对现有架构的扩展。

### 技术栈要求

| 技术 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.11+ | 开发语言 |
| akshare | 最新稳定版 | 数据源 |
| pydantic | 2.x | 数据验证 |
| pandas | 最新 | 数据处理 |
| pytest | 最新 | 测试框架 |

### AkShare API 参考

根据最新 AkShare 文档（2024），主要使用的 API：
- `ak.stock_zh_a_spot_em()` - A 股实时行情
- `ak.stock_board_industry_name_em()` - 行业板块
- `ak.stock_board_concept_name_em()` - 概念板块
- `ak.stock_zh_a_hist()` - 个股历史数据
- `ak.stock_board_concept_cons_em()` - 概念板块成分股

### 安全考虑

- API 密钥管理：AkShare 目前不需要密钥，但应预留配置支持
- 敏感数据：不在日志中记录完整的用户数据
- 速率限制：实现请求频率限制，避免被封禁

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

glm-4.7

### Completion Notes

✅ **故事 3-1: AkShare 数据源集成 - 实现完成**

**实现内容:**
- 创建了 `server/src/services/data_acquisition/` 服务模块
- 实现了抽象数据源接口 `BaseDataSource` 和 AkShare 具体实现
- 实现了 4 个核心数据获取方法：`get_stock_list()`, `get_sector_list()`, `get_daily_data()`, `get_sector_stocks()`
- 实现了指数退避重试机制（默认 3 次重试）
- 实现了速率限制机制（最小请求间隔 500ms）
- 使用 Pydantic 实现了完整的数据验证模型
- 添加了完整的 Google 风格 docstring
- 创建了 20 个单元测试，全部通过

**代码审查修复 (2025-12-24):**
- 修复异常命名冲突：`TimeoutError` → `DataSourceTimeoutError`
- 修复类型注解：`any` → `typing.Any`
- 添加速率限制功能
- 添加完整的文档字符串
- 改进结构化日志记录

**测试结果:**
- 20/20 测试通过
- 测试覆盖正常流程、异常流程、重试机制、数据验证

---

## Senior Developer Review (AI)

**Review Date:** 2025-12-24
**Reviewer:** AI Code Reviewer
**Outcome:** ✅ Approve (after fixes)

### Action Items

All issues have been fixed:

- [x] [HIGH][exceptions.py:103] 修复异常命名冲突 - `TimeoutError` → `DataSourceTimeoutError`
- [x] [HIGH][akshare_client.py] 添加速率限制机制
- [x] [MEDIUM][base.py] 添加完整的 Google 风格 docstring
- [x] [MEDIUM][akshare_client.py:131] 修复类型注解 `any` → `Any`
- [x] [MEDIUM][models.py:114] 修复 `DataFetchResult.data` 类型定义

### Summary

原始实现质量良好，核心功能完整，测试覆盖充分。
代码审查发现的问题已全部修复，代码现在符合最佳实践：
- 无命名冲突
- 完整的类型注解
- 速率限制保护
- 完整的文档字符串
- 改进的日志记录

### File List

- `server/src/services/data_acquisition/__init__.py` - 模块导出
- `server/src/services/data_acquisition/base.py` - 抽象数据源接口
- `server/src/services/data_acquisition/akshare_client.py` - AkShare 客户端实现
- `server/src/services/data_acquisition/models.py` - Pydantic 数据验证模型
- `server/src/services/data_acquisition/exceptions.py` - 自定义异常类
- `server/tests/test_data_acquisition.py` - 单元测试
- `server/requirements.txt` - 添加了 akshare 和 pandas 依赖

### Change Log

- 2025-12-23: 实现 AkShare 数据源集成，包含数据获取、重试机制、数据验证和单元测试
- 2025-12-24: 代码审查修复 - 修复异常命名冲突、添加速率限制、完善文档字符串
