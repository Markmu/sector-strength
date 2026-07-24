---
feat_id: "plan-01"
title: "数据层与采集"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01 数据层与采集

## 1. 功能概要

- **目标**: 建立板块资金流数据表，封装同花顺即时接口采集器，实现盘中每 1 分钟全板块采样落库，并提供管理员手动触发入口与定时任务（注释注册）。
- **完成后可观察结果**: 手动触发采集后，`sector_fund_flow` 表出现当日行业+概念的资金流采样记录（每条带 trade_date、sample_time、净额等字段）。重复触发同一采样分钟不会产生重复行（on_conflict 覆盖）。脚本 `scripts/test_fund_flow.py` 能跑通 fetcher→落库→查询链路并打印采集板块数。
- **依赖**: 无
- **关联验收标准**: [AC-11]
- **涉及架构模块**: 资金流采集器 AkshareFundFlowFetcher、采集编排 DataCollector._update_sector_fund_flow、TaskType handler、定时任务 job_manager
- **前置条件**: server/.venv 已装 akshare 1.18.75 + mini-racer 0.14.1；同花顺即时接口网络可达
- **不在范围**: 查询 API（plan-02）、前端页面（plan-03）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/sector_fund_flow.py` | SectorFundFlow ORM 模型 |
| modify | `server/src/models/__init__.py` | 注册导出 SectorFundFlow |
| create | `server/alembic/versions/2026_07_24_0100-add_sector_fund_flow_table.py` | 建表迁移 |
| create | `server/src/services/data_acquisition/akshare_fund_flow.py` | AkshareFundFlowFetcher + SectorFundFlowInfo |
| modify | `server/src/services/data_updater/collector.py` | 新增 _update_sector_fund_flow()，编入 run_daily_update() |
| modify | `server/src/services/task_handlers.py` | TaskType 新增 SYNC_SECTOR_FUND_FLOW + 注册 handler |
| modify | `server/src/services/scheduler/job_manager.py` | 新增 _sector_fund_flow_snapshot()（注释注册） |
| modify | `server/requirements.txt` | 新增 akshare>=1.18.75 |
| create | `server/scripts/test_fund_flow.py` | 采集链路验证脚本 |

## 3. 实现规格

### 后端部分

#### 1. SectorFundFlow ORM 模型（sector_fund_flow.py）

仿 `src/models/daily_market_data.py` 范式（Column 定义 + UniqueConstraint + Index）。

字段（架构 §7.2 存储视角）：
- id: Integer PK autoincrement
- trade_date: Date nullable=False index
- sample_time: DateTime nullable=False（精度到分钟，秒/微秒置零）
- sector_type: String(20) nullable=False（industry/concept）
- sector_name: String(100) nullable=False
- sector_index: Numeric(15,2) nullable
- change_percent: Numeric(10,4) nullable
- inflow: Numeric(15,2) nullable（亿元）
- outflow: Numeric(15,2) nullable（亿元）
- net_inflow: Numeric(15,2) nullable（亿元）
- company_count: Integer nullable
- leading_stock: String(50) nullable
- leading_stock_change: Numeric(10,4) nullable
- current_price: Numeric(15,2) nullable
- created_at: DateTime(timezone=True) server_default=func.now()

约束/索引：
- UniqueConstraint('trade_date','sample_time','sector_type','sector_name', name='uq_sector_fund_flow_sample')
- Index('idx_sff_date_type', 'trade_date', 'sector_type')
- Index('idx_sff_date_type_name_time', 'trade_date', 'sector_type', 'sector_name', 'sample_time')

#### 2. models/__init__.py 注册

在现有导出列表新增 `from .sector_fund_flow import SectorFundFlow`。

#### 3. Alembic 迁移

文件名遵循惯例 `2026_07_24_0100-{revision}_add_sector_fund_flow_table.py`。revision 用 12 位十六进制随机串，down_revision 指向当前 head（`dd92f496dfaf`，即最新迁移 add_stock_independent_tables）。

upgrade：`op.create_table('sector_fund_flow', ...)` 含上述所有列 + 约束 + 索引。
downgrade：`op.drop_table('sector_fund_flow')`。

验证：`cd server && .venv/bin/alembic upgrade head` 成功，表存在。

#### 4. AkshareFundFlowFetcher（akshare_fund_flow.py）

类 `AkshareFundFlowFetcher`，方法 `fetch(sector_type: str) -> list[SectorFundFlowInfo]`：
- sector_type="industry" → 调 `ak.stock_fund_flow_industry(symbol="即时")`
- sector_type="concept" → 调 `ak.stock_fund_flow_concept(symbol="即时")`
- 返回 DataFrame 列映射（同花顺列名 → SectorFundFlowInfo 字段）：
  - 序号→忽略；行业/概念→sector_name；行业指数→sector_index；行业-涨跌幅→change_percent
  - 流入资金→inflow；流出资金→outflow；净额→net_inflow；公司家数→company_count
  - 领涨股→leading_stock；领涨股-涨跌幅→leading_stock_change；当前价→current_price
- pydantic 模型 `SectorFundFlowInfo`：上述字段（不含 trade_date/sample_time，由调用方标记）

重试/限流：复用 tushare_client `_execute_with_retry` 模式（src/services/data_acquisition/tushare_client.py:100）。新建独立实例：限流间隔 0.3s、max_retries=3、指数退避。不可恢复关键词至少含空数据类异常描述。**不继承 TushareDataSource**，独立实现 `_execute_with_retry` 或抽公共 mixin。

行业与概念调用之间强制 sleep（≥1s）避免风控。

#### 5. collector._update_sector_fund_flow()

仿 `_update_market_data`（src/services/data_updater/collector.py:218）落库范式，但用 `on_conflict_do_update`（盘中同分钟重采需覆盖）：

```
fetcher = AkshareFundFlowFetcher()
now = datetime.now()
trade_date = now.date()
sample_time = now.replace(second=0, microsecond=0)  # 精度到分钟
for sector_type in ("industry", "concept"):
    items = fetcher.fetch(sector_type)
    for item in items:
        stmt = pg_insert(SectorFundFlow).values(
            trade_date=trade_date, sample_time=sample_time,
            sector_type=sector_type, **item.dict()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_sector_fund_flow_sample',
            set_=dict(inflow=stmt.excluded.inflow, outflow=..., net_inflow=..., ...)
        )
        await session.execute(stmt)
    await session.commit()
