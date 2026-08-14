---
feat_id: "plan-02"
title: "融资融券采集适配器"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-02: 融资融券采集适配器

## 功能概要

- **目标**: 在 `TushareDataSource` 上新增 `get_margin(trade_date) -> List[dict]`，调用 tushare `margin` 融资融券交易汇总接口（doc_id=58，2000 积分）拉取单日全交易所原始行（2026-08-14 实测并经人工裁定：SSE/SZSE/BSE 三行全量），复用 `_execute_with_retry` + `_df_to_rows` + `_decimal_field` 范式，数值字段经 `Decimal(str())` 强约束。单日行数很少（实测 3 行），**无需分页**。
- **完成后可观察结果**: 给定任意交易日 T，`get_margin(T)` 返回 0~N 行原始 dict（实测 N=3）：每行含 `trade_date`（date）、`exchange_id`（'SSE'/'SZSE'/'BSE'）与 rzye/rzmre/rzche/rqye/rqmcl/rqyl/rzrqye 七个 Decimal 字段（元/股原始口径）；任何字段缺失、非有限数、负值、日期不符均抛 `MarketDataIntegrityError`（含 exchange_id 与字段值），而不是静默返回脏数据。真实冒烟可看到三行 SSE/SZSE/BSE 数据。既有采集方法行为不变。
- **依赖**: 无（与 plan-01 文件不相交，可并行执行）
- **关联验收标准**: 无直接承接（AC-1 聚合的原料供给；聚合正确性由 plan-03 验收）
- **涉及架构模块**: 融资融券采集适配器（spec 代码地图"后端 — 改动" tushare_client 项，对应 16 期 plan-02 的采集部分）
- **前置条件**: `TUSHARE_TOKEN` 有效且账号具备 margin 接口权限（2000 积分，仅真实冒烟需要）。
- **不在范围**: 聚合与落库（plan-03）；`base.py` 抽象方法与 `data_acquisition/models.py` 领域模型（spec 代码地图未列，明确不加，见实现规格 #4）；margin_detail 个股明细（spec 禁止）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 新增 `get_margin(trade_date)`（`get_market_daily_quotes` L1923 方法族旁） |
| create | `server/tests/services/data_acquisition/test_tushare_margin.py` | mock DataApi 覆盖正常/空/非法字段场景 |

## 实现规格

### 后端部分

#### 1. get_margin 方法（spec REQ-1）

`TushareDataSource.get_margin(self, trade_date: date) -> List[dict]`，放置于 `get_market_daily_quotes`（L1923）方法族附近：

- 调用 `_get_pro_api().margin(trade_date=YYYYMMDD)`，**不传 fields**（取 Provider 原生 schema：trade_date/exchange_id/rzye/rzmre/rzche/rqye/rqmcl/rqyl/rzrqye；16 期 suspend_d 实测教训：显式请求字段可能得到全空列，原生 schema 更稳）
- 整个调用包在 `_execute_with_retry`（L115，3 次指数退避）内的 `_fetch` 闭包范式：`df = self._execute_with_retry(_fetch)`
- `rows = self._df_to_rows(df)`（L1662，NaN→None）
- 单日行数很少（实测 3 行），**一次调用取全、不加 offset/limit 分页循环**（spec 冻结："单日全量行无需分页"；2026-08-14 实测三行后人工裁定全量求和口径）
- 空结果（None/空 DataFrame）→ 返回空列表，**由调用方（plan-03）判为当日失败**

#### 2. 行构建与校验（Decimal 强约束）

每行 `_build_margin_row(row) -> dict`：

- `exchange_id = str(row.get('exchange_id')).strip()`，为空抛 `MarketDataIntegrityError`（source=self.source_name, endpoint='margin'）
- `row_date = self._parse_tushare_date(row.get('trade_date'), ts_code=exchange_id, endpoint='margin')`；`row_date != trade_date` → 抛完整性错误（防串日数据）
- 七个数值字段逐一经 `self._decimal_field(row, field, ts_code=exchange_id)`（L1711，内部 `Decimal(str(value))` + `is_finite()` 校验）转 Decimal：
  - rzye（融资余额，元）/ rzmre（融资买入额，元）/ rzche（融资偿还额，元）/ rqye（融券余额，元）/ rqmcl（融券卖出量，股）/ rqyl（融券余量，股）/ rzrqye（两融合计余额，元）
