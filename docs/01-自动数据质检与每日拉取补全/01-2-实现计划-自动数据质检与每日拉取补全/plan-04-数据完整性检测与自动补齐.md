---
feat_id: "plan-04"
title: "数据完整性检测与自动补齐"
dimension: backend
phase: 3
status: done
depends_on: ["plan-01", "plan-03"]
---

# plan-04: 数据完整性检测与自动补齐

## 1. 功能概要

- **目标**: 改造 DataQualityChecker 实现数据完整性检测与自动补齐逻辑：检查最新交易日行情数据缺失和日期缺口，发现缺失时自动从 AkShare 补齐 latest_date+1 至当日之间所有交易日的数据。清理 admin.py 中的空壳类，改造质检 API 路由支持手动触发。修改定时任务频率为每小时一次。
- **完成后可观察结果**: 质检定时任务每小时运行一次，检查 DailyMarketData 中最新交易日的股票行情数据是否完整（对比 Stock 总数），检查是否有日期缺口（latest_date+1 至当日之间有交易日无数据）。发现缺失时自动从 AkShare 拉取对应交易日的板块和个股行情，写入数据库并触发计算。管理员可通过 `GET /api/v1/admin/data/quality/check` 手动触发质检，立即获得包含补齐结果的结构化报告。admin.py 中的空壳 DataQualityChecker 已删除。
- **依赖**: plan-01（TradingCalendar，用于获取交易日列表）、plan-03（每日更新落库，质检依赖 DailyMarketData 中的数据）
- **关联验收标准**: [AC-04, AC-07]
- **涉及架构模块**: DataQualityChecker, TradingCalendar, AkShareDataSource, HealthCheck API, JobManager
- **前置条件**: plan-01 的 TradingCalendar 可用；plan-03 的每日更新已能将数据写入 DailyMarketData
- **不在范围**: 异常价格检测、强度得分有效性检测（留待后续）；外部告警通道（邮件/短信/Webhook）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/monitoring/data_quality.py` | 改造 DataQualityChecker：缺失检测 + 日期缺口检测 + 自动补齐 |
| modify | `server/src/api/v1/admin.py` | 删除空壳 DataQualityChecker 类，改造 /quality/check 路由 |
| modify | `server/src/services/scheduler/job_manager.py` | 质检频率从 5 分钟改为 1 小时；更新 _check_data_quality() 调用 |

## 3. 实现规格

### 后端部分

#### 1. 改造 DataQualityChecker 核心检测逻辑

修改 `server/src/services/monitoring/data_quality.py`。

**1.1 新增构造函数注入依赖**

```python
class DataQualityChecker:
    def __init__(self):
        self._trading_calendar = TradingCalendar()
        self._data_source = AkShareDataSource()
```

**1.2 改造 check_data_integrity() 为 run_full_check()**

新增主入口方法 `run_full_check()`，替代原有的 `check_data_integrity()`：

```python
async def run_full_check(self) -> Dict[str, Any]:
    """执行完整质检：检测缺失 → 检测日期缺口 → 自动补齐 → 返回报告"""
```

执行流程：
1. 调用 `_check_missing_market_data()` 获取缺失信息
2. 调用 `_detect_date_gaps()` 获取日期缺口
3. 若有缺失或缺口，调用 `_backfill_missing_dates(trading_days)` 自动补齐
4. 汇总生成 QualityCheckReport

**1.3 改造 _check_missing_market_data()**

当前问题：直接返回 0，无实际检测逻辑。

改造内容：
- 查询 DailyMarketData 的最大日期（`select(func.max(DailyMarketData.date))`）作为 latest_date
- 统计 latest_date 当日 `entity_type='stock'` 的去重 entity 数量
- 查询 Stock 表总数
- 差值 = 缺失数
- 板块行情不参与缺失检测（架构文档明确说明）
- 若 DailyMarketData 为空（latest_date 为 None），返回缺失数 = Stock 总数

```python
async def _check_missing_market_data(self) -> Dict[str, Any]:
    """返回 {"latest_date": date|None, "total_stocks": int, "stocks_with_data": int, "missing_count": int}"""
```

**1.4 新增 _detect_date_gaps()**

```python
async def _detect_date_gaps(self, latest_date: date) -> List[date]:
    """查询 latest_date+1 至当日之间的交易日列表"""
