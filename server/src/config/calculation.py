"""
计算引擎配置常量

定义强度计算引擎的所有配置参数。
"""

from typing import Dict, List

# =============================================================================
# 默认周期配置
# =============================================================================

DEFAULT_PERIOD_CONFIGS = [
    {"period": "5d", "name": "5日均线", "days": 5, "weight": 0.15, "is_active": True},
    {"period": "10d", "name": "10日均线", "days": 10, "weight": 0.20, "is_active": True},
    {"period": "20d", "name": "20日均线", "days": 20, "weight": 0.25, "is_active": True},
    {"period": "30d", "name": "30日均线", "days": 30, "weight": 0.20, "is_active": True},
    {"period": "60d", "name": "60日均线", "days": 60, "weight": 0.20, "is_active": True},
]

# 周期到天数映射
PERIOD_TO_DAYS = {
    "5d": 5,
    "10d": 10,
    "20d": 20,
    "30d": 30,
    "60d": 60,
}

# 周期权重映射
PERIOD_WEIGHTS = {
    "5d": 0.15,
    "10d": 0.20,
    "20d": 0.25,
    "30d": 0.20,
    "60d": 0.20,
}

# =============================================================================
# 强度得分范围
# =============================================================================

STRENGTH_SCORE_MIN = 0.0
STRENGTH_SCORE_MAX = 100.0

# 价格比率范围（用于归一化）
PRICE_RATIO_MIN = -10.0  # -10%
PRICE_RATIO_MAX = 10.0   # +10%

# 强度等级阈值
STRENGTH_LEVEL_THRESHOLDS = {
    "very_strong": 80,      # 非常强势
    "strong": 65,           # 强势
    "moderate_strong": 50,  # 偏强
    "neutral": 35,          # 中性
    "moderate_weak": 20,    # 偏弱
    "weak": 10,             # 弱势
    "very_weak": 0,         # 非常弱势
}

# 强度等级描述
STRENGTH_LEVEL_NAMES = {
    "very_strong": "非常强势",
    "strong": "强势",
    "moderate_strong": "偏强",
    "neutral": "中性",
    "moderate_weak": "偏弱",
    "weak": "弱势",
    "very_weak": "非常弱势",
}

# =============================================================================
# 趋势方向
# =============================================================================

class TrendDirection:
    """趋势方向常量"""
    UP = 1         # 上升
    NEUTRAL = 0    # 横盘/中性
    DOWN = -1      # 下降

# 趋势方向描述
TREND_DIRECTION_NAMES = {
    TrendDirection.UP: "上升",
    TrendDirection.NEUTRAL: "横盘",
    TrendDirection.DOWN: "下降",
}

# =============================================================================
# 实体类型
# =============================================================================

class EntityType:
    """实体类型常量"""
    STOCK = "stock"     # 股票
    SECTOR = "sector"   # 板块

# =============================================================================
# 批量计算配置
# =============================================================================

BATCH_SIZE = 100           # 每批处理数量
MAX_CONCURRENT = 10        # 最大并发数
CALCULATION_TIMEOUT = 30   # 单个实体计算超时时间（秒）

# 最小数据量要求
MIN_DATA_DAYS = 60         # 最少需要的历史数据天数

# =============================================================================
# 性能要求
# =============================================================================

# 1000 只股票全周期计算目标时间
TARGET_BATCH_TIME = 30  # 秒

# 单只股票按需计算目标时间
TARGET_SINGLE_TIME = 0.1  # 秒 (100ms)

# =============================================================================
# 价格位置阈值
# =============================================================================

# 用于判断价格相对于均线的位置
PRICE_POSITION_THRESHOLDS = {
    "far_above": 1.0,        # 远高于（比率 > 1%）
    "above": 0.2,            # 高于（比率 > 0.2%）
    "middle_low": -0.2,      # 中性下限（比率 > -0.2%）
    "below": -1.0,           # 低于（比率 < -1%）
    "far_below": -2.0,       # 远低于（比率 < -2%）
}

# =============================================================================
# 趋势强度计算配置
# =============================================================================

TREND_STRENGTH_WINDOW = 5  # 趋势强度计算窗口（天数）

# =============================================================================
# 数据质量检查
# =============================================================================

# 数据缺失阈值
DATA_MISSING_THRESHOLD = 0.1  # 允许 10% 的数据缺失

# 价格异常值检测阈值
PRICE_ANOMALY_THRESHOLD = 0.5  # 单日涨跌幅超过 50% 视为异常

# =============================================================================
# 缓存配置
# =============================================================================

# 计算结果缓存时间（秒）
CALCULATION_CACHE_TTL = 300  # 5 分钟

# =============================================================================
# 辅助函数
# =============================================================================

def get_period_configs(active_only: bool = True) -> List[Dict]:
    """
    获取周期配置列表

    Args:
        active_only: 是否只返回激活的周期

    Returns:
        周期配置列表
    """
    if active_only:
        return [pc for pc in DEFAULT_PERIOD_CONFIGS if pc.get("is_active", True)]
    return DEFAULT_PERIOD_CONFIGS.copy()


def get_period_weights() -> Dict[str, float]:
    """
    获取周期权重字典

    Returns:
        周期权重映射
    """
    return PERIOD_WEIGHTS.copy()


def get_strength_level(score: float) -> str:
    """
    根据得分获取强度等级

    Args:
        score: 强度得分

    Returns:
        强度等级名称
    """
    if score is None:
        return "未知"

    if score >= STRENGTH_LEVEL_THRESHOLDS["very_strong"]:
        return STRENGTH_LEVEL_NAMES["very_strong"]
    elif score >= STRENGTH_LEVEL_THRESHOLDS["strong"]:
        return STRENGTH_LEVEL_NAMES["strong"]
    elif score >= STRENGTH_LEVEL_THRESHOLDS["moderate_strong"]:
        return STRENGTH_LEVEL_NAMES["moderate_strong"]
    elif score >= STRENGTH_LEVEL_THRESHOLDS["neutral"]:
        return STRENGTH_LEVEL_NAMES["neutral"]
    elif score >= STRENGTH_LEVEL_THRESHOLDS["moderate_weak"]:
        return STRENGTH_LEVEL_NAMES["moderate_weak"]
    elif score >= STRENGTH_LEVEL_THRESHOLDS["weak"]:
        return STRENGTH_LEVEL_NAMES["weak"]
    else:
        return STRENGTH_LEVEL_NAMES["very_weak"]


def get_trend_name(trend: int) -> str:
    """
    获取趋势方向名称

    Args:
        trend: 趋势方向值

    Returns:
        趋势方向名称
    """
    return TREND_DIRECTION_NAMES.get(trend, "未知")


def is_valid_score(score: float) -> bool:
    """
    检查得分是否有效

    Args:
        score: 强度得分

    Returns:
        是否有效
    """
    return score is not None and STRENGTH_SCORE_MIN <= score <= STRENGTH_SCORE_MAX
