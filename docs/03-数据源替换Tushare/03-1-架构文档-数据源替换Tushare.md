---
workflow_type: arch-gen
status: review_ready
input_documents:
  - 03-0-需求设计-数据源替换Tushare.md
open_questions: []
---

# 03-1 架构设计：数据源替换 Tushare

_本文件只保留当前版本真正影响实现的架构决策、边界和契约。_

## 1. 系统摘要

将数据获取层从 AkShare（爬虫）替换为 Tushare（SDK），解决接口不稳定、无认证、数据获取不可靠的问题。核心闭环：**Factory → DataSource → Pydantic Model → DB**。通过环境变量切换数据源，保留 AkShare 作为可回退后备，用户使用流程无变化。

## 2. 范围、非目标与成功标准

### 2.1 范围

- 实现 `TushareDataSource`，覆盖 `BaseDataSource` 的 4 个抽象方法 + `get_trading_calendar`
- 将 `get_trading_calendar` 纳入 `BaseDataSource` 抽象接口
- 引入 `DataSourceFactory`，基于环境变量 `DATA_SOURCE_TYPE` 选择数据源实例
- 解耦 `TradingCalendar` 对 `AkShareDataSource` 的硬编码依赖
- 替换 5 个服务文件中对 `AkShareDataSource` 的直接引用
- 新增 Tushare 相关环境变量（token、服务地址、请求间隔等）

### 2.2 明确不做

- 前端 UI 变更
- 数据库结构变更
- 新增数据维度或指标
- 修改计算逻辑（均线、强度计算等）
- 删除 AkShare 实现
- 修改 API 路由或接口定义
- 引入 DI 框架（如 dependency-injector）

### 2.3 成功标准

| 指标 | 首版目标 |
|------|---------|
| 5 个数据获取方法全部可用 | 功能正常完成，无数据获取异常 |
| 环境变量切换数据源 | 切换后全链路正常，无需改代码 |
| TradingCalendar 解耦 | 切换数据源后交易日历同步切换 |
| 错误重试 | 自动重试 3 次（指数退避），耗尽后返回明确错误 |

### 2.4 验收标准承接矩阵

| AC-ID | PRD 原文摘要 | 承接模块 | 关键链路 / 状态 | 风险 / 降级说明 |
|-------|-------------|---------|----------------|----------------|
| AC-01 | 交易日历获取 | TushareDataSource.get_trading_calendar | 调用 trade_cal 接口 → 过滤休市日 → List[date] | Tushare 积分不足时该接口需 120 积分，否则返回错误 |
| AC-02 | 股票列表获取 | TushareDataSource.get_stock_list | 调用 stock_basic 接口 → StockInfo[] | 无特殊风险 |
| AC-03 | 板块列表获取 | TushareDataSource.get_sector_list | 调用 ths_index 接口 → SectorInfo[] | ths_index 需 6000 积分，是积分门槛最高的接口 |
| AC-04 | 个股日线行情获取 | TushareDataSource.get_daily_data | 调用 pro_bar(adj='qfq') → DailyQuote[] | 前复权通过 pro_bar 内置参数实现 |
| AC-05 | 板块日线行情获取 | TushareDataSource.get_sector_daily_data | 调用 ths_daily 接口 → DailyQuote[] | 需先通过板块名称查找板块代码 |
| AC-06 | 数据源可切换 | DataSourceFactory + env var | 读取 DATA_SOURCE_TYPE → 实例化对应 DataSource | AkShare 代码保留，可随时回退 |
| AC-07 | 数据获取失败处理 | TushareDataSource._execute_with_retry | 指数退避重试 3 次 → 耗尽后抛出 RetryExhaustedError | 与现有 AkShare 重试机制对齐 |

## 3. 用户流程与状态

### 3.1 主流程

```
管理员触发数据初始化/更新
  → DataSourceFactory 创建 TushareDataSource 实例
  → TushareDataSource.get_trading_calendar() 获取交易日历
  → TushareDataSource.get_stock_list() 获取股票列表
  → TushareDataSource.get_sector_list() 获取板块列表
  → TushareDataSource.get_daily_data() 获取个股日线（前复权）
  → TushareDataSource.get_sector_daily_data() 获取板块日线
  → 数据写入数据库，计算和展示正常进行
```

