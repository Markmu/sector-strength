"""
数据获取服务数据模型

定义从数据源获取的数据结构和验证模型。
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class StockInfo(BaseModel):
    """股票基本信息"""

    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: Optional[str] = Field(None, description="市场类型: SH/SZ")
    industry: Optional[str] = Field(None, description="所属行业")
    list_date: Optional[date] = Field(None, description="上市日期")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码格式"""
        v = v.strip().upper()
        if not v:
            raise ValueError("股票代码不能为空")
        return v

    @field_validator("market")
    @classmethod
    def validate_market(cls, v: Optional[str]) -> Optional[str]:
        """验证市场类型"""
        if v is not None:
            v = v.strip().upper()
            if v not in ("SH", "SZ", "BJ"):
                raise ValueError(f"无效的市场类型: {v}")
        return v


class SectorInfo(BaseModel):
    """板块信息"""

    code: str = Field(..., description="板块代码")
    name: str = Field(..., description="板块名称")
    type: str = Field(..., description="板块类型: industry/concept")
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
        if v not in ("industry", "concept"):
            raise ValueError(f"无效的板块类型: {v}")
        return v


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


class SectorConstituent(BaseModel):
    """板块成分股"""

    sector_code: str = Field(..., description="板块代码")
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    weight: Optional[float] = Field(None, description="权重", ge=0, le=100)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码"""
        v = v.strip().upper()
        if not v:
            raise ValueError("股票代码不能为空")
        return v


class DataFetchResult(BaseModel):
    """
    数据获取结果封装

    用于统一返回数据获取操作的结果，包括成功状态、数据、错误信息等。
    """

    success: bool = Field(..., description="是否成功")
    data: Optional[
        List[StockInfo] | List[SectorInfo] | List[DailyQuote] | List[SectorConstituent]
    ] = Field(None, description="返回数据")
    error_message: Optional[str] = Field(None, description="错误消息")
    cached: bool = Field(False, description="是否来自缓存")
    timestamp: datetime = Field(default_factory=datetime.now, description="获取时间")


# 批量数据类型别名
StockList = List[StockInfo]
SectorList = List[SectorInfo]
DailyQuoteList = List[DailyQuote]
SectorConstituentList = List[SectorConstituent]
