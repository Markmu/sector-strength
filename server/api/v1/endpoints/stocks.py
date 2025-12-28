"""股票相关 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.db.database import get_db
from src.models.stock import Stock

router = APIRouter()

@router.get("/stocks", response_model=List[dict])
async def get_stocks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取股票列表"""
    # TODO: 实现股票列表查询逻辑
    return [{"message": "股票列表端点 - 待实现"}]

@router.get("/stocks/{stock_id}", response_model=dict)
async def get_stock(
    stock_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个股票详情"""
    # TODO: 实现股票详情查询逻辑
    return {"message": f"股票详情 {stock_id} - 待实现"}