### 3.2 关键分支

| 分支名 | 入口/触发条件 | 架构处理方式 |
|--------|-------------|-------------|
| Tushare 不可用 | 认证失败/网络超时/服务宕机 | _execute_with_retry 自动重试 3 次（指数退避），耗尽后返回错误 |
| 积分不足 | 调用 ths_index 等高积分接口 | Tushare 返回权限错误，DataSource 转换为 DataFetchError |
| 频率超限 | 请求间隔低于积分对应限制 | _enforce_rate_limit 控制请求间隔，内置等待 |
| 回退 AkShare | 管理员修改 DATA_SOURCE_TYPE=akshare | DataSourceFactory 实例化 AkShareDataSource，全链路切回 |

### 3.3 状态机

本需求为纯替换，不引入新的业务状态流转。数据源切换为配置级别操作，不涉及运行时状态变化。

## 4. 系统上下文与模块职责

### 4.1 系统上下文

变更范围仅限后端数据获取层（虚线框内），上层服务和前端无感知：

```
┌─────────────────────────────────────────────────┐
│ 后端服务层                                        │
│                                                   │
│  DataInitService  DataUpdateService  DataCollector │
│  DataQualityChecker  TradingCalendar              │
│          │              │              │           │
│          └──────────────┼──────────────┘           │
│                         ▼                          │
│               ┌─────────────────┐                  │
│               │ DataSourceFactory│ ← env var       │
│               └────────┬────────┘                  │
│                        │                           │
│            ┌───────────┼───────────┐                │
│            ▼                       ▼                │
│   ┌─────────────────┐  ┌──────────────────┐        │
│   │TushareDataSource│  │AkShareDataSource │        │
│   │  (新增)          │  │  (保留不变)       │        │
│   └────────┬────────┘  └────────┬─────────┘        │
└────────────┼─────────────────────┼─────────────────┘
             ▼                     ▼
       Tushare API           AkShare 爬虫
```

### 4.2 模块职责

| 模块 | 职责 | 上游输入 | 下游输出 |
|------|------|---------|---------|
| TushareDataSource | 封装 Tushare SDK 调用，字段映射，重试/限流 | BaseDataSource 方法参数 | Pydantic Model（StockInfo / SectorInfo / DailyQuote / List[date]） |
| DataSourceFactory | 根据 `DATA_SOURCE_TYPE` 环境变量创建对应数据源实例 | 环境变量 | BaseDataSource 子类实例 |
| BaseDataSource（改造） | 新增 `get_trading_calendar` 抽象方法 | — | — |
| TradingCalendar（改造） | 移除硬编码 AkShareDataSource 依赖 | DataSourceFactory 提供的数据源 | List[date]（交易日列表） |

验证 `TradingCalendar` 改造：当前 `trading_calendar.py:24` 硬编码 `AkShareDataSource()`，改造后调用 `DataSourceFactory.create()` 获取数据源实例，再调用 `get_trading_calendar()`。交易日列表的缓存逻辑不变，降级逻辑（周末判断兜底）不变。

### 4.3 需要刻意避免的过度设计

| 不引入 | 原因 |
|--------|------|
| DI 框架 | 仅 2 个数据源实现，简单工厂足够 |
| 数据源配置表 | 环境变量满足需求，无需数据库存储 |
| 数据源健康检查端点 | 现有 health_check 方法已够用 |
| 数据源指标监控 | 首版只需日志，不需要 Prometheus 指标 |
| 抽象中间层 / 适配器层 | BaseDataSource 已是抽象层，TushareDataSource 直接实现即可 |

## 5. 关键架构决策（ADR）

### ADR-1：数据源选择通过环境变量 + 简单工厂

- **选择**：新增 `DATA_SOURCE_TYPE` 环境变量（`tushare` / `akshare`），`DataSourceFactory.create()` 读取后实例化对应类
- **理由**：仅 2 个实现，不需要 DI 框架或插件注册机制；环境变量已在项目中广泛使用（`.env` + `os.getenv`），团队熟悉
- **风险与对策**：环境变量拼错导致启动失败 → Factory 内做白名单校验，非法值直接报错并提示可选值

