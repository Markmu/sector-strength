---
feat_id: "plan-02"
title: "TushareDataSource 实现"
dimension: backend
phase: 2
status: draft
depends_on: ["plan-01"]
---

# plan-02: TushareDataSource 实现

## 1. 功能概要

- **目标**: 实现 TushareDataSource 类，覆盖 BaseDataSource 的 5 个抽象方法（get_trading_calendar / get_stock_list / get_sector_list / get_daily_data / get_sector_daily_data）+ health_check，完成 Tushare SDK 的所有字段映射、频率控制和重试机制。
- **完成后可观察结果**: 配置有效 Tushare Token 后，`TushareDataSource` 的 5 个数据获取方法均可正常调用并返回符合 Pydantic 模型（StockInfo / SectorInfo / DailyQuote / List[date]）的数据。health_check 能验证连接可用性。请求频率由 `_enforce_rate_limit` 控制，失败请求自动重试 3 次（指数退避）。字段映射对上层服务透明。
- **依赖**: plan-01（BaseDataSource 抽象层 + DataSourceFactory）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-07]
- **涉及架构模块**: TushareDataSource
- **前置条件**: plan-01 完成；Tushare 账户积分 ≥ 6000；有效 Tushare API Token
- **不在范围**: 服务层解耦替换（plan-03）；前端变更；数据库变更

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/data_acquisition/tushare_client.py` | TushareDataSource 完整实现 |

## 3. 实现规格

### 后端部分

#### 1. TushareDataSource 类结构

新建 `server/src/services/data_acquisition/tushare_client.py`：

```python
import logging
import os
import time
from datetime import date, datetime
from typing import Any, Callable, List, Optional, TypeVar

from pydantic import ValidationError

from .base import BaseDataSource
from .exceptions import DataFetchError, RetryExhaustedError
from .models import DailyQuote, SectorInfo, StockInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TushareDataSource(BaseDataSource):
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_BACKOFF_FACTOR = 2.0
    DEFAULT_API_INTERVAL = 0.5

    def __init__(self):
        super().__init__("Tushare")
        self._token = os.getenv("TUSHARE_TOKEN", "").strip()
        self._api_url = os.getenv("TUSHARE_API_URL", "api.tushare.pro").strip()
        self._api_interval = float(os.getenv("TUSHARE_API_INTERVAL", str(self.DEFAULT_API_INTERVAL)))
        self._max_retries = self.DEFAULT_MAX_RETRIES
        self._retry_delay = self.DEFAULT_RETRY_DELAY
        self._backoff_factor = self.DEFAULT_BACKOFF_FACTOR
        self._pro_api = None
        self._last_request_time: Optional[datetime] = None
```

#### 2. 延迟初始化 pro_api

```python
def _get_pro_api(self) -> Any:
    if self._pro_api is None:
        if not self._token:
            raise DataFetchError(
                "TUSHARE_TOKEN 未配置",
                source=self.source_name,
            )
        try:
            import tushare as ts
            self._pro_api = ts.pro_api(self._token, api_url=self._api_url)
            logger.info(f"[Tushare] 初始化成功，服务地址: {self._api_url}")
        except ImportError as e:
            raise ImportError("tushare 未安装，请运行: pip install tushare") from e
        except Exception as e:
            raise DataFetchError(
                f"Tushare 初始化失败: {e}",
                source=self.source_name,
                original_error=e,
            )
    return self._pro_api
