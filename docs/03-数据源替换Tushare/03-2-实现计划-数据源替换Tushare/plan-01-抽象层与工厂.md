---
feat_id: "plan-01"
title: "抽象层与工厂"
dimension: backend
phase: 1
status: draft
depends_on: []
---

# plan-01: 抽象层与工厂

## 1. 功能概要

- **目标**: 扩展 BaseDataSource 抽象接口（新增 `get_trading_calendar`），引入 DataSourceFactory 工厂类，为后续 TushareDataSource 实现和服务层解耦奠定基础设施。
- **完成后可观察结果**: `BaseDataSource` 新增 `get_trading_calendar` 抽象方法，AkShareDataSource 已有实现不受影响。`DataSourceFactory.create()` 在 `DATA_SOURCE_TYPE=tushare` 时能返回 TushareDataSource 实例（TushareDataSource 可为 stub），在 `DATA_SOURCE_TYPE=akshare` 时返回 AkShareDataSource 实例。非法环境变量值直接报错并提示可选值。`.env.example` 已更新包含全部新环境变量。
- **依赖**: 无
- **关联验收标准**: [AC-06]
- **涉及架构模块**: BaseDataSource, DataSourceFactory
- **前置条件**: 后端项目可正常启动；AkShareDataSource 已有 `get_trading_calendar` 实现
- **不在范围**: TushareDataSource 完整实现（plan-02）；服务层解耦替换（plan-03）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_acquisition/base.py` | 新增 `get_trading_calendar` 抽象方法 |
| modify | `server/src/services/data_acquisition/__init__.py` | 新增 DataSourceFactory，更新导出 |
| modify | `.env.example` | 新增 DATA_SOURCE_TYPE、TUSHARE_TOKEN、TUSHARE_API_URL、TUSHARE_API_INTERVAL |

## 3. 实现规格

### 后端部分

#### 1. BaseDataSource 新增 get_trading_calendar 抽象方法

在 `server/src/services/data_acquisition/base.py` 的 `BaseDataSource` 类中新增：

```python
@abstractmethod
def get_trading_calendar(self) -> List[date]:
    """
    获取交易日历

    Returns:
        交易日日期列表

    Raises:
        DataFetchError: 数据获取失败
    """
    pass
```

导入 `date` 已在文件中（`from datetime import date`）。`List` 已在文件中（`from typing import List, Optional`）。无需新增导入。

AkShareDataSource 已有同名方法实现（非抽象），纳入抽象后自动成为抽象方法的实现，无需修改。

#### 2. DataSourceFactory 工厂类

在 `server/src/services/data_acquisition/__init__.py` 中新增 `DataSourceFactory` 类：

```python
import os
import logging

logger = logging.getLogger(__name__)


class DataSourceFactory:
    VALID_TYPES = ("tushare", "akshare")

    @staticmethod
    def create() -> BaseDataSource:
        source_type = os.getenv("DATA_SOURCE_TYPE", "akshare").strip().lower()

        if source_type not in DataSourceFactory.VALID_TYPES:
            raise ValueError(
                f"无效的数据源类型: '{source_type}'，可选值: {', '.join(DataSourceFactory.VALID_TYPES)}"
            )

        if source_type == "tushare":
            from .tushare_client import TushareDataSource
            instance = TushareDataSource()
        else:
            instance = AkShareDataSource()

        logger.info(f"数据源切换为: {instance.source_name}")
        return instance
```

更新 `__all__` 列表新增 `"DataSourceFactory"`。

**可观测性（架构 §8.5）**：工厂创建数据源时记录 INFO 日志 `"数据源切换为: {source_name}"`。使用项目现有 `logging` 模块。

#### 3. 更新 .env.example

在 `.env.example` 末尾新增：

```env
# 数据源配置
DATA_SOURCE_TYPE=tushare              # 数据源类型: tushare / akshare

