"""
数据获取服务数据模型

定义从数据源获取的数据结构和验证模型。
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

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