```

#### 3. 限流与重试

`_enforce_rate_limit()` 和 `_execute_with_retry()` 与 AkShareDataSource 模式一致（复用相同逻辑：记录 `_last_request_time`，指数退避重试，日志记录）。

`_execute_with_retry` 中每次请求记录 DEBUG 日志：`"[Tushare] 请求 {api_name}，耗时 {ms}ms"`。失败记录 WARNING 日志：`"[Tushare] 请求失败，重试 {n}/{max}"`。重试耗尽记录 ERROR 日志：`"[Tushare] 重试耗尽: {error}"`。

**可观测性（架构 §8.5）**：每次请求记录 DEBUG 日志含耗时；失败记录 WARNING 含重试次数；耗尽记录 ERROR 含错误详情。

#### 4. get_trading_calendar（AC-01）

```python
def get_trading_calendar(self) -> List[date]:
    pro = self._get_pro_api()

    def _fetch():
        logger.info("[Tushare] 正在获取交易日历...")
        df = pro.trade_cal(exchange='SSE', is_open='1')
        return df

    df = self._execute_with_retry(_fetch)
    if df is None or (hasattr(df, 'empty') and df.empty):
        raise DataFetchError("交易日历返回空数据", source=self.source_name, endpoint="trade_cal")

    dates: List[date] = []
    for val in df['cal_date']:
        d = datetime.strptime(str(val), "%Y%m%d").date()
        dates.append(d)
    dates.sort()
    logger.info(f"[Tushare] 获取到 {len(dates)} 个交易日")
    return dates
```

字段映射（架构 §7.2）：`cal_date`（`YYYYMMDD` 字符串 → date），仅保留 `is_open=1` 的记录。

#### 5. get_stock_list（AC-02）

```python
def get_stock_list(self) -> List[StockInfo]:
    pro = self._get_pro_api()

    def _fetch():
        logger.info("[Tushare] 正在获取股票列表...")
        return pro.stock_basic(exchange='', list_status='L')

    df = self._execute_with_retry(_fetch)
    stocks: List[StockInfo] = []
    errors = 0

    for _, row in df.iterrows():
        try:
            ts_code = str(row['ts_code'])      # e.g. "000001.SZ"
            symbol = ts_code.split('.')[0]      # "000001"
            name = str(row['name'])
            # 市场类型从 ts_code 后缀推断
            suffix = ts_code.split('.')[1] if '.' in ts_code else ''
            market_map = {'SH': 'SH', 'SZ': 'SZ', 'BJ': 'BJ'}
            market = market_map.get(suffix)
            industry = str(row.get('industry', '')) or None
            list_date = None
            if pd.notna(row.get('list_date')):
                list_date = datetime.strptime(str(row['list_date']), "%Y%m%d").date()
            stocks.append(StockInfo(symbol=symbol, name=name, market=market, industry=industry, list_date=list_date))
        except (ValidationError, ValueError) as e:
            errors += 1

    logger.info(f"[Tushare] 成功转换 {len(stocks)} 只股票，忽略 {errors} 条异常数据")
    return stocks
```

字段映射（架构 §7.2）：`ts_code` → symbol（截取前 6 位）；suffix → market（`.SZ`=SZ, `.SH`=SH, `.BJ`=BJ）；`industry` 直接映射；`list_date`（`YYYYMMDD` → date）。

#### 6. get_sector_list（AC-03）

```python
def get_sector_list(self, sector_type: Optional[str] = None) -> List[SectorInfo]:
    pro = self._get_pro_api()
    normalized = sector_type.strip().lower() if sector_type else None
    if normalized and normalized not in ("industry", "concept"):
        raise ValueError(f"无效的板块类型过滤: {sector_type}")

    sectors: List[SectorInfo] = []

    if normalized is None or normalized == "industry":
        sectors.extend(self._fetch_sectors_by_type(pro, "行业", "industry"))

    if normalized is None or normalized == "concept":
        sectors.extend(self._fetch_sectors_by_type(pro, "概念", "concept"))

    logger.info(f"[Tushare] 获取到 {len(sectors)} 个板块")
    return sectors

def _fetch_sectors_by_type(self, pro, is_type: str, type_label: str) -> List[SectorInfo]:
    def _fetch():
        logger.info(f"[Tushare] 正在获取{is_type}板块列表...")
        return pro.ths_index(exchange='A', type=is_type)

    df = self._execute_with_retry(_fetch)
    result: List[SectorInfo] = []
    for _, row in df.iterrows():
        try:
            result.append(SectorInfo(
                code=str(row['ts_code']),
                name=str(row['name']),
                type=type_label,
            ))
        except (ValidationError, ValueError):
            pass
    return result