```

- 若 latest_date 为 None（无数据），返回空列表（不回溯历史）
- 调用 `self._trading_calendar.get_trading_days_between(latest_date + timedelta(days=1), today)`
- 返回需补齐的交易日列表

**1.5 保留 get_data_quality_report()**

现有方法已能正确统计 stock_count、sector_count、market_data_count，保持不变。

#### 2. 实现自动补齐逻辑 _backfill_missing_dates()

```python
async def _backfill_missing_dates(self, trading_days: List[date]) -> Dict[str, int]:
    """对每个缺失交易日补齐板块和个股行情数据"""
```

执行流程（每个缺失交易日）：
1. 从数据库查询所有板块（id, code, name, type），构建映射
2. 按板块逐个调用 `self._data_source.get_sector_daily_data(sector_name, sector_type, date, date)` 获取板块行情
3. 将板块行情写入 DailyMarketData（entity_type='sector', entity_id=板块id, symbol=板块code）
4. 从数据库查询所有股票（id, symbol），按批次（50 只）遍历
5. 调用 `self._data_source.get_daily_data(symbol, date, date)` 获取个股行情
6. 将个股行情写入 DailyMarketData（entity_type='stock', entity_id=股票id, symbol=股票代码）
7. 使用 INSERT ... ON CONFLICT DO NOTHING
8. 触发该日期的均线计算和强度计算
9. 单个交易日失败时记录错误日志，继续处理下一个
10. 返回 `{"filled_successfully": int, "filled_failed": int}`

速率限制由 AkShareDataSource._execute_with_retry() 内部处理（500ms 间隔），补齐循环中无需额外 sleep。

#### 3. 清理 admin.py 空壳类并改造路由

修改 `server/src/api/v1/admin.py`。

**3.1 删除空壳 DataQualityChecker 类**

删除 L31-33 的空壳类：
```python
# 删除以下代码
class DataQualityChecker:
    async def check_data_integrity(self):
        return {"has_issues": False, "issues": []}

    async def get_data_quality_report(self):
        return {"stock_count": 0}
```

**3.2 改造 /quality/check 路由**

```python
from src.services.monitoring.data_quality import DataQualityChecker as RealDataQualityChecker

