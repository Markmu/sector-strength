"""
趋势分析服务

提供趋势特征识别功能，包括趋势方向判断、移动平均线趋势、横盘检测等。
"""

import logging
import numpy as np
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.strength_history_service import StrengthHistoryService

logger = logging.getLogger(__name__)


# 趋势类型定义
TREND_TYPES = {
    "strong_up": "强势上涨",      # 斜率 > 0.5
    "up": "上涨",               # 斜率 > 0.1
    "neutral": "震荡",          # -0.1 < 斜率 < 0.1
    "down": "下跌",             # 斜率 < -0.1
    "strong_down": "强势下跌"    # 斜率 < -0.5
}


class TrendAnalysisService:
    """
    趋势分析服务

    提供趋势特征识别、移动平均线趋势分析、横盘检测等功能。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化趋势分析服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.history_service = StrengthHistoryService(session)

    async def identify_trend(
        self,
        entity_type: str,
        entity_id: int,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        识别趋势特征

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            趋势分析结果
        """
        if end_date is None:
            end_date = date.today()

        # 获取历史数据
        history_data = await self.history_service.get_stock_history(
            entity_id, days, end_date
        ) if entity_type == "stock" else await self.history_service.get_sector_history(
            entity_id, days, end_date
        )

        if not history_data or len(history_data) < 3:
            return {
                "trend_type": "unknown",
                "confidence": "low",
                "error": "数据不足（至少需要3天数据）"
            }

        # 提取分数和日期
        scores = [float(d["score"]) for d in history_data if d.get("score") is not None]
        dates = [d["date"] for d in history_data]

        if len(scores) < 3:
            return {
                "trend_type": "unknown",
                "confidence": "low",
                "error": "有效数据不足"
            }

        # 1. 计算线性回归斜率
        x = np.arange(len(scores))
        z = np.polyfit(x, scores, 1)
        slope = float(z[0])

        # 2. 计算R²确定拟合优度
        p = np.poly1d(z)
        y_hat = p(x)
        y_bar = np.mean(scores)
        ss_tot = np.sum((scores - y_bar) ** 2)
        ss_res = np.sum((scores - y_hat) ** 2)
        r_squared = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0

        # 3. 计算趋势强度（斜率的绝对值）
        trend_strength = abs(slope)

        # 4. 判断趋势类型
        if slope > 0.5:
            trend_type = "strong_up"
            direction = "强势上涨"
        elif slope > 0.1:
            trend_type = "up"
            direction = "上涨"
        elif slope > -0.1:
            trend_type = "neutral"
            direction = "震荡"
        elif slope > -0.5:
            trend_type = "down"
            direction = "下跌"
        else:
            trend_type = "strong_down"
            direction = "强势下跌"

        # 5. 检测横盘整理
        consolidation = self._detect_consolidation(scores)

        # 6. 计算移动平均线趋势
        ma_trends = {}
        for window in [5, 10, 20]:
            if len(scores) >= window:
                ma_trends[f"ma{window}"] = self._calculate_ma_trend(scores, window)

        # 7. 计算置信度
        if r_squared > 0.7:
            confidence = "high"
        elif r_squared > 0.4:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "trend_type": trend_type,
            "trend_direction": direction,
            "trend_strength": round(trend_strength, 4),
            "slope": round(slope, 4),
            "r_squared": round(r_squared, 4),
            "confidence": confidence,
            "is_consolidating": consolidation["is_consolidating"],
            "consolidation_info": consolidation,
            "ma_trends": ma_trends,
            "start_date": dates[0].isoformat() if dates else None,
            "end_date": dates[-1].isoformat() if dates else None,
            "data_points": len(scores)
        }

    def _detect_consolidation(
        self,
        scores: List[float],
        threshold: float = 2.0
    ) -> Dict:
        """
        检测横盘整理

        Args:
            scores: 分数列表
            threshold: 波动阈值

        Returns:
            整理状态信息
        """
        if len(scores) < 5:
            return {
                "is_consolidating": False,
                "reason": "数据不足（需要至少5天数据）"
            }

        # 计算标准差
        std_dev = float(np.std(scores))

        # 计算价格范围
        price_range = float(max(scores) - min(scores))

        # 判断是否为横盘
        is_consolidating = std_dev < threshold and price_range < threshold * 3

        return {
            "is_consolidating": is_consolidating,
            "std_dev": round(std_dev, 2),
            "price_range": round(price_range, 2),
            "support_level": round(min(scores), 2),
            "resistance_level": round(max(scores), 2),
            "threshold": threshold
        }

    def _calculate_ma_trend(
        self,
        scores: List[float],
        window: int
    ) -> Dict:
        """
        计算移动平均线趋势

        Args:
            scores: 分数列表
            window: 窗口大小

        Returns:
            移动平均线趋势信息
        """
        if len(scores) < window:
            return {
                "window": window,
                "status": "insufficient_data"
            }

        # 计算移动平均
        ma_values = []
        for i in range(window - 1, len(scores)):
            ma = sum(scores[i - window + 1:i + 1]) / window
            ma_values.append(ma)

        # 判断MA方向
        if len(ma_values) >= 2:
            ma_slope = ma_values[-1] - ma_values[-2]

            if ma_slope > 0.5:
                ma_direction = "strong_up"
            elif ma_slope > 0.1:
                ma_direction = "up"
            elif ma_slope > -0.1:
                ma_direction = "flat"
            elif ma_slope > -0.5:
                ma_direction = "down"
            else:
                ma_direction = "strong_down"

            return {
                "window": window,
                "current_ma": round(ma_values[-1], 2),
                "previous_ma": round(ma_values[-2], 2),
                "ma_slope": round(ma_slope, 4),
                "direction": ma_direction,
                "status": "calculated"
            }

        return {
            "window": window,
            "status": "insufficient_data"
        }

    async def detect_consolidation(
        self,
        entity_type: str,
        entity_id: int,
        days: int = 30,
        threshold: float = 2.0,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        检测横盘整理状态

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            threshold: 波动阈值
            end_date: 结束日期

        Returns:
            整理状态信息
        """
        # 获取趋势分析
        trend_result = await self.identify_trend(
            entity_type, entity_id, days, end_date
        )

        if "error" in trend_result:
            return {
                "is_consolidating": False,
                "error": trend_result.get("error")
            }

        consolidation_info = trend_result.get("consolidation_info", {})
        consolidation_info["threshold_used"] = threshold

        return consolidation_info

    async def calculate_moving_avg_trend(
        self,
        entity_type: str,
        entity_id: int,
        window: int = 10,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        计算指定周期的移动平均线趋势

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            window: 移动平均窗口
            days: 查询天数
            end_date: 结束日期

        Returns:
            移动平均线趋势信息
        """
        # 获取趋势分析（包含所有MA趋势）
        trend_result = await self.identify_trend(
            entity_type, entity_id, days, end_date
        )

        ma_key = f"ma{window}"
        ma_trends = trend_result.get("ma_trends", {})

        if ma_key not in ma_trends:
            return {
                "window": window,
                "status": "not_available",
                "error": f"无法计算{window}日移动平均线趋势"
            }

        return ma_trends[ma_key]

    async def get_trend_summary(
        self,
        entity_type: str,
        entity_id: int,
        days: int = 30,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        获取趋势分析摘要

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            趋势摘要信息
        """
        trend_result = await self.identify_trend(
            entity_type, entity_id, days, end_date
        )

        if "error" in trend_result:
            return trend_result

        # 提取关键信息
        return {
            "trend_type": trend_result.get("trend_type"),
            "trend_direction": trend_result.get("trend_direction"),
            "confidence": trend_result.get("confidence"),
            "slope": trend_result.get("slope"),
            "is_consolidating": trend_result.get("is_consolidating"),
            "data_points": trend_result.get("data_points"),
            "period": f"最近{days}天",
            "start_date": trend_result.get("start_date"),
            "end_date": trend_result.get("end_date")
        }
