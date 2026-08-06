"""
板块类型统一定义

集中管理所有板块类型的常量映射，作为后端唯一的类型真相源。
- 同花顺板块：行业/概念/地域三种类型（SECTOR_TYPES）
- 申万行业：sw_industry 类型（L1/L2/L3 三级，与同花顺体系隔离）
"""

# 所有合法的板块类型 key（同花顺三类型）
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


# ======================================================================
# 申万行业分类（与同花顺体系隔离，独立 type/level 体系）
# ======================================================================

# 申万行业在 sectors.type 中的取值
SW_SECTOR_TYPE = "sw_industry"

# 申万行业层级（一级/二级/三级）
SW_LEVELS = ("L1", "L2", "L3")

# 申万行业分类标准（默认 2021 版；SW2014 为 2014 旧版）
SW_SRC = "SW2021"

# 申万行业类型 → 中文标签
SW_SECTOR_TYPE_LABELS = {
    SW_SECTOR_TYPE: "申万行业",
    "L1": "申万一级",
    "L2": "申万二级",
    "L3": "申万三级",
}