@router.get("/quality/check")
async def quality_check(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    checker = RealDataQualityChecker()
    report = await checker.run_full_check()
    return {"success": True, "data": report}
```

返回结构符合 QualityCheckReport 契约：
```python
{
    "check_time": "ISO datetime",
    "is_healthy": bool,
    "latest_trading_date": "ISO date or None",
    "checks": {"missing_data": {"affected_count": int, "severity": str}},
    "backfill": {
        "gap_start": "ISO date or None",
        "gap_end": "ISO date or None",
        "trading_days_to_fill": int,
        "filled_successfully": int,
        "filled_failed": int,
    },
    "data_overview": {
        "total_stocks": int,
        "total_sectors": int,
        "total_market_data": int,
    },
}
```

#### 4. 修改 JobManager 质检频率和调用

修改 `server/src/services/scheduler/job_manager.py`。

**4.1 修改质检频率**

在 `_register_jobs()` 中将质检任务的 IntervalTrigger 从 `minutes=5` 改为 `hours=1`：

```python
self.scheduler.add_job(
    self._check_data_quality,
    trigger=IntervalTrigger(hours=1),
    id='data_quality_check',
    name='数据质量检查',
    replace_existing=True
)
```

**4.2 更新 _check_data_quality() 调用**

```python
async def _check_data_quality(self):
    from src.services.monitoring.data_quality import DataQualityChecker

    logger.info("[定时任务] 执行数据质量检查")

    try:
        checker = DataQualityChecker()
        report = await checker.run_full_check()

        if not report.get('is_healthy'):
            logger.warning(f"[定时任务] 发现数据质量问题: 缺失 {report['checks']['missing_data']['affected_count']} 条")
            backfill = report.get('backfill', {})
            logger.info(f"[定时任务] 补齐结果: 成功 {backfill.get('filled_successfully', 0)} 日, 失败 {backfill.get('filled_failed', 0)} 日")
        else:
            logger.info("[定时任务] 数据质量检查通过")
    except Exception as e:
        logger.error(f"[定时任务] 数据质量检查失败: {e}")
```

**可观测性（架构 §8.4）**: 质检完成时记录 info/warning 日志，包含缺失数、补齐成功/失败数。使用结构化日志输出关键指标。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 改造 DataQualityChecker：新增 run_full_check() + 构造函数注入依赖 | backend | done | 替代 check_data_integrity()，注入 TradingCalendar 和 AkShareDataSource |
| 2 | 改造 _check_missing_market_data() | backend | done | 查询最新日期 + Stock 总数对比 |
| 3 | 新增 _detect_date_gaps() | backend | done | 查询 DailyMarketData 最大日期 + TradingCalendar 获取缺口交易日 |
| 4 | 新增 _backfill_missing_dates() | backend | done | 按交易日补齐板块+个股行情，ON CONFLICT DO NOTHING |
| 5 | 清理 admin.py 空壳类 + 改造 /quality/check 路由 | backend | done | 删除空壳类，路由调用真实 DataQualityChecker.run_full_check() |
| 6 | 修改 JobManager 质检频率为每小时 + 更新 _check_data_quality() 调用 | backend | done | IntervalTrigger(hours=1) + 调用 run_full_check() |

## 5. 验收标准

### 功能验收

- [x] AC-04 质检检测到最新交易日股票行情缺失时，missing_count > 0
- [x] AC-04 质检检测到日期缺口（latest_date+1 至当日有交易日无数据）时，trading_days_to_fill > 0
- [x] AC-04 质检自动补齐缺失交易日的板块和个股行情数据，并触发计算
- [x] AC-04 补齐范围严格限定为 latest_date+1 至当日，不回溯更早历史数据
- [x] AC-04 单个交易日补齐失败时不影响其余交易日的补齐
- [x] AC-07 通过 `GET /api/v1/admin/data/quality/check` 手动触发质检，返回 QualityCheckReport
- [x] admin.py 中的空壳 DataQualityChecker 已删除
- [x] JobManager 质检任务频率为每小时一次

## 6. 验证命令

```bash
cd server
# 单元测试
pytest tests/ -v -k "data_quality or quality_check or backfill"
# 手动触发质检（需启动服务 + 数据库 + 有存量数据）
uvicorn server.main:app --port 8000 &
curl -H "api_key: <key>" http://localhost:8000/api/v1/admin/data/quality/check
# 期望: {"success": true, "data": {"is_healthy": bool, "checks": {...}, "backfill": {...}, ...}}
# 验证 admin.py 空壳类已删除
python -c "from src.api.v1.admin import DataQualityChecker; print('ERROR: should not exist')" 2>&1 | grep -q "ImportError" && echo "OK" || echo "FAIL"
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责（DataQualityChecker）、§5 ADR-3、§6.2 数据完整性检测与自动补齐链路
- **相关代码**: `server/src/services/monitoring/data_quality.py`、`server/src/api/v1/admin.py`、`server/src/services/scheduler/job_manager.py`
- **契约 / 数据对象**:
  - QualityCheckReport: `{check_time, is_healthy, latest_trading_date, checks: {missing_data: {affected_count, severity}}, backfill: {gap_start, gap_end, trading_days_to_fill, filled_successfully, filled_failed}, data_overview: {total_stocks, total_sectors, total_market_data}}`
  - API: `GET /api/v1/admin/data/quality/check` → QualityCheckReport
- **下游消费方**: 无直接下游，管理 API 供管理员使用

## 8. 风险与边界

- **执行顺序**: Task 1-4（DataQualityChecker 改造）→ Task 5（admin.py 清理，依赖 Task 1 的新接口）→ Task 6（JobManager，依赖 Task 1 的 run_full_check）
- **验证失败排查方向**: 检查 TradingCalendar 是否可用（plan-01）、DailyMarketData 是否有数据（plan-03）、AkShare 接口是否正常
- **允许修改的额外文件**: 无
- **暂停条件**: 补齐逻辑运行时间超过预期（大量交易日缺失）
- **E2E 不适用说明**: 后端定时任务 + 管理 API，无用户可观察 UI；通过 API 调用验证
- **风险备注**: 若数据库长期未运行（如初始化后数周），补齐可能涉及大量交易日。但补齐范围限定为 latest_date+1 至当日，不会无限回溯。无数据时（latest_date 为 None）不触发补齐

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| DailyMarketData 为空（latest_date = None） | 不触发补齐，报告 is_healthy=false，missing_count = total_stocks | done |
| Stock 表为空（total_stocks = 0） | missing_count = 0，is_healthy = true | done |
| 补齐中 AkShare 单个交易日失败 | 记录错误，继续补齐下一个交易日，filled_failed++ | done |
| 补齐中 AkShare 完全不可用 | 所有交易日补齐失败，报告 filled_failed = trading_days_to_fill | done |
| admin.py 空壳类有其他引用 | 扫描确认无其他引用后再删除（架构文档确认仅路由使用） | done |
| 质检与每日更新并发执行 | APScheduler 已配置 max_instances 防止并发 | done |
| TradingCalendar 降级为周末判断 | get_trading_days_between 可能返回非交易日，补齐时 ON CONFLICT 跳过 | done |