```

字段映射（架构 §7.2）：`ths_index(exchange='A', type='行业')` → type=industry；`ths_index(exchange='A', type='概念')` → type=concept。

#### 7. get_daily_data（AC-04）

使用 `tushare.pro_bar(adj='qfq')` 获取前复权数据（ADR-3），内部合并 daily + adj_factor，无需手动计算复权。

```python
def get_daily_data(self, symbol: str, start_date: date, end_date: date) -> List[DailyQuote]:
    if not symbol:
        raise ValueError("股票代码不能为空")
    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")

    import tushare as ts
    pro = self._get_pro_api()
    ts_code = self._symbol_to_ts_code(symbol)

    def _fetch():
        logger.info(f"[Tushare] 正在获取 {symbol} 的日线数据 ({start_date} 至 {end_date})...")
        return ts.pro_bar(
            ts_code=ts_code,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adj='qfq',
            api=pro,
        )

    df = self._execute_with_retry(_fetch)
    if df is None or (hasattr(df, 'empty') and df.empty):
        return []

    quotes: List[DailyQuote] = []
    errors = 0
    for _, row in df.iterrows():
        try:
            trade_date = datetime.strptime(str(row['trade_date']), "%Y%m%d").date()
            quote = DailyQuote(
                symbol=symbol,
                trade_date=trade_date,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['vol']),
                amount=float(row['amount']) * 1000,  # 千元 → 元
                turnover=float(row.get('turnover_rate', 0)) if 'turnover_rate' in row.index and row.get('turnover_rate') is not None else None,
            )
            quotes.append(quote)
        except (ValidationError, ValueError, TypeError):
            errors += 1

    quotes.sort(key=lambda q: q.trade_date)
    logger.info(f"[Tushare] 成功转换 {len(quotes)} 条日线数据，忽略 {errors} 条异常数据")
    return quotes
```

字段映射（架构 §7.2）：`pro_bar(adj='qfq')` 直接返回前复权价格，无需手动乘 adj_factor；`ts_code` → symbol（截取前 6 位）；`amount` ×1000（千元→元）。

辅助方法 `_symbol_to_ts_code`：

```python
@staticmethod
def _symbol_to_ts_code(symbol: str) -> str:
    if symbol.startswith('6'):
        return f"{symbol}.SH"
    elif symbol.startswith(('0', '3')):
        return f"{symbol}.SZ"
    elif symbol.startswith(('8', '4')):
        return f"{symbol}.BJ"
    else:
        return symbol
```

#### 8. get_sector_daily_data（AC-05）

```python
def get_sector_daily_data(self, sector_name: str, sector_type: str, start_date: date, end_date: date) -> List[DailyQuote]:
    if not sector_name:
        raise ValueError("板块名称不能为空")
    if not sector_type:
        raise ValueError("板块类型不能为空")
    normalized = sector_type.strip().lower()
    if normalized not in ("industry", "concept"):
        raise ValueError(f"无效的板块类型: {sector_type}")
    if start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")

    pro = self._get_pro_api()

    # 通过板块名称查找 ts_code
    is_type = "行业" if normalized == "industry" else "概念"
    sectors = self._fetch_sectors_by_type(pro, is_type, normalized)
    ts_code = None
    for s in sectors:
        if s.name == sector_name:
            ts_code = s.code
            break
    if not ts_code:
        logger.warning(f"[Tushare] 未找到板块 '{sector_name}' 的 ts_code")
        return []

    def _fetch():
        logger.info(f"[Tushare] 正在获取板块 {sector_name} 的日线数据 ({start_date} 至 {end_date})...")
        return pro.ths_daily(ts_code=ts_code, start_date=start_date.strftime("%Y%m%d"),
                            end_date=end_date.strftime("%Y%m%d"))

    df = self._execute_with_retry(_fetch)
    if df is None or (hasattr(df, 'empty') and df.empty):
        return []

    quotes: List[DailyQuote] = []
    errors = 0
    for _, row in df.iterrows():
        try:
            trade_date = datetime.strptime(str(row['trade_date']), "%Y%m%d").date()
            quote = DailyQuote(
                symbol=sector_name,
                trade_date=trade_date,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['vol']),
            )
            quotes.append(quote)
        except (ValidationError, ValueError, TypeError):
            errors += 1

    quotes.sort(key=lambda q: q.trade_date)
    logger.info(f"[Tushare] 成功转换 {len(quotes)} 条板块日线数据，忽略 {errors} 条异常数据")
    return quotes
