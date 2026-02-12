---
title: '板块数据接入重构：东方财富切换为同花顺（AkShare）'
slug: 'sector-data-source-ths-migration'
created: '2026-02-12T14:43:35+08:00'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.11', 'FastAPI', 'SQLAlchemy 2.x AsyncSession', 'Pydantic v2', 'AkShare 1.18.x', 'Pytest + pytest-asyncio']
files_to_modify: ['server/src/services/data_acquisition/base.py', 'server/src/services/data_acquisition/akshare_client.py', 'server/src/services/data_acquisition/models.py', 'server/src/services/data_init.py', 'server/src/services/task_handlers.py', 'server/src/services/task_executor.py', 'server/src/services/data_updater/collector.py', 'server/src/api/admin/init.py', 'server/src/api/admin/tasks.py', 'scripts/truncate_sector_related_tables.sql (新建)', 'server/tests/test_data_init.py', 'server/tests/test_task_system.py', 'server/tests/test_data_updater.py', 'server/tests/test_data_acquisition/test_akshare_client.py (新建)']
code_patterns: ['数据源方法为同步函数，服务层在 async 方法中直接调用', '统一使用 progress_callback(current,total,message) 上报进度', 'TaskRegistry.register 装饰器注册任务类型到 handler', 'TaskExecutor 轮询+并发上限+超时重试机制']
test_patterns: ['pytest.mark.asyncio + AsyncMock/MagicMock', 'patch 注入 AkShareDataSource（按模块路径 patch）', '任务系统测试通过 TaskRegistry 注册项断言', '数据更新测试覆盖边界值与失败路径', 'collector 测试以方法级 patch 为主']
---

# Tech-Spec: 板块数据接入重构：东方财富切换为同花顺（AkShare）

**Created:** 2026-02-12T14:43:35+08:00

## Overview

### Problem Statement

当前板块数据接入依赖 AkShare 的东方财富系接口（`*_em`）。需求要求一次性切换为同花顺系接口（`*_ths`），并重构后端、数据采集、任务执行链路，删除东方财富板块相关分支代码；同时本次不再保留板块成分股功能。

### Solution

以 `AkShareDataSource` 为核心进行接口替换和能力收敛：板块列表与板块日线统一改为同花顺接口；同步改造 `data_init`、`data_update`、`data_updater`、`task_handlers`、`task_executor` 的板块链路逻辑，并补齐完整单测与集成测试，确保一次性切换后可稳定运行。

### Scope

**In Scope:**
- 板块列表采集切换为 `stock_board_industry_name_ths` 和 `stock_board_concept_name_ths`
- 板块日线采集切换为 `stock_board_industry_index_ths` 和 `stock_board_concept_index_ths`
- 切换前在停机窗口人工触发 `TRUNCATE` 清空历史相关表（不保留旧数据兼容路径）
- 删除东方财富板块相关分支逻辑和无效代码
- 重构板块相关任务处理与执行链路（含并发/重试/异常处理策略）
- 完整测试覆盖（数据源、服务层、任务链路、失败场景）

**Out of Scope:**
- 股票列表和个股行情数据接入切换
- 板块成分股采集与相关功能
- 灰度发布、回滚开关、多数据源并行兼容

## Context for Development

### Codebase Patterns

