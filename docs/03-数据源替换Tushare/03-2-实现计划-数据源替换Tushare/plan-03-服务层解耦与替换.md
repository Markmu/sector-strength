---
feat_id: "plan-03"
title: "服务层解耦与替换"
dimension: backend
phase: 3
status: draft
depends_on: ["plan-01", "plan-02"]
---

# plan-03: 服务层解耦与替换

## 1. 功能概要

- **目标**: 将 5 个服务文件中对 AkShareDataSource 的硬编码依赖替换为通过 DataSourceFactory 获取数据源实例，实现数据源切换的透明化。完成后管理员可通过修改环境变量在 Tushare 和 AkShare 之间切换，无需修改任何代码。
- **完成后可观察结果**: `DATA_SOURCE_TYPE=tushare` 时，管理员触发数据初始化，系统通过 Tushare 获取交易日历、股票列表、板块列表、个股日线和板块日线，数据写入数据库后计算和展示正常进行。`DATA_SOURCE_TYPE=akshare` 时，系统回退到 AkShare，行为与改造前完全一致。5 个服务文件中不再有 `from ...akshare_client import AkShareDataSource` 的直接导入。
- **依赖**: plan-01（DataSourceFactory）, plan-02（TushareDataSource 实现）
- **关联验收标准**: [AC-06]
- **涉及架构模块**: TradingCalendar, DataInitService, DataUpdateService, DataCollector, DataQualityChecker, DataSourceFactory
- **前置条件**: plan-01 和 plan-02 完成；后端服务可正常启动
- **不在范围**: 前端变更；数据库变更；AkShare 代码删除

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/trading_calendar.py` | 移除 AkShareDataSource 硬编码，改用 DataSourceFactory |
| modify | `server/src/services/data_init.py` | 移除 AkShareDataSource 硬编码，改用 DataSourceFactory |
| modify | `server/src/services/data_update.py` | 移除 AkShareDataSource 硬编码，改用 DataSourceFactory |
| modify | `server/src/services/data_updater/collector.py` | 移除 AkShareDataSource 硬编码，改用 DataSourceFactory（单实例复用） |
| modify | `server/src/services/monitoring/data_quality.py` | 移除 AkShareDataSource 硬编码，改用 DataSourceFactory |

## 3. 实现规格

### 后端部分

#### 1. TradingCalendar 解耦

文件：`server/src/services/trading_calendar.py`

当前代码（第 5 行、第 24 行）：
```python
from src.services.data_acquisition.akshare_client import AkShareDataSource
...
source = AkShareDataSource()
```

替换为：
```python
from src.services.data_acquisition import DataSourceFactory
...
source = DataSourceFactory.create()
```

TradingCalendar 的缓存逻辑和降级逻辑（获取失败时用周末判断兜底）保持不变。

#### 2. DataInitService 解耦

文件：`server/src/services/data_init.py`

当前代码（第 20 行、第 64 行）：
```python
from src.services.data_acquisition.akshare_client import AkShareDataSource
...
self.ak_source = AkShareDataSource()
```

替换为：
```python
from src.services.data_acquisition import DataSourceFactory
...
self.ak_source = DataSourceFactory.create()
```

变量名 `ak_source` 保留不变（仅作为内部数据源实例引用，不影响功能）。

#### 3. DataUpdateService 解耦

文件：`server/src/services/data_update.py`

当前代码（第 23 行、第 72 行）：
```python
from src.services.data_acquisition.akshare_client import AkShareDataSource
...
self.ak_source = AkShareDataSource()
```

替换为：
```python
from src.services.data_acquisition import DataSourceFactory
...
self.ak_source = DataSourceFactory.create()
```

#### 4. DataCollector 解耦

文件：`server/src/services/data_updater/collector.py`

当前代码（第 22 行）：
```python
from src.services.data_acquisition.akshare_client import AkShareDataSource
```

以及 3 处实例化（第 132 行、第 162 行、第 191 行）：
```python
data_source = AkShareDataSource()
```

替换方案：在 `__init__` 中创建一次数据源实例并复用（保留限流状态）：

```python
from src.services.data_acquisition import DataSourceFactory
...
# __init__ 中新增：
self._data_source = DataSourceFactory.create()
```

3 处 `data_source = AkShareDataSource()` 统一改为 `data_source = self._data_source`。

注意：仅在 `__init__` 已存在时新增 `self._data_source` 赋值；若 `__init__` 不存在，则新增 `__init__` 方法。

#### 5. DataQualityChecker 解耦

文件：`server/src/services/monitoring/data_quality.py`

当前代码（第 21 行、第 30 行）：
```python
from src.services.data_acquisition.akshare_client import AkShareDataSource
...
self._data_source = AkShareDataSource()
```

替换为：
```python
from src.services.data_acquisition import DataSourceFactory
...
self._data_source = DataSourceFactory.create()
```

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | TradingCalendar: 替换 AkShareDataSource → DataSourceFactory | backend | todo | |
| 2 | DataInitService: 替换 AkShareDataSource → DataSourceFactory | backend | todo | |
| 3 | DataUpdateService: 替换 AkShareDataSource → DataSourceFactory | backend | todo | |
| 4 | DataCollector: 替换 AkShareDataSource → DataSourceFactory（单实例复用） | backend | todo | |
| 5 | DataQualityChecker: 替换 AkShareDataSource → DataSourceFactory | backend | todo | |
| 6 | 全局验证：确认无残留 AkShareDataSource 直接导入 | backend | todo | grep 确认 |

## 5. 验收标准

### 后端验收

- [ ] AC-06 `DATA_SOURCE_TYPE=tushare` 时，5 个服务文件通过 DataSourceFactory 获取 TushareDataSource 实例
- [ ] AC-06 `DATA_SOURCE_TYPE=akshare` 时，5 个服务文件回退使用 AkShareDataSource，行为与改造前一致
- [ ] AC-06 `DATA_SOURCE_TYPE` 未设置时，默认使用 AkShareDataSource
- [ ] 5 个服务文件中不再有 `from src.services.data_acquisition.akshare_client import AkShareDataSource`
- [ ] DataCollector 中数据源实例只创建一次并复用（`self._data_source`），限流状态保持连续
- [ ] TradingCalendar 缓存逻辑和降级逻辑不变
- [ ] E2E 不适用说明（见下方）：本功能为纯后端服务层改造，无用户可观察 UI 变化，通过全链路验证确认

### 全流程验收（US 覆盖矩阵）

> 架构文档 §2.3 定义的成功标准对应 PRD US-01 ~ US-05。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 管理员触发数据初始化时系统使用 Tushare 获取数据 | plan-03 | 配置 TUSHARE_TOKEN，DATA_SOURCE_TYPE=tushare，调用 POST /api/admin/init/all |
| US-02 | 系统从 Tushare 获取个股前复权日线行情 | plan-02, plan-03 | 触发数据初始化，检查 DailyMarketData 表有个股数据 |
| US-03 | 系统从 Tushare 获取板块日线行情 | plan-02, plan-03 | 触发数据初始化，检查 DailyMarketData 表有板块数据 |
| US-04 | 系统从 Tushare 获取交易日历 | plan-02, plan-03 | 触发交易日判断，检查 TradingCalendar 返回正确 |
| US-05 | 开发者通过环境变量控制数据源切换 | plan-01, plan-03 | 切换 DATA_SOURCE_TYPE 并重启，确认全链路切换成功 |
- [ ] US-01 ~ US-05 全部可在当前实现下正常走通

## 6. 验证命令

```bash
cd server