### ADR-2：get_trading_calendar 纳入 BaseDataSource 抽象

- **选择**：在 `BaseDataSource` 中新增 `get_trading_calendar() -> List[date]` 抽象方法，AkShareDataSource 中已有实现无需改动
- **理由**：交易日历是数据源提供的数据之一，应跟随数据源切换；当前 TradingCalendar 硬编码依赖 AkShare 就是由于该方法不在抽象层内
- **风险与对策**：AkShareDataSource 已有该方法实现，无破坏性变更风险

### ADR-3：Tushare 使用 pro_bar 获取前复权数据

- **选择**：个股日线通过 `pro_bar(symbol, start_date, end_date, adj='qfq', api=pro_api)` 获取前复权数据
- **理由**：pro_bar 内部合并 daily + adj_factor，直接返回前复权价格，无需手动计算；Tushare 官方推荐方式
- **风险与对策**：pro_bar 单次返回数据量有限（约 5000 行）→ 日期范围过大时分批获取

### ADR-4：板块数据通过同花顺接口获取

- **选择**：板块列表用 `ths_index`，板块日线用 `ths_daily`，通过 `is_type='行业/概念'` 区分板块类型
- **理由**：Tushare 的同花顺接口数据结构与系统现有板块分类（industry/concept）最匹配
- **风险与对策**：ths_index / ths_daily 需 6000 积分 → 在启动时检测积分不足给出明确提示

### ADR-5：请求频率控制内置在 TushareDataSource

- **选择**：TushareDataSource 内置 `_enforce_rate_limit()`，通过 `TUSHARE_API_INTERVAL` 环境变量配置最小请求间隔（默认 0.5 秒）
- **理由**：Tushare 积分制对请求频率有硬限制，不同积分等级限制不同；内置限流与 AkShareDataSource 现有模式一致
- **风险与对策**：默认间隔可能对低积分账户不够 → 环境变量可调

### ADR-6：支持自定义 Tushare 服务地址

- **选择**：通过 `TUSHARE_API_URL` 环境变量配置 Tushare 服务地址，默认为 `api.tushare.pro`
- **理由**：部署环境可能在内网或使用 Tushare 镜像服务（如社区自建节点），默认官方地址 `api.tushare.pro` 可能存在网络延迟或不可达；通过环境变量指定地址可适配不同网络环境，无需修改代码
- **风险与对策**：自定义地址可能不兼容 → 健康检查时验证连接可用性

### 5.x 待确认问题

无。以下问题已在 PRD 决策记录中确认：
- Q1（Tushare SDK 自定义服务地址支持）：通过 `tushare.pro_api(token, api_url)` 参数传入
- Q2（get_trading_calendar 归属）：纳入 BaseDataSource 抽象（ADR-2）
- Q3（字段映射策略）：TushareDataSource 内部处理（ADR-3）
- Q4（频率限制参数）：通过环境变量可配（ADR-5）

## 6. 运行链路

### 6.1 数据初始化链路

1. 管理员调用 `POST /api/admin/init/all`
2. `DataInitService.__init__` 调用 `DataSourceFactory.create()` 获取数据源实例
3. 调用 `data_source.get_trading_calendar()` 获取交易日历
4. 调用 `data_source.get_sector_list()` 获取板块列表 → 写入 Sector 表
5. 调用 `data_source.get_stock_list()` 获取股票列表 → 写入 Stock 表
6. 遍历板块，调用 `data_source.get_sector_daily_data()` 获取板块历史日线 → 写入 DailyMarketData 表
7. 遍历股票，调用 `data_source.get_daily_data()` 获取个股历史日线 → 写入 DailyMarketData 表

这条链路的实现原则：
- DataInitService 不感知具体数据源类型，仅依赖 BaseDataSource 抽象
- 每次调用 data_source 方法时自动触发限流检查和重试机制

### 6.2 TradingCalendar 交易日判断链路

1. `TradingCalendar._get_trading_days()` 调用 `DataSourceFactory.create()` 获取数据源
2. 调用 `data_source.get_trading_calendar()` 获取交易日列表
3. 缓存至 `self._cache`（当日有效）
4. 后续调用直接读缓存

这条链路的实现原则：
- TradingCalendar 不再 import AkShareDataSource，改为依赖 DataSourceFactory
- 缓存和降级逻辑（获取失败时用周末判断兜底）保持不变

