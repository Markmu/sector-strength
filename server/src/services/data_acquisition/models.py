"""
数据获取服务数据模型

定义从数据源获取的数据结构和验证模型。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .exceptions import DataSourceError
from .sector_types import SECTOR_TYPES


# A 股交易所集合：在全表扫描 stocks 时用于排除港股（HKEX）等非 A 股标的
A_STOCK_EXCHANGES = ("SSE", "SZSE", "BSE")


class StockInfo(BaseModel):
    """股票基本信息 — 与 Tushare stock_basic 输出字段对齐"""

    # 必填字段
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")

    # Tushare stock_basic 基础字段
    ts_code: Optional[str] = Field(None, description="TS 代码（如 000001.SZ）")
    area: Optional[str] = Field(None, description="地域（如 深圳）")
    industry: Optional[str] = Field(None, description="所属行业（如 银行）")
    fullname: Optional[str] = Field(None, description="股票全称")
    enname: Optional[str] = Field(None, description="英文全称")
    cnspell: Optional[str] = Field(None, description="拼音缩写")
    market: Optional[str] = Field(None, description="市场类型（主板/创业板/科创板/CDR）")
    exchange: Optional[str] = Field(None, description="交易所（SSE/SZSE/BSE）")
    curr_type: Optional[str] = Field(None, description="交易货币")
    list_status: Optional[str] = Field(None, description="上市状态: L 上市 D 退市 P 暂停 G 过会")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    is_hs: Optional[str] = Field(None, description="是否沪深港通标的: N 否 H 沪股通 S 深股通")
    act_name: Optional[str] = Field(None, description="实控人名称")
    act_ent_type: Optional[str] = Field(None, description="实控人企业性质")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码格式"""
        v = v.strip().upper()
        if not v:
            raise ValueError("股票代码不能为空")
        return v

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, v: Optional[str]) -> Optional[str]:
        """验证交易所代码（A 股 SSE/SZSE/BSE + 港股 HKEX）"""
        if v is not None:
            v = v.strip().upper()
            if v not in ("SSE", "SZSE", "BSE", "HKEX", ""):
                raise ValueError(f"无效的交易所代码: {v}")
        return v

    @field_validator("list_status")
    @classmethod
    def validate_list_status(cls, v: Optional[str]) -> Optional[str]:
        """验证上市状态"""
        if v is not None:
            v = v.strip().upper()
            if v not in ("L", "D", "P", "G", ""):
                raise ValueError(f"无效的上市状态: {v}")
        return v

    @field_validator("is_hs")
    @classmethod
    def validate_is_hs(cls, v: Optional[str]) -> Optional[str]:
        """验证沪深港通标的标识"""
        if v is not None:
            v = v.strip().upper()
            if v not in ("N", "H", "S", ""):
                raise ValueError(f"无效的沪深港通标识: {v}")
        return v


class SectorInfo(BaseModel):
    """板块信息"""

    code: str = Field(..., description="板块代码")
    name: str = Field(..., description="板块名称")
    type: str = Field(..., description="板块类型: industry/concept/region")
    description: Optional[str] = Field(None, description="板块描述")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证板块代码"""
        v = v.strip()
        if not v:
            raise ValueError("板块代码不能为空")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证板块类型"""
        v = v.strip().lower()
        if v not in SECTOR_TYPES:
            raise ValueError(f"无效的板块类型: {v}")
        return v


class SectorMemberInfo(BaseModel):
    """板块成分股信息"""

    sector_code: str = Field(..., description="板块代码 (ts_code 格式，如 850121.SI)")
    stock_codes: List[str] = Field(
        default_factory=list,
        description="成分股 symbol 列表 (短码格式，如 000001)",
    )


class DailyQuote(BaseModel):
    """日线行情数据"""

    symbol: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价", ge=0)
    high: float = Field(..., description="最高价", ge=0)
    low: float = Field(..., description="最低价", ge=0)
    close: float = Field(..., description="收盘价", ge=0)
    volume: float = Field(..., description="成交量", ge=0)
    amount: Optional[float] = Field(None, description="成交额", ge=0)
    turnover: Optional[float] = Field(None, description="换手率")


class TradingCalendarEntry(BaseModel):
    """交易日历条目（含开市/休市标记）

    闭区间全量记录中的一个自然日。``TradingCalendarRepository.refresh_range``
    据此构造闭区间一一对应校验后写入本地 ``trading_calendar_days`` 表。

    与旧 ``get_trading_calendar() -> List[date]``（仅开市日、过滤休市）的区别：
    本条目不过滤 ``is_open``，首页缺口轴与非交易日守卫需要休市日锚点（架构 ADR-6）。
    """

    cal_date: date = Field(..., description="自然日")
    is_open: bool = Field(..., description="是否开市（True 开市 / False 休市）")


class MarketDailyQuote(BaseModel):
    """全市场单日未复权日线行情（Tushare ``daily`` 当批响应，第 16 期 plan-02）

    数值一律 ``Decimal``（适配器以 ``Decimal(str(value))`` 构造，禁止 binary float
    累加路径，架构 §6.1.4）。单位保持 Tushare 原始口径：``vol`` 单位=手、
    ``amount`` 单位=千元；单位转换（手×100 → 股、千元×1000 → 元）在 plan-03
    汇总服务完成。
    """

    ts_code: str = Field(..., description="TS 代码（如 000001.SZ）")
    trade_date: date = Field(..., description="交易日期")
    close: Decimal = Field(..., description="未复权收盘价（元）")
    pre_close: Optional[Decimal] = Field(
        None, description="未复权前收盘价（元），历史窗口模式可为空"
    )
    vol: Decimal = Field(..., description="成交量（手，Tushare 原始单位）")
    amount: Decimal = Field(..., description="成交额（千元，Tushare 原始单位）")