- 数据源抽象 `BaseDataSource` 当前强制要求 `get_sector_stocks`，与本次“移除成分股能力”冲突，需要接口收敛。
- `AkShareDataSource` 的板块列表与板块日线仍是东方财富实现：`stock_board_industry_name_em` / `stock_board_concept_name_em` / `stock_board_industry_hist_em`。
- `DataInitService.init_sectors()` 当前包含“建板块 + 拉成分股 + 建关联”的耦合流程；`init_sector_stocks()` 也是独立任务入口，需整体移除。
- `DataInitService.init_sector_historical_data()` 调用 `get_sector_daily_data(sector.code, start, end)`，未显式传入板块类型；切 THS 后必须按 `sector.type` 路由。
- `TaskHandlers` 已将 `init_sector_stocks` 注册为任务类型，并在 `__all__`/测试中被断言；移除时要同步更新注册与测试基线。
- `TaskExecutor` 机制是“DB pending 轮询 + 本地 running_tasks 集合 + 超时重试”；本次重构应聚焦板块链路任务领取、幂等和失败语义，不扩大到全部任务类型。
- `DataCollector` 存在接口名不一致问题（例如 `await data_source.get_sector_list()`、`await data_source.get_daily_quotes()`），说明该模块处于半成品状态，需在本次改造中统一调用约定。
- 管理端任务入口统一为“API 创建 TaskManager 任务”，不在 API 层直接执行业务清空。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `server/src/services/data_acquisition/base.py` | 抽象接口定义；需删除 `get_sector_stocks` 能力要求并保持接口契约一致 |
| `server/src/services/data_acquisition/akshare_client.py` | 板块接口从 EM 切 THS 的核心文件；还需修正 endpoint 标识与类型路由 |
| `server/src/services/data_acquisition/models.py` | 清理 `SectorConstituent` 与相关类型别名导出，移除兼容分支 |
| `server/src/services/data_init.py` | 成分股逻辑高度耦合点；需拆除 `init_sectors` 中关联构建并移除 `init_sector_stocks` |
| `server/src/services/task_handlers.py` | 任务类型枚举、注册器、日志语义同步重构；移除 `INIT_SECTOR_STOCKS` |
| `server/src/services/task_executor.py` | 板块任务执行策略（并发、重试、幂等语义）重构锚点 |
| `server/src/services/data_updater/collector.py` | 板块更新链路调用适配；修正 async/sync 方法不匹配与接口命名漂移 |
| `server/src/api/admin/init.py` | 管理端初始化文案与流程改造，明确停机清空为人工前置步骤 |
| `server/src/api/admin/tasks.py` | API 创建 TaskManager 任务的主入口，需补齐板块迁移任务创建语义 |
| `scripts/truncate_sector_related_tables.sql` (新建) | 维护一次性清空 SQL，供人工停机窗口执行 |
| `server/tests/test_data_init.py` | 现有用例大量断言成分股行为，需重写为“仅板块实体”语义 |
| `server/tests/test_task_system.py` | 注册任务集合包含 `init_sector_stocks`，需同步变更断言 |
| `server/tests/test_data_updater.py` | 现有 mock 接口名与真实实现不一致，需重构为真实方法契约 |
| `server/tests/test_data_acquisition/test_akshare_client.py` (新建) | 为 THS 映射、字段转换、错误与重试提供接口层单测基线 |

### Technical Decisions

#### ADR-001: 板块数据源统一切换到同花顺（AkShare THS）
- 决策：一次性全量迁移 THS（列表+日线）
- 理由：满足明确需求，避免双栈维护
- 影响：移除东方财富板块分支，统一接口语义

#### ADR-002: 板块成分股能力本次彻底移除
- 决策：代码和任务链路都移除
- 理由：需求明确不再需要成分股功能
- 影响：收敛采集边界，减少后续回归面

#### ADR-003: 日线接口按板块类型显式路由
- 决策：行业/概念分别路由到对应 THS 函数
- 理由：避免接口误用，提升可测试性与可读性
- 影响：调用方需显式传入或识别板块类型

#### ADR-004: 任务执行器板块链路深度重构但范围隔离
- 决策：重构板块任务链路的并发/重试/异常处理，不扩散到无关任务
- 理由：在改造深度与发布风险之间取可控平衡
- 影响：`task_handlers` 与 `task_executor` 将有结构性调整

#### ADR-005: 发布策略为一次性切换，不保留运行时开关
- 决策：不引入 `SECTOR_SOURCE` 之类的动态开关
- 理由：降低系统复杂度，与业务决策一致
- 影响：上线前测试门槛提高，需完整回归

#### ADR-006: 测试采用三层覆盖策略
- 决策：接口层 + 服务层 + 任务链路集成测试
- 理由：覆盖字段映射、重试调度、失败恢复等关键风险
- 影响：测试工作量增加，但显著降低一次性切换故障概率

#### ADR-007: 板块日线获取接口调整为类型显式参数
- 决策：`get_sector_daily_data` 从仅 `sector_code` 升级为显式接收 `sector_type`
- 理由：THS 行业/概念函数不同，必须靠类型分路由
- 影响：`data_init`/任务链路需要同步传递 `sector.type`