### 6.3 数据源切换链路

1. 管理员修改 `.env` 中 `DATA_SOURCE_TYPE=akshare`
2. 重启服务
3. DataSourceFactory.create() 读取新环境变量，创建 AkShareDataSource 实例
4. 全部服务自动使用新数据源

这条链路的实现原则：
- 切换是配置级操作，不涉及代码修改
- DataSourceFactory 每次调用 `create()` 时读取环境变量（不缓存实例），确保重启后生效

## 7. 领域对象与关键契约

### 7.1 核心对象

| 对象 | Source of Truth | Owner | 用途 |
|------|----------------|-------|------|
| StockInfo | Tushare stock_basic / AkShare | DataSource | 股票列表获取的统一输出 |
| SectorInfo | Tushare ths_index / AkShare | DataSource | 板块列表获取的统一输出 |
| DailyQuote | Tushare pro_bar / ths_daily / AkShare | DataSource | 日线行情获取的统一输出 |
| BaseDataSource | 抽象层 | 架构 | 数据源切换的契约基础 |

### 7.2 Tushare 字段映射

TushareDataSource 内部将 Tushare 原始字段映射到 Pydantic 模型，上层服务无感知：

**stock_basic → StockInfo**

| Tushare 字段 | Pydantic 字段 | 转换规则 |
|-------------|-------------|---------|
| ts_code | symbol | 截取前 6 位（如 `000001.SZ` → `000001`） |
| name | name | 直接映射 |
| market / exchange | market | `1=SH, 0=SZ, 2=BJ`（根据 ts_code 后缀也可：`.SZ`=SZ, `.SH`=SH, `.BJ`=BJ） |
| industry | industry | 直接映射 |
| list_date | list_date | 格式 `YYYYMMDD` → date |

**ths_index → SectorInfo**

| Tushare 字段 | Pydantic 字段 | 转换规则 |
|-------------|-------------|---------|
| ts_code | code | 直接映射（如 `881101.TI`） |
| name | name | 直接映射 |
| exchange / is_type | type | `ths_index(exchange='A', type='行业')` → `industry`；`ths_index(exchange='A', type='概念')` → `concept` |

**pro_bar(adj='qfq') → DailyQuote（个股）**

输入转换 — symbol → ts_code：Tushare pro_bar 接受 `ts_code` 参数（格式如 `000001.SZ`），系统内部传递纯数字 `symbol`，需按首位数字拼接市场后缀：`6→.SH`、`0/3→.SZ`、`8/4→.BJ`。

| Tushare 字段 | Pydantic 字段 | 转换规则 |
|-------------|-------------|---------|
| ts_code | symbol | 截取前 6 位 |
| trade_date | trade_date | 格式 `YYYYMMDD` → date |
| open | open | 直接映射（float） |
| high | high | 直接映射 |
| low | low | 直接映射 |
| close | close | 直接映射 |
| vol | volume | 直接映射（股） |
| amount | amount | 直接映射（千元 → 元，需 ×1000） |
| turnover_rate | turnover | 直接映射 |

**ths_daily → DailyQuote（板块）**

| Tushare 字段 | Pydantic 字段 | 转换规则 |
|-------------|-------------|---------|
| ts_code | symbol | 直接映射 |
| trade_date | trade_date | 格式 `YYYYMMDD` → date |
| open | open | 直接映射 |
| high | high | 直接映射 |
| low | low | 直接映射 |
| close | close | 直接映射 |
| vol | volume | 直接映射 |

**trade_cal → get_trading_calendar**

| Tushare 字段 | 输出 | 转换规则 |
|-------------|------|---------|
| cal_date | date | 格式 `YYYYMMDD` → date，仅保留 `is_open=1` 的记录 |

### 7.3 API 边界

本需求不新增或修改任何 API 端点。所有变更限于后端内部实现。

### 7.4 状态流转

不涉及新的状态流转。

### 7.5 数据边界

