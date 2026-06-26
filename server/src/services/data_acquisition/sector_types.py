"""
板块类型统一定义

集中管理所有板块类型的常量映射，作为后端唯一的类型真相源。
仅保留行业/概念/地域三种板块类型。
"""

# 所有合法的板块类型 key
SECTOR_TYPES = ("industry", "concept", "region")

# 内部 key → Tushare API type 参数
THS_TYPE_MAP = {
    "industry": "I",
    "concept": "N",
    "region": "R",
}

# Tushare API type 代码 → 中文标签
THS_TYPE_LABEL = {
    "I": "行业",
    "N": "概念",
    "R": "地域",
}

# 内部 key → 简短中文标签
SECTOR_TYPE_LABELS = {
    "industry": "行业",
    "concept": "概念",
    "region": "地域",
}


def is_valid_sector_type(sector_type: str) -> bool:
    """检查是否为合法的板块类型"""
    return sector_type in SECTOR_TYPES