#### ADR-008: 移除 `init_sector_stocks` 任务类型与关联测试
- 决策：删除 `TaskType.INIT_SECTOR_STOCKS` 及对应 handler、注册断言和服务方法引用
- 理由：成分股能力已明确出 scope
- 影响：任务系统基线与 API 文案需要同步更新，避免遗留入口

#### ADR-009: 历史数据清空策略固定为停机人工触发 TRUNCATE
- 决策：在停机窗口人工触发清空任务，直接 `TRUNCATE` 历史关联表，不做回滚与恢复方案
- 理由：需求明确要求“直接清”，且不保留旧数据兼容
- 影响：实现必须提供明确表清单与“清空后计数为 0”校验

## Implementation Plan

### Tasks

- [x] Task 1: 收敛数据源抽象契约并移除成分股能力
  - File: `server/src/services/data_acquisition/base.py`
  - Action: 删除 `get_sector_stocks` 抽象方法；将板块相关抽象接口明确为 `get_sector_list` 与 `get_sector_daily_data`（支持 `sector_type`）
  - Notes: 保持 `BaseDataSource` 其余行为不变，避免影响股票链路

- [x] Task 2: 切换板块列表到 THS 接口并统一字段映射
  - File: `server/src/services/data_acquisition/akshare_client.py`
  - Action: 将行业/概念列表获取从 `*_name_em` 改为 `stock_board_industry_name_ths` 与 `stock_board_concept_name_ths`
  - Notes: 映射 THS 字段 `name/code` 到 `SectorInfo(name/code/type)`；修正 endpoint 日志标识

- [x] Task 3: 切换板块日线到 THS 并按类型显式路由
  - File: `server/src/services/data_acquisition/akshare_client.py`
  - Action: 重构 `get_sector_daily_data` 签名，增加 `sector_type` 参数；行业路由 `stock_board_industry_index_ths`，概念路由 `stock_board_concept_index_ths`
  - Notes: 保留日期格式和数据清洗逻辑；字段兼容 `日期/开盘价/最高价/最低价/收盘价/成交量/成交额`

- [x] Task 4: 清理成分股数据模型输出边界
  - File: `server/src/services/data_acquisition/models.py`
  - Action: 移除 `SectorConstituent` 及其相关类型别名在数据源导出链路中的使用，去除兼容分支
  - Notes: 本次明确不做旧数据兼容，采用单一路径清理

- [x] Task 5: 重构板块初始化服务并移除成分股流程
  - File: `server/src/services/data_init.py`
  - Action: `init_sectors` 仅保留板块实体初始化；删除成分股拉取与 `SectorStock` 关联逻辑；删除 `init_sector_stocks` 方法
  - Notes: `init_sector_historical_data` 调用 `get_sector_daily_data` 时传入 `sector.type`

- [x] Task 6: 重构任务类型与处理器注册
  - File: `server/src/services/task_handlers.py`
  - Action: 删除 `TaskType.INIT_SECTOR_STOCKS` 与 `init_sector_stocks_task`；更新板块初始化任务日志与结果字段
  - Notes: 确保 `__all__` 与注册表输出无残留符号

- [x] Task 7: 重构任务执行链路的板块语义一致性
  - File: `server/src/services/task_executor.py`
  - Action: 明确增强 `_execute_task` 和 `_handle_task_timeout` 的板块任务日志字段（task_type/retry_count/error_class），并补充失败分类与重试记录
  - Notes: 范围仅限板块任务相关语义，不扩散到其他任务类型策略

- [x] Task 8: 固化清空 SQL 脚本与执行说明（人工执行）
  - File: `scripts/truncate_sector_related_tables.sql` (新建)
  - Action: 编写 `TRUNCATE ... RESTART IDENTITY CASCADE` 脚本，清空 `sector_classification`、`strength_scores`、`moving_average_data`、`daily_market_data`、`sector_stocks`、`sectors`
  - Notes: 脚本是唯一清空手段；不在 `data_init` 中实现 `TRUNCATE`

- [x] Task 9: 建立“清空完成后再迁移”的硬前置步骤
  - File: `server/src/api/admin/init.py`
  - Action: 在板块迁移入口明确要求人工先执行清空脚本，再允许创建迁移任务
  - Notes: 无自动校验，由人工确认