| 存储层 | 职责 | 变更说明 |
|--------|------|---------|
| 环境变量（.env） | 数据源配置 | 新增 `DATA_SOURCE_TYPE`、`TUSHARE_TOKEN`、`TUSHARE_API_URL`、`TUSHARE_API_INTERVAL` |
| BaseDataSource 抽象层 | 数据源契约 | 新增 `get_trading_calendar` 抽象方法 |
| Pydantic 模型层 | 数据格式 | 不变（StockInfo / SectorInfo / DailyQuote） |
| PostgreSQL | 业务数据 | 不变（DailyMarketData / Sector / Stock 表结构不变） |

### 7.6 命名与标识规则

| 规则 | 说明 |
|------|------|
| 数据源类型标识 | `tushare` / `akshare`（小写，用于环境变量） |
| 新文件命名 | `tushare_client.py`（与 `akshare_client.py` 平行） |
| 工厂类命名 | `DataSourceFactory`（放在 `data_acquisition/` 目录下） |
| 环境变量前缀 | Tushare 相关变量使用 `TUSHARE_` 前缀 |
| source_name | `"Tushare"`（传给 BaseDataSource.__init__，用于日志） |

## 8. 非功能需求、风险与运行策略

### 8.1 性能与吞吐量目标

| 指标 | 目标 | 说明 |
|------|------|------|
| 单次 API 调用延迟 | < 5s | Tushare API 响应时间 + 网络延迟 |
| 股票列表获取 | < 30s | 约 5000 只股票 |
| 全量历史数据初始化 | 可接受 | 取决于股票数量和日期范围，不设硬性目标 |

### 8.2 可靠性、错误处理与降级策略

| 级别 | 条件 | 系统行为 |
|------|------|---------|
| L1 正常 | Tushare 可用 | 使用 Tushare 获取数据 |
| L2 重试 | 单次请求失败 | 自动重试 3 次（指数退避，间隔 1s / 2s / 4s） |
| L3 降级 | Tushare 持续不可用 | 重试耗尽后返回 RetryExhaustedError，上层记录错误日志 |
| L4 回退 | 管理员主动切换 | 修改 `DATA_SOURCE_TYPE=akshare` 并重启，回退到 AkShare |

### 8.3 安全与反滥用策略

| 项目 | 首版策略 |
|------|---------|
| Tushare Token 存储 | 环境变量，不硬编码，不提交到版本控制 |
| Token 传输 | 仅服务端使用，不暴露给前端 |
| 日志脱敏 | 日志中不输出 Token 值 |

### 8.4 成本控制预期

| 模块 | 预估成本 | 首版控制策略 |
|------|---------|-------------|
| Tushare API 调用 | 免费（积分制，当前账户积分满足需求） | 内置请求间隔控制，避免无谓请求 |

### 8.5 可观测性

- 数据源切换时记录 INFO 日志：`"数据源切换为: {source_name}"`
- 每次请求记录 DEBUG 日志：`"[Tushare] 请求 {api_name}，耗时 {ms}ms"`
- 请求失败记录 WARNING 日志：`"[Tushare] 请求失败，重试 {n}/{max}"`
- 重试耗尽记录 ERROR 日志：`"[Tushare] 重试耗尽: {error}"`

### 8.6 主要风险

| 风险 | 影响 | 缓解方式 |
|------|------|---------|
| Tushare 积分不足，ths_index 接口需 6000 积分 | 无法获取板块数据 | 启动时调用 health_check 验证积分，不足时日志告警；保留 AkShare 回退路径 |
| Tushare 服务维护/宕机 | 数据更新中断 | 指数退避重试 + 环境变量快速回退 |
| Tushare 接口返回格式变更 | 数据解析失败 | Pydantic 模型验证 + 异常捕获 + 明确错误日志 |
| pro_bar 前复权数据与 AkShare 数据存在差异 | 历史数据重初始化后计算结果可能变化 | 切换后建议触发全量历史数据重初始化 |

## 9. 实施方案

### Phase A：抽象层扩展与工厂

**后端**

1. `server/src/services/data_acquisition/base.py` — 新增 `get_trading_calendar(self) -> List[date]` 抽象方法
2. `server/src/services/data_acquisition/__init__.py` — 新增 `DataSourceFactory` 类：
   - `create() -> BaseDataSource`：读取 `DATA_SOURCE_TYPE`，白名单校验后实例化对应类
   - 非法值抛出 `ValueError` 并提示可选值 `tushare` / `akshare`
