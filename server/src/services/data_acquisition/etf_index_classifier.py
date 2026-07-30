"""ETF 指数归集器（第 14 期）

从 ETF 的 ``benchmark`` 文本（如"沪深300指数收益率×100%"）和 ``name`` 中归集出
跟踪的指数名（index_name）与分类（category: broad/industry/other）。

设计要点（ADR-2）：
- 宽基精确枚举：维护宽基指数名清单，**精确匹配**提取出的指数名，避免"沪深300
  自由现金流"被误归"沪深300"——优先匹配更长的指数名（清单按长度降序排列），
  且对提取出的纯指数名做整串相等比较，而非子串包含。
- 行业关键词规则：从 benchmark/name 提取行业主题匹配。
- other 兜底：宽基与行业都未命中，不抛异常，index_name 取清洗后的指数名或 None。

返回 ``classify(benchmark, name) -> (index_name, category)``。
"""

import re
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 宽基指数精确枚举
#
# 关键：清单按名称长度降序排列，匹配时取首个整串相等的指数名。
# 这样"沪深300自由现金流"（若未来加入）会先于"沪深300"匹配；同时由于是对
# **提取出的纯指数名**做整串比较（非子串包含），"沪深300自由现金流"不会等于
# "沪深300"，从而避免误归类。基础宽基名见 _BROAD_BASE_NAMES。
# ---------------------------------------------------------------------------
_BROAD_BASE_NAMES: List[str] = [
    # 长名优先（避免被短名先匹配）
    "科创创业50",
    "沪深300自由现金流",
    "中证500自由现金流",
    "中证A1000",
    "中证A500",
    "中证A50",
    "中证1000",
    "中证500",
    "中证100",
    "上证180",
    "上证50",
    "深证100",
    "创业板50",
    "创业板指",
    "科创100",
    "科创50",
    "北证50",
    "沪深300",
]

# 行业关键词（出现即归 industry）
_INDUSTRY_KEYWORDS: List[str] = [
    "半导体", "芯片", "集成电路", "新能源", "光伏", "锂电", "稀土", "储能",
    "医药", "医疗", "生物医药", "创新药", "中药", "银行", "券商", "证券",
    "保险", "食品饮料", "白酒", "消费", "军工", "国防", "化工", "有色金属",
    "煤炭", "钢铁", "房地产", "地产", "电力", "电信", "通信", "传媒",
    "游戏", "旅游", "航空", "汽车", "机械", "家电", "建材", "农业",
    "环保", "有色", "计算机", "电子", "软件", "机器人", "人工智能",
    "黄金", "原油", "石油", "铜", "5G", "物联网", "碳中和",
]


def _extract_index_name_from_benchmark(benchmark: Optional[str]) -> Optional[str]:
    """从 benchmark 文本中提取"指数收益率"前的指数名。

    典型输入："沪深300指数收益率×100%" / "创业板指收益率×100%"
    返回："沪深300" / "创业板指"。

    匹配策略（按优先级）：
    1. ``<name>指数收益率`` → 截取 <name>（"指数"二字作为分隔）
    2. ``<name>收益率`` → 截取 <name>
    3. 取"×"/"*"/"X"/百分号等分隔符前的整段，再清洗。
    """
    if not benchmark:
        return None
    text = str(benchmark).strip()
    if not text:
        return None

    # 1. <name>指数收益率 —— 最典型（沪深300指数收益率 → 沪深300）
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9·\.\-]+?)指数收益率", text)
    if m:
        name = m.group(1).strip()
        name = name.removeprefix("同期")
        return name or None

    # 2. <name>收益率（如"创业板指收益率"，无"指数"二字）
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9·\.\-]+?)收益率", text)
    if m:
        name = m.group(1).strip()
        name = name.removeprefix("同期")
        # 若以"指数"结尾，去掉"指数"二字保留核心名
        if name.endswith("指数"):
            name = name[: -len("指数")]
        return name or None

    # 3. 兜底：取分隔符（× * X % +）前的整段，清洗常见噪声词与尾部"指数"
    for sep in ["×", "*", "x", "X", "%", "＋", "+"]:
        if sep in text:
            head = text.split(sep, 1)[0].strip()
            for noise in ("同期", "跟踪", "标的"):
                head = head.removeprefix(noise)
            if head:
                if head.endswith("指数"):
                    head = head[: -len("指数")]
                return head or None
            break

    return None


def classify(
    benchmark: Optional[str], name: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """归集 ETF 跟踪指数。

    Args:
        benchmark: 业绩比较基准文本（如"沪深300指数收益率×100%"）。
        name: ETF 产品名（如"华泰柏瑞沪深300ETF"），辅助匹配。

    Returns:
        (index_name, category)
        - index_name: 归集出的指数名，未命中宽基/行业时为清洗后的指数名或 None
        - category: "broad"（宽基）/ "industry"（行业）/ "other"（兜底）

    规则顺序：先从 benchmark 提取纯指数名 → 宽基精确枚举（整串相等，长名优先）
    → 行业关键词（在 extracted/benchmark/name 任一命中）→ other 兜底。
    归类失败不抛异常，归入 other。
    """
    benchmark_text = str(benchmark) if benchmark else ""
    name_text = str(name) if name else ""

    # 从 benchmark 提取清洗后的纯指数名（供宽基整串匹配）
    extracted = _extract_index_name_from_benchmark(benchmark_text)

    # 1. 宽基精确枚举：对提取出的纯指数名做整串相等比较（长名优先）。
    #    整串相等天然避免"沪深300自由现金流"误归"沪深300"。
    if extracted:
        for idx_name in _BROAD_BASE_NAMES:
            if extracted == idx_name:
                return idx_name, "broad"
        # 也容许 extracted 带前缀（如"中证沪深300"）含宽基名的情况：用精确边界
        # 子串匹配作为补充（宽基名前后不含中文/字母/数字）。
        for idx_name in _BROAD_BASE_NAMES:
            pattern = (
                r"(?<![\u4e00-\u9fa5A-Za-z0-9])"
                + re.escape(idx_name)
                + r"(?![\u4e00-\u9fa5A-Za-z0-9])"
            )
            if re.search(pattern, extracted):
                return idx_name, "broad"

    # 2. 行业关键词（在 extracted、benchmark、name 任一命中即归行业）
    industry_search_text = " ".join(
        [t for t in [extracted or "", benchmark_text, name_text] if t]
    )
    for kw in _INDUSTRY_KEYWORDS:
        if kw in industry_search_text:
            return kw, "industry"

    # 3. 兜底 other：index_name 取清洗后的指数名或 None，不抛异常
    if extracted:
        return extracted, "other"
    return None, "other"