- 数值范围复验（`_decimal_field` 只保证可解析与有限，范围由本方法按字段语义追加，同 16 期 `_build_market_daily_quote` 惯例）：七字段均要求 `>= 0`，负值抛完整性错误（余额/买入额/偿还额/卖出量/余量不可能为负）
- 返回 dict：`{'trade_date': row_date, 'exchange_id': exchange_id, 'rzye': Decimal, ..., 'rzrqye': Decimal}`（键名与 tushare 原生一致，蛇形）
- 结束 `logger.info("[Tushare] margin %s 获取 %d 行（交易所: %s）", trade_date, len(rows), [r['exchange_id'] for r in rows])`

**rqyl/rzrqye 的去向**：rqyl 不入库（spec REQ-2 存储字段不含）；rzrqye 原样返回仅供排查参考，**服务层（plan-03）禁止直接 sum 每行 rzrqye**（spec 冻结 D2）——两字段在本层保真透传，聚合口径在 plan-03。

#### 3. 可观测性

结构化日志：trade_date、返回行数、交易所集合；完整性错误日志含 exchange_id 与字段值（对齐 16 期 §8.5 惯例：失败只记 endpoint、错误类别与样本）。

#### 4. 明确不做（spec 边界）

- **不改 `base.py`**（不加抽象方法）、**不改 `data_acquisition/models.py`**（不加 Pydantic 领域模型）：spec 代码地图"后端 — 改动"仅列 tushare_client.py。16 期 plan-02 因新增抽象方法被迫为测试替身补最小实现，本期规避该扩散面。`MarginService`（plan-03）经 `DataSourceFactory.create()` 获取实例后直接调用（仓库唯一实现即 TushareDataSource，工厂返回类型注解为 BaseDataSource，运行时无影响）
- 不做 exchange_id 白名单过滤（返回 Provider 原生全部行，实测 SSE/SZSE/BSE 三行；行集合校验由 plan-03 日志观察）

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 实现 get_margin 主流程 | backend | done | pro.margin(trade_date=) + _execute_with_retry + _df_to_rows，无分页 |
| 2 | 实现 _build_margin_row 校验 | backend | done | 七字段 Decimal + 非负 + 日期一致 + exchange_id 非空 |
| 3 | 编写 test_tushare_margin.py | backend | done | mock DataApi 覆盖下述场景 |

## 验收标准

### 后端验收

- [x] 正常三行（SSE/SZSE/BSE，2026-08-14 实测人工裁定口径）：返回 3 个 dict，七数值字段全为 `Decimal` 实例（断言 `isinstance(v, Decimal)` 且非 float 构造），trade_date 与入参一致；本层不强制行数，两行/单行照常返回
- [x] 空结果（Provider 返回空 DataFrame/None）：返回空列表不抛错（失败判定归 plan-03）
- [x] 字段缺失 / NaN / Infinity / 负值 / 日期不符 / exchange_id 为空六类场景均抛 `MarketDataIntegrityError`，错误信息含 exchange_id 与字段值
- [x] 单日仅发起 1 次 `margin` 调用（mock 断言调用次数=1，无分页循环）
- [x] `Decimal(str(...))` 精度保持：构造科学计数法值（如 1.0e12）断言无 float 精度损失
- [x] 既有采集方法回归通过（`get_market_daily_quotes`/`get_trading_calendar_range` 等现有测试不受影响）
- [x] E2E 不适用：纯采集层功能，无用户界面；用户可见效果由 plan-04 同步任务执行验证与 plan-07 面板间接验证

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 单测（mock DataApi，不依赖网络）
pytest tests/services/data_acquisition/test_tushare_margin.py -v --no-cov

# 2. 回归：采集层既有测试
pytest tests/services/data_acquisition/ -q --no-cov

# 3. 真实冒烟（需 TUSHARE_TOKEN + margin 2000 积分；实测返回 SSE/SZSE/BSE 三行）
python -c "
from datetime import date
from decimal import Decimal
from src.services.data_acquisition import DataSourceFactory
rows = DataSourceFactory.create().get_margin(date(2026, 8, 13))
print('margin rows:', len(rows))
for r in rows:
    print(r['exchange_id'], {k: str(v) for k, v in r.items() if isinstance(v, Decimal)})
