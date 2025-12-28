"""
批量处理协调器

协调多个实体的批量强度计算，支持异步并发处理。
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date
from dataclasses import dataclass
import logging

from .base_calculator import BaseCalculator, CalculationResult
from .strength_calculator import StrengthCalculator
from .trend_analyzer import TrendDirection

logger = logging.getLogger(__name__)


@dataclass
class BatchCalculationResult:
    """
    批量计算结果

    Attributes:
        total_count: 总实体数
        success_count: 成功计算数
        failure_count: 失败计算数
        results: 结果字典 {entity_id: result_data}
        errors: 错误字典 {entity_id: error_message}
        duration_seconds: 计算耗时（秒）
    """
    total_count: int
    success_count: int
    failure_count: int
    results: Dict[str, Any]
    errors: Dict[str, str]
    duration_seconds: float

    def __repr__(self) -> str:
        return (
            f"<BatchCalculationResult("
            f"total={self.total_count}, "
            f"success={self.success_count}, "
            f"failure={self.failure_count}, "
            f"duration={self.duration_seconds:.2f}s)>"
        )


class BatchProcessor(BaseCalculator):
    """
    批量处理协调器

    支持异步并发计算多个股票/板块的强度得分。
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化批量处理器

        Args:
            config: 配置参数，可包含:
                - batch_size: 每批处理数量（默认 100）
                - max_concurrent: 最大并发数（默认 10）
                - timeout: 单个实体计算超时时间（秒，默认 30）
        """
        super().__init__(config)
        self.batch_size = config.get("batch_size", 100) if config else 100
        self.max_concurrent = config.get("max_concurrent", 10) if config else 10
        self.timeout = config.get("timeout", 30) if config else 30

        # 初始化强度计算器
        self.strength_calculator = StrengthCalculator(config)

    async def calculate(
        self,
        entities_data: Dict[str, Dict],
        period_configs: List[Dict],
    ) -> CalculationResult:
        """
        批量计算强度

        Args:
            entities_data: 实体数据字典 {entity_id: {prices, current_price}}
            period_configs: 周期配置列表

        Returns:
            CalculationResult: 包含批量计算结果
        """
        if not self.validate_input(entities_data):
            return CalculationResult(
                success=False,
                error="实体数据无效"
            )

        try:
            result = await self.batch_calculation(entities_data, period_configs)
            return CalculationResult(success=True, data=result)
        except Exception as e:
            return CalculationResult(success=False, error=f"批量计算失败: {str(e)}")

    async def batch_calculation(
        self,
        entities_data: Dict[str, Dict],
        period_configs: List[Dict],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BatchCalculationResult:
        """
        批量计算多个实体的强度得分

        Args:
            entities_data: 实体数据 {entity_id: {prices: Series, current_price: float}}
            period_configs: 周期配置列表
            progress_callback: 进度回调函数 (current, total)

        Returns:
            BatchCalculationResult: 批量计算结果
        """
        start_time = datetime.now()
        total_count = len(entities_data)
        results = {}
        errors = {}
        success_count = 0
        failure_count = 0

        logger.info(f"开始批量计算，共 {total_count} 个实体")

        # 分批处理
        entity_ids = list(entities_data.keys())
        for i in range(0, len(entity_ids), self.batch_size):
            batch_ids = entity_ids[i:i + self.batch_size]
            batch_data = {eid: entities_data[eid] for eid in batch_ids}

            # 并发计算当前批次
            batch_results = await self._calculate_batch(
                batch_data, period_configs
            )

            # 收集结果
            for entity_id, result in batch_results.items():
                if "error" in result:
                    errors[entity_id] = result["error"]
                    failure_count += 1
                else:
                    results[entity_id] = result
                    success_count += 1

            # 报告进度
            if progress_callback:
                progress_callback(len(results), total_count)

            logger.info(
                f"批次 {i // self.batch_size + 1} 完成: "
                f"{len(batch_ids)} 个实体"
            )

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"批量计算完成: 成功 {success_count}, 失败 {failure_count}, "
            f"耗时 {duration:.2f} 秒"
        )

        return BatchCalculationResult(
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            results=results,
            errors=errors,
            duration_seconds=duration,
        )

    async def _calculate_batch(
        self,
        batch_data: Dict[str, Dict],
        period_configs: List[Dict],
    ) -> Dict[str, Dict]:
        """
        计算一个批次的数据

        Args:
            batch_data: 批次数据
            period_configs: 周期配置

        Returns:
            批次结果字典
        """
        # 创建并发任务
        tasks = []
        for entity_id, entity_data in batch_data.items():
            task = self._calculate_entity_safe(
                entity_id, entity_data, period_configs
            )
            tasks.append(task)

        # 限制并发数
        results = {}
        for i in range(0, len(tasks), self.max_concurrent):
            batch_tasks = tasks[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 处理结果
            for j, result in enumerate(batch_results):
                entity_id = list(batch_data.keys())[i + j]
                if isinstance(result, Exception):
                    results[entity_id] = {
                        "error": f"计算异常: {str(result)}"
                    }
                else:
                    results[entity_id] = result

        return results

    async def _calculate_entity_safe(
        self,
        entity_id: str,
        entity_data: Dict,
        period_configs: List[Dict],
    ) -> Dict:
        """
        安全地计算单个实体（带超时保护）

        Args:
            entity_id: 实体 ID
            entity_data: 实体数据
            period_configs: 周期配置

        Returns:
            计算结果字典
        """
        try:
            # 使用超时保护
            result = await asyncio.wait_for(
                self._calculate_single_entity(entity_data, period_configs),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            return {
                "error": f"计算超时（超过 {self.timeout} 秒）",
                "entity_id": entity_id,
            }
        except Exception as e:
            return {
                "error": f"计算失败: {str(e)}",
                "entity_id": entity_id,
            }

    async def _calculate_single_entity(
        self,
        entity_data: Dict,
        period_configs: List[Dict],
    ) -> Dict:
        """
        计算单个实体的强度数据

        Args:
            entity_data: 实体数据 {prices, current_price}
            period_configs: 周期配置

        Returns:
            计算结果字典
        """
        prices = entity_data.get("prices")
        current_price = entity_data.get("current_price")

        if prices is None or current_price is None:
            return {
                "error": "缺少必要数据（prices 或 current_price）"
            }

        # 使用强度计算器
        result = self.strength_calculator.calculate_entity_strength(
            prices=prices,
            current_price=current_price,
            period_configs=period_configs,
        )

        return result

    def prepare_prices_series(
        self,
        price_data: List[Dict[str, Any]],
    ) -> pd.Series:
        """
        准备价格序列

        Args:
            price_data: 价格数据列表，如:
                [{'date': '2024-01-01', 'close': 100.0}, ...]

        Returns:
            价格 Series（索引为日期）
        """
        if not price_data:
            return pd.Series(dtype=float)

        df = pd.DataFrame(price_data)
        if 'date' not in df.columns or 'close' not in df.columns:
            return pd.Series(dtype=float)

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')

        return df['close']

    def validate_data_sufficiency(
        self,
        prices: pd.Series,
        required_periods: List[int],
    ) -> Dict[str, any]:
        """
        验证数据是否充足

        Args:
            prices: 价格序列
            required_periods: 需要的周期列表

        Returns:
            验证结果字典
        """
        max_period = max(required_periods) if required_periods else 0
        data_length = len(prices)

        is_sufficient = data_length >= max_period
        missing_days = max(0, max_period - data_length)

        return {
            "is_sufficient": is_sufficient,
            "data_length": data_length,
            "required_length": max_period,
            "missing_days": missing_days,
            "can_calculate_partial": data_length >= min(required_periods) if required_periods else False,
        }

    async def calculate_sector_from_stocks(
        self,
        stock_strengths: Dict[str, float],
        stock_market_caps: Dict[str, float],
    ) -> float:
        """
        从成分股计算板块强度

        Args:
            stock_strengths: 成分股强度
            stock_market_caps: 成分股市值

        Returns:
            板块强度得分
        """
        return self.strength_calculator.calculate_sector_strength_from_stocks(
            stock_strengths, stock_market_caps
        )
