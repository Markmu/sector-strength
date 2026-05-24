---
feat_id: "plan-01"
title: "交易日历服务"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 交易日历服务

## 1. 功能概要

- **目标**: 提供权威的 A 股交易日历判断能力，替代现有硬编码周末判断，正确区分交易日、周末、法定节假日和调休工作日。
- **完成后可观察结果**: 调用 TradingCalendar.is_trading_day() 对任意日期能返回准确的交易/非交易日判断和具体原因（如"周末"、"节假日"）。AkShare 数据源不可用时自动降级为简单周末判断并记录 warning 日志。调用方无需关心降级细节，接口契约统一。
- **依赖**: 无
- **关联验收标准**: [AC-02, AC-03]
- **涉及架构模块**: TradingCalendar, AkShareDataSource
- **前置条件**: AkShare 已安装，可调用 `tool_trade_date_hist_sina()` 接口
- **不在范围**: 交易日历的离线缓存和手动维护机制；交易日历本地表

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_acquisition/akshare_client.py` | 新增 get_trading_calendar() 方法 |
| create | `server/src/services/trading_calendar.py` | 新建 TradingCalendar 服务类 |

## 3. 实现规格

### 后端部分

#### 1. AkShareDataSource.get_trading_calendar()

在 `AkShareDataSource` 类中新增方法：

```python
def get_trading_calendar(self) -> List[date]:
    """获取 A 股交易日历（含节假日调休）"""
```

- 调用 `ak.tool_trade_date_hist_sina()` 获取交易日列表（返回 DataFrame，含 `trade_date` 列）
- 复用 `_execute_with_retry()` 做重试和速率限制
- 将 DataFrame 的 `trade_date` 列转换为 `List[date]`，按日期升序排列
- 失败时抛出 `DataFetchError` 或 `RetryExhaustedError`

#### 2. TradingCalendar 服务类

新建 `server/src/services/trading_calendar.py`：

```python
class TradingCalendar:
    def __init__(self):
        self._cache: Optional[List[date]] = None
        self._cache_date: Optional[date] = None

    async def is_trading_day(self, check_date: date = None) -> tuple[bool, str | None]:
        """判断是否为交易日，返回 (是否交易日, 跳过原因)"""

    async def get_trading_days_between(self, start: date, end: date) -> List[date]:
        """获取两个日期之间的交易日列表"""
```

`is_trading_day()` 实现：
- 当日结果内存缓存（`_cache` + `_cache_date`）：首次调用时获取交易日历，缓存至当日结束
- 判断目标日期是否在交易日历中
- 在交易日历中 → `(True, None)`
- 不在交易日历中且为周末 → `(False, "周末")`
- 不在交易日历中且非周末 → `(False, "节假日")`
- AkShare 不可用（捕获 DataFetchError/RetryExhaustedError）→ 降级为简单周末判断，记录 warning 日志：`"交易日历获取失败，降级为周末判断: {error}"`

`get_trading_days_between()` 实现：
- 获取交易日历（同缓存逻辑）
- 过滤 start ≤ date ≤ end 的交易日
- 返回升序列表

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 在 AkShareDataSource 新增 get_trading_calendar() 方法 | backend | done | 调用 ak.tool_trade_date_hist_sina()，返回 List[date] |
| 2 | 新建 TradingCalendar 服务类 | backend | done | is_trading_day() + get_trading_days_between()，含内存缓存和降级逻辑 |

## 5. 验收标准

### 功能验收

- [x] AC-02 调用 `is_trading_day()` 对周末日期返回 `(False, "周末")`，不执行后续数据拉取
- [x] AC-02 调用 `is_trading_day()` 对法定节假日（如春节、国庆）返回 `(False, "节假日")`
- [x] AC-03 调用 `is_trading_day()` 对调休工作日（周末补班日）返回 `(True, None)`
- [x] AkShare 不可用时降级为周末判断，记录 warning 日志
- [x] 交易日历结果当日内存缓存，同日多次调用不重复请求 AkShare
- [x] `get_trading_days_between()` 正确返回指定范围内的交易日列表

## 6. 验证命令

```bash
cd server
# 单元测试：TradingCalendar 和 AkShareDataSource 的 get_trading_calendar
pytest tests/ -v -k "trading_calendar or get_trading_calendar"
# 类型检查
python -c "from src.services.trading_calendar import TradingCalendar; print('import ok')"
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责（TradingCalendar）、§5 ADR-2、§6.1 运行链路
- **相关代码**: `server/src/services/data_acquisition/akshare_client.py`
- **契约 / 数据对象**: `is_trading_day(date) -> tuple[bool, str | None]`、`get_trading_days_between(start, end) -> List[date]`
- **下游消费方**: plan-03（DataCollector 集成 TradingCalendar）、plan-04（DataQualityChecker 使用 TradingCalendar）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（先 akshare_client 再 trading_calendar）
- **验证失败排查方向**: 检查 AkShare 是否安装、网络是否可达、`tool_trade_date_hist_sina()` 接口是否正常返回
- **允许修改的额外文件**: 无
- **暂停条件**: AkShare 接口变更导致 `tool_trade_date_hist_sina()` 不可用
- **E2E 不适用说明**: 纯后端内部服务，无用户可观察 UI；通过单元测试覆盖
- **风险备注**: AkShare 交易日历可能滞后更新（新的节假日安排公布后），但这是数据源的固有限制

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| AkShare 接口超时 | 降级为周末判断，记录 warning 日志 | done |
| AkShare 返回空 DataFrame | 降级为周末判断，记录 warning 日志 | done |
| 传入未来日期 | 正常判断（交易日历包含未来已知交易日） | done |
| 传入 None（使用默认今天） | 默认使用 `datetime.now().date()` | done |
| 跨日调用（缓存过期） | `_cache_date` 与当日不一致时重新获取 | done |