3. `.env.example` — 新增 `DATA_SOURCE_TYPE=tushare`、`TUSHARE_TOKEN`、`TUSHARE_API_URL`、`TUSHARE_API_INTERVAL`

验证目标：`DataSourceFactory.create()` 在 `tushare` / `akshare` 两种配置下均能返回正确实例；非法值报错。

### Phase B：TushareDataSource 实现

**后端**

4. `server/src/services/data_acquisition/tushare_client.py` — 新建文件，实现 `TushareDataSource(BaseDataSource)`：
   - `__init__`：从环境变量读取 token、api_url、api_interval 等配置
   - `_get_pro_api()`：延迟初始化 `tushare.pro_api(token, api_url)`，启动时验证连接
   - `_enforce_rate_limit()`：请求间隔控制（与 AkShareDataSource 模式一致）
   - `_execute_with_retry()`：指数退避重试（与 AkShareDataSource 模式一致）
   - `get_trading_calendar()`：调用 `trade_cal(exchange='SSE', is_open='1')` → List[date]
   - `get_stock_list()`：调用 `stock_basic(exchange='', list_status='L')` → List[StockInfo]（字段映射见 7.2）
   - `get_sector_list(sector_type)`：调用 `ths_index(exchange='A')`，按 type 过滤 → List[SectorInfo]
   - `get_daily_data(symbol, start, end)`：先将 symbol 按 `6→.SH, 0/3→.SZ, 8/4→.BJ` 拼接为 ts_code，再调用 `pro_bar(ts_code, start, end, adj='qfq')` → List[DailyQuote]（amount 需 ×1000）
   - `get_sector_daily_data(sector_name, sector_type, start, end)`：先通过板块名称在 ths_index 结果中查找 ts_code，再调用 `ths_daily(ts_code, start, end)` → List[DailyQuote]
   - `health_check()`：override BaseDataSource.health_check()，调用 `trade_cal(limit=1)` 验证连接（比默认实现调用 get_stock_list 更轻量）

验证目标：5 个数据获取方法 + health_check 均可正常调用，返回符合 Pydantic 模型的数据。

### Phase C：服务层解耦与替换

**后端**

5. `server/src/services/trading_calendar.py` — 移除 `from src.services.data_acquisition.akshare_client import AkShareDataSource`；`_get_trading_days` 中 `source = AkShareDataSource()` 改为 `source = DataSourceFactory.create()`
6. `server/src/services/data_init.py` — 移除 `from ...akshare_client import AkShareDataSource`；`self.ak_source = AkShareDataSource()` 改为 `self.ak_source = DataSourceFactory.create()`
7. `server/src/services/data_update.py` — 同上替换
8. `server/src/services/data_updater/collector.py` — 移除 AkShare 导入；新增 `__init__` 中 `self._data_source = DataSourceFactory.create()` 创建一次实例并复用（保留限流状态）；`_update_sectors`、`_update_stocks`、`_update_market_data` 中的 `data_source = AkShareDataSource()` 统一改为 `self._data_source`
9. `server/src/services/monitoring/data_quality.py` — `self._data_source = AkShareDataSource()` 改为 `DataSourceFactory.create()`

验证目标：`DATA_SOURCE_TYPE=tushare` 时全链路使用 Tushare；`DATA_SOURCE_TYPE=akshare` 时回退到 AkShare，行为与改造前一致。

## 10. 架构结论

核心判断：这是一个数据获取层的替换改造，不涉及业务逻辑变更。通过将 `get_trading_calendar` 纳入 `BaseDataSource` 抽象并引入 `DataSourceFactory`，所有服务对数据源的依赖统一收敛到工厂方法，消除了 5 处硬编码。TushareDataSource 内部封装字段映射和频率控制，上层服务完全无感知。

设计原则：
- **最小侵入**：仅改 5 个服务文件的 import 和实例化，不改变任何业务逻辑
- **可回退**：AkShare 代码保留不变，环境变量一行切换
- **对齐现有模式**：重试机制、限流策略与 AkShareDataSource 保持一致

演进方向：未来如需新增数据源（如东方财富），只需新增一个 `DataSource` 子类并在工厂中注册，无需修改服务层代码。
