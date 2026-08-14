---
feat_id: "plan-02"
title: "全市场量价采集适配器"
dimension: backend
phase: 1
status: done
depends_on: ["plan-01"]
---

# plan-02: 全市场量价采集适配器

## 功能概要

- **目标**: 扩展 `TushareDataSource`：参数化 `daily` 分页器（单日模式 + 历史窗口模式）、当日 `suspend_d` 停牌查询、L/D/P/G 四状态生命周期分页拉取、按代码分块的未复权前收盘窗口查询；配套领域模型。**明确不复用**现有逐股 qfq `get_daily_data()`（tushare_client.py:362-422）。
- **完成后可观察结果**: 给定一个交易日，适配器能一次拿全沪深北全市场未复权行情（约 5500 行，自动 3000/页翻页并有硬停止守卫）；给定一批代码与时间窗口，能返回窗口内仅属批次代码的未复权行情；能返回当日停牌记录与 L/D/P/G 生命周期全集。任何分页异常（签名重复、满页无新 key、页数超限、跨页重复）抛出包含计数信息的完整性错误，而不是静默截断或死循环。
- **依赖**: plan-01（`data_acquisition/models.py` / `base.py` / `tushare_client.py` 同文件顺序编辑，避免并行冲突）
- **关联验收标准**: [AC-01]（原始数据获取）、[AC-07]（缺失/重复检测原料）、[AC-13]（停牌证据与前收盘来源）
- **涉及架构模块**: 采集与本地日历适配（架构 §4.2 模块 1）
- **前置条件**: plan-01 已合并；`TUSHARE_TOKEN` 有效（真实冒烟）。
- **不在范围**: 指标计算与落库（plan-03）；任务编排（plan-04/05）；`get_trading_calendar_range`（plan-01 已交付）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_acquisition/models.py` | 新增 MarketDailyQuote / SuspensionRecord / LifecycleStock |
| modify | `server/src/services/data_acquisition/base.py` | 新增 4 个抽象方法 |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 共享分页器 + 4 个实现 |
| create | `server/tests/services/data_acquisition/test_tushare_market_daily.py` | 分页/校验/单位测试（mock DataApi） |

## 实现规格

### 后端部分

#### 1. 领域模型（架构 §7.1）

`data_acquisition/models.py` 新增（数值一律 Decimal）：

- `MarketDailyQuote { ts_code: str; trade_date: date; close: Decimal; pre_close: Optional[Decimal]; vol: Decimal; amount: Decimal }`（vol 单位=手，amount 单位=千元，保持 Tushare 原始单位，转换在 plan-03）
- `SuspensionRecord { ts_code: str; suspend_type: str; suspend_timing: Optional[str] }`
- `LifecycleStock { ts_code: str; exchange: str; list_status: str; name: Optional[str]; list_date: Optional[date]; delist_date: Optional[date] }`

#### 2. BaseDataSource 抽象方法

```python
@abstractmethod
def get_market_daily_quotes(self, trade_date: date, expected_count: int) -> List[MarketDailyQuote]
@abstractmethod
def get_close_quotes_in_window(self, ts_codes: List[str], window_start: date, window_end: date) -> List[MarketDailyQuote]
@abstractmethod
def get_suspensions(self, trade_date: date) -> List[SuspensionRecord]
@abstractmethod
def get_lifecycle_stocks(self) -> List[LifecycleStock]
```

`expected_count` 用于单日模式硬页数上限（架构 §6.1.3），由调用方从生命周期快照传入。

#### 3. 共享参数化分页器（ADR-1 / §6.1.3 / §6.1.6）

TushareDataSource 内新增私有分页引擎，两模式共用守卫、独享谓词：

- **共同守卫**（每页校验）：
  - 页签名（首行 ts_code + 行数 + offset 的元组）重复 → `MarketDataIntegrityError`
  - 满页（rows==3000）但新增 key 数为 0 → `MarketDataIntegrityError`
  - 跨页出现重复 ts_code → 记为完整性错误（**禁止 drop_duplicates 静默修复**，架构 §6.1 实现原则）
  - 请求页数 > 硬上限 → `MarketDataIntegrityError`
  - 每页调用走 `_enforce_rate_limit`（0.3s 节流）+ `_execute_with_retry`（3 次退避，非可重试关键字立即失败）
- **单日模式** `get_market_daily_quotes(trade_date, expected_count)`：
  - `pro.daily(trade_date=YYYYMMDD, fields='ts_code,trade_date,close,pre_close,vol,amount', limit=3000, offset=...)`
  - 每行校验 `trade_date == T`；硬页数 = `ceil(expected_count/3000)+1`（含尾部探测页）
  - 首张 0 行页：由本方法返回空列表，由**调用方（plan-03）判为全市场空并失败**；至少一张合法满页后的 0 行页 = 正常终止
- **历史模式** `get_close_quotes_in_window(ts_codes, window_start, window_end)`：
  - 批次内代码（≤100/批，分块由调用方做，本方法整批一次传参或按接口上限再内部分块）；`pro.daily(ts_code=逗号拼接或分块, start_date=..., end_date=...)` 分页
  - 每行校验：`window_start <= trade_date <= window_end` 且 `trade_date < T`（T=window_end+1 语义由调用方保证窗口止于 T-1）且 ts_code ∈ 批次
  - 最大候选行 = `batch_size × window_calendar_days`（内部按 `(window_end-window_start).days+1` 计算）；硬页数 = `ceil(最大候选行/3000)+1`
  - **首张空页 ≠ 失败**：表示该窗口无命中，返回空列表，由调用方推进更早窗口

#### 4. 数值构建与校验（架构 §6.1.4）

- 每行以 `Decimal(str(value))` 建数值（DataFrame 值先转 str），**禁止 binary float 累加路径**
- 校验：Decimal `is_finite()`、`close > 0`、`vol >= 0`、`amount >= 0`；任一非法 → `MarketDataIntegrityError`（含 ts_code 与字段值）

#### 5. suspend_d 查询（ADR-3）

`get_suspensions(trade_date)`：`pro.suspend_d(suspend_date=YYYYMMDD)`（不传 fields，取 Provider 原生 schema——实测显式请求 `suspend_date` 字段只会得到全空列），忠实返回 Provider 全量行、不做日期/类型过滤（原始数据保真——实测上游忽略 `suspend_date` 查询过滤，任意日期返回同一批跨约 300 个日期的全量行；且代理把停牌日期列命名为 `trade_date`，官方 schema 为 `suspend_date`，适配器双键兼容并归一化为 `SuspensionRecord.suspend_date`）；每行日期按 YYYYMMDD 解析，失败抛完整性错误；调用方（plan-03）必须按 `record.suspend_date == trade_date` 客户端过滤后才能作为当日停牌证据，`suspend_type='S'` 与全天判定同样由 plan-03 做；空结果返回空列表。

#### 6. L/D/P/G 生命周期拉取（ADR-2）

`get_lifecycle_stocks()`：对 `list_status in ('L','D','P','G')` 分别调用 `pro.stock_basic(exchange='', list_status=..., fields='ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,delist_date')` 并分页（参照 `get_fund_list` 的 offset/limit while 循环，tushare_client.py:572）；合并四状态返回。**不写库**（upsert/set-diff 在 plan-03）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新增 3 个领域模型 | backend | done | Decimal 数值字段 |
| 2 | BaseDataSource 新增 4 个抽象方法 | backend | done | 测试替身补最小实现 |
| 3 | 实现共享分页引擎与守卫 | backend | done | 页签名/新 key/重复/硬页数 |
| 4 | 实现单日模式 get_market_daily_quotes | backend | done | 首空页语义交调用方 |
| 5 | 实现历史模式 get_close_quotes_in_window | backend | done | 首空页=窗口无命中 |
| 6 | 实现 get_suspensions 与 get_lifecycle_stocks | backend | done | 四状态分页合并 |
| 7 | 编写 test_tushare_market_daily.py | backend | done | mock DataApi 覆盖下述场景 |

## 验收标准

### 后端验收

- [ ] AC-01（原料）单日模式对完整交易日返回全市场行（真实冒烟 >5000 行），每行含 close/vol/amount Decimal 值
- [ ] AC-07（原料）页签名重复、满页无新增 key、页数超过 `ceil(expected/3000)+1`、跨页重复 ts_code 四种场景均抛 `MarketDataIntegrityError`，错误信息含页数与计数
- [ ] exact-3000 页 + 空尾页正常终止；exact-6000 两满页 + 空尾页正常终止；单页 <3000 直接终止
- [ ] 历史模式：窗口内返回行全部满足日期谓词与批次归属；首张空页返回空列表不抛错；越界行抛完整性错误
- [ ] 数值校验：close=0 / 负值 / NaN / Infinity 抛错；`Decimal(str(...))` 精度保持（测试断言非 float 构造）
- [ ] AC-13（原料）`get_suspensions` 返回当日 suspend 记录；`get_lifecycle_stocks` 真实冒烟四状态均非空且 D 状态含 delist_date
- [ ] 旧 `get_daily_data` / `get_stock_list` / `get_trading_calendar` 行为不变（现有测试回归）
- [ ] E2E 不适用：纯采集层功能，无用户界面；用户可见效果由 plan-05 同步任务与 plan-07 面板间接验证

### 性能验收（架构 §8.1）

- [ ] 单日常态请求数 = 2 页 daily（mock 断言 offset 只出现 0 与 3000）；每页间遵守 0.3s 节流

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 单测（mock DataApi，不依赖网络）
pytest tests/services/data_acquisition/test_tushare_market_daily.py -v --no-cov

# 2. 回归：采集层既有测试
pytest tests/test_data_acquisition tests/test_data_source_factory -v --no-cov

# 3. 真实冒烟（需 TUSHARE_TOKEN）
python -c "
from datetime import date
from decimal import Decimal
from src.services.data_acquisition import DataSourceFactory
ds = DataSourceFactory.create()
quotes = ds.get_market_daily_quotes(date(2026,8,12), expected_count=5400)
print('daily rows:', len(quotes), 'sample:', quotes[0])
codes = [q.ts_code for q in quotes[:100]]
w = ds.get_close_quotes_in_window(codes, date(2026,7,13), date(2026,8,11))
print('window rows:', len(w))
s = ds.get_suspensions(date(2026,8,12)); print('suspensions:', len(s))
lc = ds.get_lifecycle_stocks()
from collections import Counter; print('lifecycle:', Counter(x.list_status for x in lc))
"
```