class SuspensionRecord(BaseModel):
    """停牌查询原始行（Tushare ``suspend_d`` 响应，第 16 期 plan-02）

    适配器忠实返回 Provider 全量行、不做日期过滤（原始数据保真）：
    实测上游代理忽略 ``suspend_date`` 查询过滤（不同日期返回同一批全量行），
    且把停牌日期列命名为 ``trade_date``（官方 schema 为 ``suspend_date``，
    适配器双键归一化）；调用方（plan-03）必须按
    ``record.suspend_date == trade_date`` 客户端过滤后才能作为当日停牌证据，
    ``suspend_type='S'`` 与全天停牌判定同样由 plan-03 做（ADR-3）。
    """

    ts_code: str = Field(..., description="TS 代码")
    suspend_date: date = Field(
        ...,
        description="停牌日期（上游 suspend_date/trade_date 列归一化，供调用方客户端过滤当日记录）",
    )
    suspend_type: str = Field(
        ..., description="停牌类型：S 连续停牌 / R 复牌等，判定交 plan-03"
    )
    suspend_timing: Optional[str] = Field(
        None, description="停牌时段（如开盘/尾盘；连续停牌常为空）"
    )


class LifecycleStock(BaseModel):
    """生命周期股票（``stock_basic`` L/D/P/G 四状态合并快照，第 16 期 plan-02）

    只承载采集映射，不写库；L/D/P 强制 ``list_date``、D 强制 ``delist_date``、
    G 固定排除等集合校验由 plan-03 ``LifecycleSnapshot`` 做（ADR-2）。
    """

    ts_code: str = Field(..., description="TS 代码")
    exchange: str = Field(..., description="交易所（SSE/SZSE/BSE）")
    list_status: str = Field(..., description="上市状态: L 上市 D 退市 P 暂停 G 过会")
    name: Optional[str] = Field(None, description="股票名称")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")


class MarketDataIntegrityError(DataSourceError):
    """市场量价数据完整性错误（第 16 期 plan-02 新增）

    分页守卫（页签名重复 / 满页无新增 key / 跨页重复行 key / 页数超过硬上限）
    或行级校验（日期谓词、批次归属、数值非法）触发。错误信息必须包含页数与
    计数上下文，供调用方（plan-03）判定整日失败；**禁止 drop_duplicates
    静默修复**（架构 §6.1 实现原则）。
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        endpoint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化市场数据完整性异常

        Args:
            message: 错误消息（含页数/计数/ts_code 上下文）
            source: 数据源名称（如 "Tushare"）
            endpoint: API 端点或方法名（如 "daily"）
            original_error: 原始异常对象
        """
        self.endpoint = endpoint
        super().__init__(message, source, original_error)


class FundInfo(BaseModel):
    """基金基本信息 — 与 Tushare fund_basic 输出字段对齐"""

    ts_code: Optional[str] = Field(None, description="TS代码")
    name: Optional[str] = Field(None, description="基金名称")
    management: Optional[str] = Field(None, description="管理人")
    custodian: Optional[str] = Field(None, description="托管人")
    fund_type: Optional[str] = Field(None, description="基金类型")
    invest_type: Optional[str] = Field(None, description="投资类型")
    benchmark: Optional[str] = Field(None, description="业绩比较基准")
    market: Optional[str] = Field(None, description="市场类型: E 场内 O 场外")
    found_date: Optional[str] = Field(None, description="成立日期 YYYYMMDD")
    list_date: Optional[str] = Field(None, description="上市日期 YYYYMMDD")
    delist_date: Optional[str] = Field(None, description="退市日期 YYYYMMDD")
    status: Optional[str] = Field(None, description="状态: D 存续 I 发行 E 到期")


class EtfShareInfo(BaseModel):
    """ETF 日份额数据 — 与 Tushare fund_share 输出字段对齐（第 14 期）

    fd_share 单位为万份，与 etf_daily.share 存储口径一致。
    """

    ts_code: Optional[str] = Field(None, description="TS代码")
    trade_date: Optional[str] = Field(None, description="交易日 YYYYMMDD")
    fd_share: float = Field(..., description="基金份额（万份）")
    fund_type: Optional[str] = Field(None, description="基金类型（ETF）")
    market: Optional[str] = Field(None, description="市场类型: E 场内")


class EtfNavInfo(BaseModel):
    """ETF 单位净值数据 — 与 Tushare fund_nav 输出字段对齐（第 14 期）

    unit_nav 单位为元，与 etf_daily.unit_nav 存储口径一致。
    """

    ts_code: Optional[str] = Field(None, description="TS代码")
    unit_nav: float = Field(..., description="单位净值（元）")
    nav_date: Optional[str] = Field(None, description="净值日期 YYYYMMDD")


class DataFetchResult(BaseModel):
    """
    数据获取结果封装

    用于统一返回数据获取操作的结果，包括成功状态、数据、错误信息等。
    """

    success: bool = Field(..., description="是否成功")
    data: Optional[List[StockInfo] | List[SectorInfo] | List[DailyQuote]] = Field(
        None, description="返回数据"
    )
    error_message: Optional[str] = Field(None, description="错误消息")
    cached: bool = Field(False, description="是否来自缓存")
    timestamp: datetime = Field(default_factory=datetime.now, description="获取时间")


# 批量数据类型别名
StockList = List[StockInfo]
SectorList = List[SectorInfo]
DailyQuoteList = List[DailyQuote]