- [x] Task 10: 对齐 API 创建任务语义（TaskManager）
  - File: `server/src/api/admin/tasks.py`
  - Action: 统一板块迁移相关任务通过该 API 创建并交由 TaskManager 调度；补齐参数与状态语义
  - Notes: API 只创建任务，不直接执行清空

- [x] Task 11: 对齐管理端初始化 API 语义
  - File: `server/src/api/admin/init.py`
  - Action: 删除成分股语义并增加“停机人工清空”提示
  - Notes: 与 `server/src/api/admin/tasks.py` 的任务创建入口保持一致

- [x] Task 12: 修正数据采集协调器的接口调用契约
  - File: `server/src/services/data_updater/collector.py`
  - Action: 统一 `AkShareDataSource` 调用方式（同步方法不使用 `await`，方法名改为真实存在的接口）
  - Notes: 仅修复板块相关调用，股票链路不在本次改造范围

- [x] Task 13: 新增 THS 数据源映射单测
  - File: `server/tests/test_data_acquisition/test_akshare_client.py` (新建)
  - Action: 覆盖板块列表映射、板块日线路由、字段漂移、空数据、重试耗尽
  - Notes: 使用 patch 模拟 AkShare 返回 DataFrame，不依赖外网

- [x] Task 14: 重构初始化服务测试基线
  - File: `server/tests/test_data_init.py`
  - Action: 移除 `get_sector_stocks`/`init_sector_stocks` 相关断言；新增“初始化板块不拉取成分股”“按 sector.type 拉取 THS 日线”测试
  - Notes: 保持原有进度回调与取消逻辑覆盖

- [x] Task 15: 重构任务系统与协调器测试
  - File: `server/tests/test_task_system.py`
  - Action: 移除 `init_sector_stocks` 注册断言，补充“API 创建 TaskManager 任务（含 task_type/params/status 字段）”链路断言
  - Notes: 验证 TaskRegistry 与 handler 对齐

- [x] Task 16: 修正采集协调器测试契约
  - File: `server/tests/test_data_updater.py`
  - Action: 将 `fetch_sectors/fetch_stocks/fetch_daily_quotes` 的 mock 改为实际方法契约
  - Notes: 明确同步/异步 mock 的边界，避免“假通过”

- [x] Task 17: 执行板块链路回归并输出测试证据
  - File: `server/tests/test_data_acquisition/test_akshare_client.py`, `server/tests/test_data_init.py`, `server/tests/test_task_system.py`, `server/tests/test_data_updater.py`
  - Action: 运行板块链路测试并产出通过/失败摘要与日志链接
  - Notes: 失败场景至少覆盖字段缺失、路由错误、重试耗尽、任务异常

### Acceptance Criteria

- [x] AC 1: Given 板块列表初始化任务触发，when 调用数据源获取板块列表，then 行业与概念均通过 THS 接口获取并成功映射为 `SectorInfo`
- [x] AC 2: Given 板块类型为 `industry`，when 获取板块日线，then 系统调用 `stock_board_industry_index_ths` 并成功写入 `DailyMarketData`
- [x] AC 3: Given 板块类型为 `concept`，when 获取板块日线，then 系统调用 `stock_board_concept_index_ths` 并成功写入 `DailyMarketData`
- [ ] AC 4: Given 传入非法板块类型，when 请求板块日线，then 系统返回可追踪错误且任务状态标记为失败
- [x] AC 5: Given 历史代码调用成分股初始化入口，when 系统启动任务注册，then 不存在 `init_sector_stocks` 任务类型且无残留 handler
- [x] AC 6: Given 执行 `/init/sectors` 或对应异步任务，when 初始化完成，then 结果中不再包含成分股关联统计字段且板块实体仍可正确创建
- [x] AC 7: Given THS 返回空数据集，when 执行板块日线初始化，then 系统记录告警并跳过对应板块，不导致整体任务崩溃
- [ ] AC 8: Given THS 返回字段异常或映射失败，when 触发重试机制，then 在达到最大重试次数后任务失败并写入重试耗尽上下文日志
- [ ] AC 9: Given 板块任务执行期间发生异常，when TaskExecutor 处理该任务，then 任务状态按重试策略在 `pending/running/failed` 间正确迁移
- [x] AC 10: Given 运行板块链路测试集，when 执行 CI 测试，then 接口层、服务层、任务层测试全部通过
- [ ] AC 11: Given 人工在停机窗口执行清空流程，when 触发 `TRUNCATE` 脚本，then `sector_classification`、`strength_scores`、`moving_average_data`、`daily_market_data`、`sector_stocks`、`sectors` 表数据条数均为 0
- [x] AC 12: Given 管理端 API 触发后台任务，when 创建迁移任务，then 由 TaskManager 创建并调度任务，且 `task_type`、`params`、`status` 字段与规范一致（API 仅负责创建，不直接执行业务清空）