# 1. 确认无残留 AkShareDataSource 直接导入
grep -rn "from.*akshare_client import AkShareDataSource" src/services/trading_calendar.py src/services/data_init.py src/services/data_update.py src/services/data_updater/collector.py src/services/monitoring/data_quality.py
# 预期：无输出（所有直接导入已移除）

# 2. 确认使用 DataSourceFactory
grep -n "DataSourceFactory" src/services/trading_calendar.py src/services/data_init.py src/services/data_update.py src/services/data_updater/collector.py src/services/monitoring/data_quality.py
# 预期：每个文件都有 DataSourceFactory 引用

# 3. 验证 tushare 模式全链路（需要有效 TUSHARE_TOKEN）
export DATA_SOURCE_TYPE=tushare
export TUSHARE_TOKEN=your_token_here
python -c "
from src.services.data_acquisition import DataSourceFactory
ds = DataSourceFactory.create()
print(f'数据源: {ds.source_name}')
print(f'健康检查: {ds.health_check()}')
"

# 4. 验证 akshare 模式回退
export DATA_SOURCE_TYPE=akshare
python -c "
from src.services.data_acquisition import DataSourceFactory
ds = DataSourceFactory.create()
print(f'数据源: {ds.source_name}')
assert ds.source_name == 'AkShare'
print('OK: 回退到 AkShare 正常')
"
```

## 7. 交接上下文

- **架构章节**: §4.1 系统上下文, §6.1 数据初始化链路, §6.2 TradingCalendar 链路, §6.3 数据源切换链路
- **相关代码**:
  - `server/src/services/trading_calendar.py` — TradingCalendar 服务
  - `server/src/services/data_init.py` — DataInitService
  - `server/src/services/data_update.py` — DataUpdateService
  - `server/src/services/data_updater/collector.py` — DataCollector
  - `server/src/services/monitoring/data_quality.py` — DataQualityChecker
  - `server/src/services/data_acquisition/__init__.py` — DataSourceFactory
- **契约 / 数据对象**: DataSourceFactory.create() → BaseDataSource
- **下游消费方**: 无（本功能为最终集成功能）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→4→5→6）。Task 6（全局 grep 验证）必须在所有替换完成后执行。
- **验证失败排查方向**:
  - grep 仍有残留 → 搜索遗漏的 `AkShareDataSource` 引用
  - DataSourceFactory 报错 → 检查 plan-01 的工厂是否正确导入
  - 全链路失败 → 检查 TUSHARE_TOKEN 配置和 Tushare 服务可用性
- **允许修改的额外文件**: 无
- **暂停条件**: DataSourceFactory 导入失败；替换后 akshare 模式行为异常
- **E2E 不适用说明**: 本功能为纯后端服务层 import 替换，无用户可观察 UI 变化。数据源功能正确性已在 plan-02 验收中覆盖。本功能验证的是"依赖注入替换是否完整"，通过 grep + 全链路切换测试即可确认。
- **风险备注**:
  - DataCollector 中 3 处 `AkShareDataSource()` 改为共用实例，需确认共用不会引入状态污染（限流状态连续是预期行为）
  - 变量名 `self.ak_source` 保留不变避免不必要的变量重命名
  - TradingCalendar 的 `_get_trading_days` 是同步方法，`DataSourceFactory.create()` 也是同步的，无 async 兼容问题
  - **前复权数据差异（架构 §8.6）**：Tushare pro_bar 前复权数据与 AkShare 前复权数据可能存在微小差异（复权算法不同），切换后建议触发全量历史数据重初始化以确保计算结果一致性

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| DATA_SOURCE_TYPE=tushare 且 Token 无效 | DataSourceFactory 返回 TushareDataSource 实例，首次调用时报错（与改造前 AkShare 模式下网络不通的行为一致） | todo |
| DATA_SOURCE_TYPE=tushare 且积分不足 | ths_index/ths_daily 调用报错，上层服务捕获 DataFetchError | todo |
| DataSourceFactory.create() 多次调用 | 每次 create() 都读取环境变量并创建新实例（架构 §6.3，不缓存实例） | todo |
| DataCollector 共用实例的限流状态 | 限流状态连续是预期行为（与原来 3 次新建 AkShareDataSource 的行为略有不同但更合理） | todo |
| AkShareDataSource 在 __init__.py 中仍有导出 | 保留（AkShare 代码不删除，其他未改造模块可能仍在使用） | todo |