```

字段映射（架构 §7.2）：板块日线无 `amount` 和 `turnover` 字段（ths_daily 不返回），设为 `None`。

#### 9. health_check

```python
def health_check(self) -> bool:
    try:
        pro = self._get_pro_api()
        df = pro.trade_cal(exchange='SSE', limit=1)
        return df is not None and not df.empty
    except Exception as e:
        logger.warning(f"[Tushare] 健康检查失败: {e}")
        return False
```

调用 `trade_cal(limit=1)` 验证连接，比默认的 `get_stock_list` 更轻量（架构 §9 Phase B）。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 tushare_client.py 骨架（类结构 + __init__ + 延迟初始化 pro_api） | backend | todo | |
| 2 | 实现 _enforce_rate_limit 和 _execute_with_retry | backend | todo | 与 AkShareDataSource 模式一致 |
| 3 | 实现 get_trading_calendar | backend | todo | AC-01 |
| 4 | 实现 get_stock_list | backend | todo | AC-02 |
| 5 | 实现 get_sector_list + _fetch_sectors_by_type 辅助方法 | backend | todo | AC-03 |
| 6 | 实现 get_daily_data + _symbol_to_ts_code 辅助方法 | backend | todo | AC-04 |
| 7 | 实现 get_sector_daily_data | backend | todo | AC-05 |
| 8 | 实现 health_check | backend | todo | |
| 9 | 更新 __init__.py 导出 TushareDataSource | backend | todo | |

## 5. 验收标准

### 后端验收

- [ ] AC-01 `get_trading_calendar()` 返回上交所交易日列表，仅包含交易日，日期按升序排列
- [ ] AC-02 `get_stock_list()` 返回全部上市 A 股，每条包含 symbol / name / market（SH/SZ/BJ）/ industry
- [ ] AC-03 `get_sector_list(sector_type="industry")` 返回行业板块列表，`get_sector_list(sector_type="concept")` 返回概念板块列表，每条包含 code / name / type
- [ ] AC-04 `get_daily_data(symbol, start, end)` 返回前复权日线数据，包含 open/high/low/close/volume/amount/turnover；amount 单位为元（×1000 转换）
- [ ] AC-05 `get_sector_daily_data(sector_name, sector_type, start, end)` 返回板块日线数据；自动将板块名称转换为板块代码查询
- [ ] AC-07 单次请求失败时自动重试最多 3 次（间隔 1s / 2s / 4s 指数退避），耗尽后抛出 RetryExhaustedError
- [ ] `health_check()` 返回 True（Token 有效时）或 False（Token 无效/网络不通时）
- [ ] 所有方法返回的数据符合对应 Pydantic 模型（StockInfo / SectorInfo / DailyQuote）
- [ ] 日志中不输出 Token 值（安全要求，架构 §8.3）
- [ ] E2E 不适用：本功能为纯后端数据源实现，无用户可观察 UI，通过 plan-03 全链路验证间接覆盖

### 性能验收（架构 §8.1 目标）

- [ ] 单次 Tushare API 调用延迟 < 5s（人工确认日志中的耗时记录）
- [ ] `get_stock_list()` 完整获取 < 30s（约 5000 只股票）

## 6. 验证命令

```bash
cd server