```

在 `run_daily_update()` 末尾追加调用 `await self._update_sector_fund_flow()`。

#### 6. TaskType + handler（task_handlers.py）

- `TaskType` 枚举新增 `SYNC_SECTOR_FUND_FLOW = "sync_sector_fund_flow"`（仿 SYNC_BROKER_RECOMMEND，task_handlers.py:66）
- 注册 handler：`@TaskRegistry.register(TaskType.SYNC_SECTOR_FUND_FLOW)` async def，内部实例化 DataCollector，调 `_update_sector_fund_flow()`
- **执行验证验收（AC-11）**：触发任务 → 等待完成 → 查 sector_fund_flow 表有新增记录

#### 7. job_manager 定时任务（注释注册）

新增 `_sector_fund_flow_snapshot()` 方法（仿 `_daily_data_update`），内部调 `_update_sector_fund_flow`。在 `_register_jobs()` 按 ADR-6 惯例**注释注册**（交易时段每 1 分钟 IntervalTrigger(minutes=1)），注释块写明取消注释即启用。

#### 8. requirements.txt

新增 `akshare>=1.18.75`。

#### 9. scripts/test_fund_flow.py

仿 `scripts/test_ths_sectors.py`：实例化 fetcher → fetch industry/concept → 调 collector._update_sector_fund_flow → 查表打印条数。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 SectorFundFlow ORM 模型 | backend | done | sector_fund_flow.py |
| 2 | models/__init__.py 注册导出 | backend | done | |
| 3 | 创建 Alembic 迁移并 upgrade head | backend | done | 验证建表成功 |
| 4 | 实现 AkshareFundFlowFetcher | backend | done | 含重试/限流 |
| 5 | collector 新增 _update_sector_fund_flow 并编入 run_daily_update | backend | done | on_conflict_do_update |
| 6 | TaskType 新增成员 + 注册 handler | backend | done | SYNC_SECTOR_FUND_FLOW |
| 7 | job_manager 新增定时任务（注释注册） | backend | done | ADR-6 惯例 |
| 8 | requirements.txt 新增 akshare | backend | done | |
| 9 | 创建 test_fund_flow.py 验证脚本 | backend | done | 跑通全链路 |

## 5. 验收标准

### 采集功能验收
- [x] AC-11 手动触发采集：通过 TaskType handler 触发 SYNC_SECTOR_FUND_FLOW，任务 status=completed，sector_fund_flow 表有当日行业+概念记录
- [x] 同一采样分钟重复触发不产生重复行（on_conflict 覆盖生效）
- [x] test_fund_flow.py 脚本运行成功，打印采集板块数（行业≈90、概念≈386）
- [x] alembic upgrade head 成功，表结构含唯一约束与索引

### 执行验证验收（task handler 必填）
- [x] 触发 SYNC_SECTOR_FUND_FLOW 任务 → 等待任务完成（status=completed）→ 查询 sector_fund_flow 表确认 trade_date/sample_time/sector_type/sector_name/net_inflow 字段值正确

## 6. 验证命令

```bash
cd server
# 迁移
.venv/bin/alembic upgrade head
# 采集链路脚本
.venv/bin/python scripts/test_fund_flow.py
# 单元测试（如有）
.venv/bin/python -m pytest tests/ -k "fund_flow" -v
```

## 7. 交接上下文

- **架构章节**: §6.1 采集链路、§4.2 采集器/采集编排模块、ADR-1/2/3/6
- **相关代码**: collector.py（落库范式）、tushare_client.py:100（重试范式）、task_handlers.py:28（TaskType）、init_funds.py（admin 触发范式）
- **契约/数据对象**: SectorFundFlow ORM、SectorFundFlowInfo pydantic、唯一约束 uq_sector_fund_flow_sample
- **下游消费方**: plan-02 查询 API 依赖 sector_fund_flow 表

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（模型→迁移→fetcher→collector→handler→job_manager）
- **验证失败排查方向**: alembic 失败检查 down_revision；fetcher 失败检查 akshare/mini-racer 是否装在 .venv；落库失败检查唯一约束名
- **允许修改的额外文件**: 无
- **暂停条件**: 同花顺接口持续不可用（网络问题）时暂停，记录现象请求确认
- **E2E 不适用说明**: 纯后端采集功能，无 UI；用 test_fund_flow.py 脚本 + task handler 执行验证替代 E2E
- **风险备注**: sample_time 必须精度到分钟（秒/微秒置零），否则同分钟重采会新增而非覆盖

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 同花顺接口部分板块失败 | 成功部分落库，失败跳过，日志记录 | done |
| 同花顺接口整体不可用 | 重试耗尽后记录日志，不影响已有数据 | done |
| 同一采样分钟重复触发 | on_conflict_do_update 覆盖最新值 | done |
| 非交易时段触发 | 仍可采集（取上一交易日收盘定稿值），不报错 | done |