assert len(rows) == 3 and {r['exchange_id'] for r in rows} == {'SSE', 'SZSE', 'BSE'}
assert all(isinstance(r[f], Decimal) for r in rows for f in ('rzye', 'rzmre', 'rzche', 'rqye', 'rqmcl', 'rqyl', 'rzrqye'))
"
```

## 交接上下文

- **spec 章节**: REQ-1（采集）、边界（必须：Decimal 强约束；禁止：margin_detail）、代码地图（tushare_client.py 改动项）、任务清单 T2
- **相关代码**: `server/src/services/data_acquisition/tushare_client.py`（`_execute_with_retry` L115、`_df_to_rows` L1662、`_parse_tushare_date` L1680、`_decimal_field` L1711、`_build_market_daily_quote` L1736 数值范围复验范式、`get_market_daily_quotes` L1923 方法族定位、`MarketDataIntegrityError` 同文件既有异常）
- **契约 / 数据对象**: 返回 `List[dict]`：`{trade_date: date, exchange_id: str, rzye/rzmre/rzche/rqye/rqmcl/rqyl/rzrqye: Decimal}`（非 Pydantic 模型，spec 代码地图冻结）
- **下游消费方**: plan-03（`MarginService.sync_date` 拉取与聚合）
- **实现级补充项**: 非负校验与日期一致性校验服务于 AC-1（聚合输入质量），非新造 AC
- **调用细节注意**: `_decimal_field(row, field, ts_code=exchange_id)` 的 `ts_code` 参数在此语义为行标识（交易所代码）；其错误消息 endpoint 文案固定为 "daily"，仅影响日志文案不影响行为，不要为改文案去动 16 期方法签名

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行
- **验证失败排查方向**: mock DataFrame 构造参照 `tests/services/data_acquisition/` 既有替身（dict-like 模拟 tushare 返回）；真实冒烟失败先查积分/限流（`_NON_RETRYABLE_KEYWORDS`，2000 积分门槛不足时报权限错误）
- **允许修改的额外文件**: 无（base.py / data_acquisition/models.py 明确不改）
- **暂停条件（已触发并裁定，2026-08-14）**: 原条件"若实测 `margin` 接口对单日返回超过两行则暂停上报"已触发并完成裁定——全市场合计口径 = 对接口返回的全部交易所行求和（SSE/SZSE/BSE 三行，含北交所）；采集层保真透传 3 行不改
- **风险备注**: tushare 积分不足时 `_execute_with_retry` 会对非可重试关键字立即失败——这是期望行为，不要捕获吞错

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| Provider 返回空 DataFrame | 空列表（当日无两融数据判定归 plan-03） | done |
| 某数值字段为 NaN/None | `_df_to_rows` NaN→None 后 `_decimal_field` 抛完整性错误 | done |
| 行 trade_date 与入参不符 | 抛完整性错误（防串日） | done |
| exchange_id 为空串/缺失 | 抛完整性错误 | done |
| 返回仅 1 行（如上游截断） | 本层照常返回 1 行（不强制行数，常态三行）；行数异常观察与口径由 plan-03 边界处理 | done |

### 暂停条件已裁定（2026-08-14）：三行全量求和口径，采集层保真透传 3 行不改

真实冒烟（§6 命令 3）实测：该 Tushare 代理对 `margin` 单日**稳定返回 3 行 SSE/SZSE/BSE**（非偶发，2026-07-15 / 08-07 / 08-11 / 08-12 / 08-13 五个交易日全部 3 行），触发暂停条件并已由人工裁定：**全市场合计口径 = 对接口返回的全部交易所行求和（SSE/SZSE/BSE 三行，含北交所）**。spec / README / plan-03 的口径表述已由主 agent 同步更新。

- **plan-02 实现无需改动**：保真透传全部行、无白名单过滤（spec：行集合校验由 plan-03 日志观察），BSE 行七数值字段均通过完整性校验（如 2026-08-13：rzye=8,371,680,293 元，量级远小于沪深）。
- **本文件已按裁定更新**：§6 冒烟断言改为 3 行（SSE/SZSE/BSE 全存在，各行七字段全部通过校验）；单测正常场景改为三行，两行/单行保留为"本层不强制行数"边界。
- **下游影响**：plan-03 聚合对全部行求和（rzrqye 仍为 sum(rzye)+sum(rqye) 服务层重算，禁止直接 sum 每行 rzrqye 的约束不变）。