# Tushare 配置
TUSHARE_TOKEN=                        # Tushare API Token（必填）
TUSHARE_API_URL=api.tushare.pro       # Tushare 服务地址（可选，默认官方地址）
TUSHARE_API_INTERVAL=0.5              # Tushare 请求最小间隔（秒，默认 0.5）
```

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | BaseDataSource 新增 `get_trading_calendar` 抽象方法 | backend | todo | |
| 2 | 创建 DataSourceFactory 类 | backend | todo | 在 `__init__.py` 中 |
| 3 | 更新 `__init__.py` 导出列表 | backend | todo | 新增 DataSourceFactory |
| 4 | 更新 `.env.example` 新增环境变量 | backend | todo | |

## 5. 验收标准

### 后端验收

- [ ] AC-06 `DataSourceFactory.create()` 在 `DATA_SOURCE_TYPE=tushare` 时返回 TushareDataSource 实例（可先为 stub）
- [ ] AC-06 `DataSourceFactory.create()` 在 `DATA_SOURCE_TYPE=akshare` 时返回 AkShareDataSource 实例
- [ ] AC-06 `DataSourceFactory.create()` 在 `DATA_SOURCE_TYPE` 为非法值时抛出 `ValueError` 并提示可选值
- [ ] AC-06 `DATA_SOURCE_TYPE` 未设置时默认使用 `akshare`
- [ ] `BaseDataSource` 新增 `get_trading_calendar` 抽象方法，AkShareDataSource 不受影响（其同名方法自动成为实现）
- [ ] `.env.example` 包含 `DATA_SOURCE_TYPE`、`TUSHARE_TOKEN`、`TUSHARE_API_URL`、`TUSHARE_API_INTERVAL`
- [ ] E2E 不适用：本功能为纯后端基础设施（抽象层 + 工厂类），无用户可观察 UI，通过 plan-03 全链路验证间接覆盖

## 6. 验证命令

```bash
cd server

# 验证 BaseDataSource 抽象方法存在
python -c "
from src.services.data_acquisition.base import BaseDataSource
import inspect
assert 'get_trading_calendar' in [m[0] for m in inspect.getmembers(BaseDataSource, predicate=inspect.isfunction)]
print('OK: get_trading_calendar 抽象方法已存在')
"

# 验证 AkShareDataSource 不受影响（已有实现）
python -c "
from src.services.data_acquisition import AkShareDataSource
ds = AkShareDataSource()
assert hasattr(ds, 'get_trading_calendar')
print(f'OK: AkShareDataSource.get_trading_calendar 存在')
"

# 验证 DataSourceFactory 默认 akshare
python -c "
from src.services.data_acquisition import DataSourceFactory
ds = DataSourceFactory.create()
print(f'OK: 默认数据源 = {ds.source_name}')
"

# 验证非法值报错
DATA_SOURCE_TYPE=invalid python -c "
import os; os.environ['DATA_SOURCE_TYPE'] = 'invalid'
from src.services.data_acquisition import DataSourceFactory
try:
    DataSourceFactory.create()
    print('FAIL: 应该抛出 ValueError')
except ValueError as e:
    print(f'OK: 非法值报错: {e}')
"
```

## 7. 交接上下文

- **架构章节**: §4.1 系统上下文, §4.2 模块职责（DataSourceFactory、BaseDataSource）, §5 ADR-1, ADR-2
- **相关代码**:
  - `server/src/services/data_acquisition/base.py` — BaseDataSource 抽象基类
  - `server/src/services/data_acquisition/akshare_client.py` — AkShareDataSource（参考其 get_trading_calendar 实现）
  - `server/src/services/data_acquisition/__init__.py` — 模块导出 + Factory 所在文件
- **契约 / 数据对象**: `BaseDataSource` 抽象接口（5 个方法 + health_check）
- **下游消费方**: plan-02（TushareDataSource 实现 BaseDataSource）, plan-03（所有服务通过 Factory 获取数据源）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→4）
- **验证失败排查方向**: 检查 Python 环境是否安装了 tushare（plan-01 的 Factory 对 tushare 的 import 需在 plan-02 中实现，plan-01 阶段可用条件导入或 stub）
- **允许修改的额外文件**: 无
- **暂停条件**: BaseDataSource 改造导致 AkShareDataSource 无法启动
- **E2E 不适用说明**: 本功能为纯后端基础设施抽象层，无用户可观察行为，通过 plan-03 全链路验证间接覆盖
- **风险备注**: TushareDataSource 在 plan-01 阶段只需 stub（`__init__` + 抽象方法空实现），Factory 中使用延迟导入避免循环依赖

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| DATA_SOURCE_TYPE 未设置 | 默认使用 `akshare` | todo |
| DATA_SOURCE_TYPE 为非法值 | 抛出 ValueError 并提示可选值 | todo |
| DATA_SOURCE_TYPE 大小写混合 | `.strip().lower()` 归一化 | todo |
| TushareDataSource 尚未实现（plan-01 阶段） | Factory 中使用延迟导入，导入失败时给出明确提示 | todo |