# 基础导入验证
python -c "
from src.services.data_acquisition.tushare_client import TushareDataSource
ds = TushareDataSource()
print(f'OK: TushareDataSource 创建成功, source_name={ds.source_name}')
"

# 需要配置 TUSHARE_TOKEN 后验证（以下命令需要有效 Token）
export TUSHARE_TOKEN=your_token_here

# health_check
python -c "
from src.services.data_acquisition.tushare_client import TushareDataSource
ds = TushareDataSource()
print(f'健康检查: {ds.health_check()}')
"

# get_trading_calendar
python -c "
from src.services.data_acquisition.tushare_client import TushareDataSource
ds = TushareDataSource()
dates = ds.get_trading_calendar()
print(f'交易日数量: {len(dates)}, 最新: {dates[-1] if dates else None}')
"

# get_stock_list
python -c "
from src.services.data_acquisition.tushare_client import TushareDataSource
ds = TushareDataSource()
stocks = ds.get_stock_list()
print(f'股票数量: {len(stocks)}, 示例: {stocks[0] if stocks else None}')
"

# get_sector_list
python -c "
from src.services.data_acquisition.tushare_client import TushareDataSource
ds = TushareDataSource()
sectors = ds.get_sector_list('industry')
print(f'行业板块数量: {len(sectors)}, 示例: {sectors[0] if sectors else None}')
"
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责（TushareDataSource）, §5 ADR-3/4/5/6, §7.2 字段映射, §8.1 性能目标, §8.2 重试策略, §8.5 可观测性
- **相关代码**:
  - `server/src/services/data_acquisition/akshare_client.py` — AkShareDataSource（参考限流/重试模式）
  - `server/src/services/data_acquisition/base.py` — BaseDataSource 抽象接口
  - `server/src/services/data_acquisition/models.py` — Pydantic 模型定义
  - `server/src/services/data_acquisition/exceptions.py` — 异常类
- **契约 / 数据对象**: StockInfo / SectorInfo / DailyQuote / List[date]
- **下游消费方**: plan-03（服务层通过 DataSourceFactory 调用）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→...→9）
- **验证失败排查方向**: 检查 TUSHARE_TOKEN 是否有效；检查网络是否可达 Tushare 服务；检查账户积分是否 ≥ 6000（ths_index/ths_daily）
- **允许修改的额外文件**: `server/src/services/data_acquisition/__init__.py`（更新导出）
- **暂停条件**: Tushare API 连接不通或 Token 无效；积分不足无法调用 ths_index
- **E2E 不适用说明**: 本功能为纯后端数据源实现，无用户可观察 UI，通过 plan-03 全链路验证间接覆盖
- **风险备注**:
  - ths_index / ths_daily 需 6000 积分，积分不足时调用会报错
  - pro_bar 内部返回数据量限制约 5000 行，当前场景（单只股票指定日期范围）通常不触发
  - amount 字段 Tushare 返回单位为千元，需 ×1000 转为元（架构 §7.2）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| TUSHARE_TOKEN 未配置 | _get_pro_api 抛出 DataFetchError | todo |
| Tushare 服务不可用 | _execute_with_retry 重试 3 次后抛出 RetryExhaustedError | todo |
| 积分不足调用 ths_index | Tushare 返回权限错误，转换为 DataFetchError | todo |
| 频率超限 | _enforce_rate_limit 控制请求间隔 | todo |
| 返回空 DataFrame | get_daily_data/get_sector_daily_data 返回空列表 | todo |
| 股票代码无法映射市场后缀 | _symbol_to_ts_code 原样返回 | todo |
| 板块名称未找到对应 ts_code | get_sector_daily_data 返回空列表并记录 WARNING | todo |
| 日志中不输出 Token | 只记录 api_url 和 source_name | todo |