## Additional Context

### Dependencies

- 运行时依赖：`akshare`（当前本地为 1.18.24）、`pandas`、`sqlalchemy[asyncio]`、`asyncpg`
- 任务系统依赖：`TaskManager` + `AsyncTask` 状态机字段（`retry_count/max_retries/timeout_seconds`）
- 数据模型依赖：`Sector.type` 必须稳定为 `industry|concept`，作为 THS 路由输入
- 接口数据依赖：THS 板块列表字段需提供 `name/code`，板块日线需提供日期与 OHLCV 字段
- 测试依赖：`pytest`、`pytest-asyncio`、`unittest.mock` 用于异步会话和 AkShare mock
- 运维依赖：人工停机窗口与数据库脚本执行权限（用于 `TRUNCATE`）

### Testing Strategy

- 最小必测集：
  - `server/tests/test_data_acquisition/test_akshare_client.py`：THS 列表映射与日线路由
  - `server/tests/test_data_init.py`：移除成分股后的板块初始化与日线初始化
  - `server/tests/test_task_system.py`：API 创建 TaskManager 任务字段一致性
  - `server/tests/test_data_updater.py`：板块路径接口契约一致
- 回归门槛：以上 4 组测试必须全部通过
- 人工验证：
  - 停机窗口手动执行清空脚本后，目标表计数全部为 0
  - 触发一次板块初始化任务并检查任务日志是否仅包含板块实体与板块日线
  - 检查管理端初始化文案与返回字段不再出现成分股语义
  - 抽样核对行业与概念板块各一条数据的日线来源路由

### Notes

#### Failure Modes & Mitigations

##### FM-01: THS 列表字段变化（`name/code` 列名变动或空值）
- 检测：字段存在性断言、空数据比例告警
- 缓解：字段别名兼容层、无效行跳过并记录、超过阈值 fail fast

##### FM-02: THS 日线接口返回异常格式（日期/价格列异常）
- 检测：标准列清单校验、类型转换错误计数
- 缓解：统一 DataFrame 映射器、行级容错与阈值失败、原始列采样日志

##### FM-03: 行业/概念路由错误（类型判定错导致调错函数）
- 检测：`sector_type` 强校验、双分支路由覆盖测试
- 缓解：模型层约束、调用前显式分支判断和路由日志

##### FM-04: 成分股移除后遗留调用导致运行时崩溃
- 检测：全仓引用扫描、主链路集成测试
- 缓解：删除接口定义与实现、同步调整调用方和测试桩、补充迁移说明

##### FM-05: 任务执行器重构引入并发竞态（重复执行/状态错乱）
- 检测：状态迁移断言、并发场景集成测试
- 缓解：任务领取原子化、执行幂等保护、重试退避与上限

##### FM-06: 一次性切换后外部源不稳定（超时/限流）
- 检测：超时率/重试率/成功率指标、失败原因分布
- 缓解：分级重试、严格限速、批处理切片与断点续跑

##### FM-07: 测试覆盖不足导致链路问题晚暴露
- 检测：覆盖率门槛 + 关键路径用例门槛、PR 强制任务链路测试
- 缓解：三层测试基线（接口/服务/任务）、失败场景回归套件

#### Reasoning via Planning Summary
- 依赖顺序：`契约` → `调用方` → `任务注册与执行` → `测试`
- 执行原则：
  - 先清空，再迁移，不保留兼容分支
  - 每阶段必须绑定可独立验证的测试集
  - 任务类型变更与测试断言同提交，防止注册漂移

## Review Notes
- Adversarial review completed
- Findings: 10 total, 8 fixed, 2 skipped (F6=undecided, F9=全局覆盖率策略不在本次迁移范围)
- Resolution approach: auto-fix