## 交接上下文

- **架构章节**: §4.2 模块 1、§5 ADR-1/2/3、§6.1.3-6、§8.1、§8.4、§8.6
- **相关代码**: `server/src/services/data_acquisition/tushare_client.py`（`_execute_with_retry` L103、`_enforce_rate_limit` L86、`get_fund_list` 分页范式 L572、qfq `get_daily_data` L362-422 禁用）
- **契约 / 数据对象**: `MarketDailyQuote` / `SuspensionRecord` / `LifecycleStock`；异常类型 `MarketDataIntegrityError`（本功能新增，建议定义在 `data_acquisition/models.py` 或独立 errors 模块）
- **下游消费方**: plan-03（MarketMetricsService 消费四个方法与异常类型）
- **实现级补充项**: 异常类型与 `expected_count` 参数服务于 AC-01/07/13，非新造 AC
- **suspend_d 上游行为补充（实现级）**: 实测代理忽略 `suspend_date` 查询过滤（任意日期返回同一批跨约 300 个日期的全量行，约 5000 行），且停牌日期列名为 `trade_date`（官方 schema 为 `suspend_date`，显式请求该字段只得全空列）；`get_suspensions` 不传 fields 取原生 schema、双键归一化日期后保真返回全量行、不做日期过滤，plan-03 消费时必须客户端过滤 `record.suspend_date == trade_date` 后才能作为当日停牌证据（服务 AC-13 的实现级补充，非新造 AC）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；分页引擎先于两模式实现
- **验证失败排查方向**: mock DataFrame 构造需模拟 tushare 返回 dict-like（参照现有 `test_data_acquisition` 目录替身）；真实冒烟失败先查积分/限流（`_NON_RETRYABLE_KEYWORDS`）
- **允许修改的额外文件**: 测试替身补最小实现
- **暂停条件**: 若 Tushare 代理对 `daily` 的 `offset` 参数不支持（返回同页），暂停并上报——这是分页设计的硬前提
- **风险备注**: 历史模式 ts_code 批量传参若接口报参数超限，按 100/批内部分块即可，勿放大批

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 单日首张空页 | 返回空列表，调用方判失败 | done |
| 合法满页后空探测页 | 正常终止 | done |
| 历史窗口首张空页 | 返回空列表，调用方换更早窗口 | done |
| expected_count=0 | 硬页数=1，仅探测一页 | done |
| suspend_d 无记录 | 空列表（当日无停牌） | done |
| stock_basic 某状态 0 行 | 该状态空集，合并继续 | done |
