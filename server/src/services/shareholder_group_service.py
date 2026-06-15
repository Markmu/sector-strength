"""股东监控组管理服务

提供分组 CRUD、关键词编辑、匹配股数预览等业务逻辑。

安全要求（架构 §8.3）：
- LIKE 关键词先转义 % 和 _ 通配符，再通过参数绑定使用，禁止字符串拼接 SQL。
- 所有匹配统计基于 top10_float_holders 最新报告期。
"""

import logging
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.shareholder_group import ShareholderGroup, ShareholderGroupRule
from src.models.stock import Stock
from src.models.top10_float_holder import Top10FloatHolder
from src.repositories.shareholder_group_repository import ShareholderGroupRepository

logger = logging.getLogger(__name__)


# 预定义监控组及关键词种子（迁移脚本、测试 conftest 与本服务共享此定义）
PREDEFINED_GROUPS: list[dict[str, Any]] = [
    {
        "name": "国家队",
        "description": "汇金、证金等国家队资金",
        "sort_order": 1,
        "keywords": [
            "中央汇金",
            "中国证券金融",
            "国家外汇管理局",
            "国新投资",
            "基本养老保险基金",
        ],
    },
    {
        "name": "外资投行",
        "description": "著名外资投资银行",
        "sort_order": 2,
        "keywords": [
            "高盛",
            "摩根士丹利",
            "摩根大通",
            "瑞士银行",
            "美林",
            "花旗",
            "渣打",
        ],
    },
    {
        "name": "社保基金",
        "description": "全国社会保障基金",
        "sort_order": 3,
        "keywords": ["全国社保基金"],
    },
    {
        "name": "保险公司",
        "description": "保险资金",
        "sort_order": 4,
        "keywords": [
            "中国人寿",
            "中国平安",
            "中国太保",
            "新华保险",
            "泰康资产",
        ],
    },
    {
        "name": "私募基金",
        "description": "知名私募机构",
        "sort_order": 5,
        "keywords": [
            "高毅资产",
            "景林资产",
            "淡水泉",
            "重阳投资",
            "幻方量化",
            "九坤投资",
        ],
    },
]


def _escape_like_keyword(keyword: str) -> str:
    """转义 LIKE 关键词中的 % 和 _ 通配符（架构 §8.3 安全要求）。

    Args:
        keyword: 原始关键词

    Returns:
        转义后的关键词（% → \\%, _ → \\_）
    """
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ShareholderGroupService:
    """股东监控组管理服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ShareholderGroupRepository(session)

    # ============== 查询最新报告期 ==============

    async def _get_latest_report_period(self) -> Optional[Any]:
        """查询 top10_float_holders 表的最新报告期。"""
        stmt = select(func.max(Top10FloatHolder.report_period))
        result = await self.session.execute(stmt)
        return result.scalar()

    async def _count_matched_stocks(
        self, keywords: list[str], exclude_group_id: Optional[int] = None
    ) -> int:
        """用给定关键词在最新报告期对 holder_name 做 LIKE 匹配，统计去重股票数。

        安全要求：所有关键词先转义再参数绑定，不拼接 SQL。

        Args:
            keywords: 关键词列表
            exclude_group_id: 预览时可忽略某组（暂未在 SQL 中过滤，保留接口）

        Returns:
            匹配的去重股票数（最新报告期无数据时返回 0）
        """
        # 过滤空关键词
        clean_keywords = [kw for kw in keywords if kw and kw.strip()]
        if not clean_keywords:
            return 0

        latest_period = await self._get_latest_report_period()
        if latest_period is None:
            return 0

        # 构建 OR 组合的 LIKE 条件，每个关键词先转义通配符再包成 %keyword%
        like_conditions = [
            Top10FloatHolder.holder_name.like(
                f"%{_escape_like_keyword(kw)}%", escape="\\"
            )
            for kw in clean_keywords
        ]

        stmt = (
            select(func.count(func.distinct(Top10FloatHolder.symbol)))
            .where(
                and_(
                    Top10FloatHolder.report_period == latest_period,
                    or_(*like_conditions),
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    # ============== 单关键词匹配（plan-01 新增）==============

    async def _count_matched_stocks_single(self, keyword: str, period: Any) -> int:
        """单关键词版本的股数统计（plan-01 §3 #1）。

        与 `_count_matched_stocks` 的差异：
        - 不再调用 `_get_latest_report_period`，period 由调用方传入
          （避免在 preview_match_breakdown 中 N 个关键词 N 次查 MAX）
        - 单关键词，无需 OR 组合

        安全要求：
        - keyword 必须经 `_escape_like_keyword` 转义 % 和 _ 通配符
        - 所有匹配通过参数绑定，不拼接 SQL

        Args:
            keyword: 单关键词（调用方保证已 strip 且非空）
            period: 报告期（调用方保证非 None）

        Returns:
            匹配的去重股票数（int）
        """
        stmt = (
            select(func.count(func.distinct(Top10FloatHolder.symbol)))
            .where(
                and_(
                    Top10FloatHolder.report_period == period,
                    Top10FloatHolder.holder_name.like(
                        f"%{_escape_like_keyword(keyword)}%", escape="\\"
                    ),
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def _get_keyword_matches(self, keyword: str, period: Any) -> list[Any]:
        """单关键词的明细行查询（plan-01 §3 #2 / ADR-3）。

        使用 PostgreSQL `DISTINCT ON (symbol, holder_name)` 配合
        `ORDER BY symbol, holder_name, ann_date DESC NULLS LAST`：
        每个 (symbol, holder_name) 取最新 ann_date 一行，避免历史重复。

        LEFT JOIN stocks 表，stocks 表缺失该 symbol 时 stock_name 为 None
        （由路由层 Pydantic 输出为 null）。

        安全要求：keyword 必须经 `_escape_like_keyword` 转义。

        Args:
            keyword: 单关键词（调用方保证已 strip 且非空）
            period: 报告期（调用方保证非 None）

        Returns:
            list[Row(symbol, stock_name, holder_name)]，按 symbol ASC、
            holder_name ASC 排序
        """
        stmt = (
            select(
                Top10FloatHolder.symbol,
                Stock.name.label("stock_name"),
                Top10FloatHolder.holder_name,
            )
            .select_from(Top10FloatHolder)
            .outerjoin(Stock, Stock.symbol == Top10FloatHolder.symbol)
            .where(
                and_(
                    Top10FloatHolder.report_period == period,
                    Top10FloatHolder.holder_name.like(
                        f"%{_escape_like_keyword(keyword)}%", escape="\\"
                    ),
                )
            )
            # DISTINCT ON 必须配合 ORDER BY 前缀匹配（PG 要求）
            .distinct(
                Top10FloatHolder.symbol,
                Top10FloatHolder.holder_name,
            )
            .order_by(
                Top10FloatHolder.symbol.asc(),
                Top10FloatHolder.holder_name.asc(),
                Top10FloatHolder.ann_date.desc().nullslast(),
            )
        )
        result = await self.session.execute(stmt)
        return result.all()

    # ============== list_groups ==============

    async def list_groups(self) -> list[dict[str, Any]]:
        """查询所有监控组列表（含规则数、关键词、匹配股数）。

        Returns:
            GroupListItem 字典列表（snake_case，由路由层 to_camel 输出）
        """
        groups = await self.repo.get_with_rules()

        # 一次性预查最新报告期，避免循环查询
        latest_period = await self._get_latest_report_period()

        items: list[dict[str, Any]] = []
        for group in groups:
            keywords = [rule.keyword for rule in group.rules]
            matched_stock_count = 0
            if keywords and latest_period is not None:
                matched_stock_count = await self._count_matched_stocks(keywords)

            items.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "sort_order": group.sort_order,
                    "is_system": bool(group.is_system),
                    "rule_count": len(keywords),
                    "matched_stock_count": matched_stock_count,
                    "keywords": keywords,
                }
            )
        return items

    # ============== get_group ==============

    async def get_group(self, group_id: int) -> dict[str, Any]:
        """查询单个监控组详情（含规则数、关键词、匹配股数）。

        与 ``list_groups`` 单项同结构，供详情页 / 编辑页按 id 独立加载。

        Args:
            group_id: 监控组ID

        Returns:
            GroupListItem 字典（snake_case，由路由层 to_camel 输出）

        Raises:
            LookupError: 分组不存在（由 repo.get_by_id_with_rules 抛出）
        """
        group = await self.repo.get_by_id_with_rules(group_id)

        keywords = [rule.keyword for rule in group.rules]
        matched_stock_count = 0
        if keywords:
            matched_stock_count = await self._count_matched_stocks(keywords)

        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "sort_order": group.sort_order,
            "is_system": bool(group.is_system),
            "rule_count": len(keywords),
            "matched_stock_count": matched_stock_count,
            "keywords": keywords,
        }

    # ============== create_group ==============

    async def create_group(
        self,
        name: str,
        description: Optional[str],
        keywords: list[str],
    ) -> dict[str, Any]:
        """创建监控组（含初始关键词）。

        Args:
            name: 组名（唯一）
            description: 描述
            keywords: 初始关键词列表

        Returns:
            新建分组详情（snake_case）

        Raises:
            ValueError: 组名已存在
        """
        existing = await self.repo.get_by_name(name)
        if existing is not None:
            raise ValueError("组名已存在")

        # 计算下一个 sort_order（最大值 + 1，默认从 10 开始避免与预定义冲突）
        max_order_stmt = select(func.max(ShareholderGroup.sort_order))
        max_order_result = await self.session.execute(max_order_stmt)
        max_order = max_order_result.scalar() or 0
        sort_order = max(max_order + 1, 10)

        group = ShareholderGroup(
            name=name,
            description=description,
            sort_order=sort_order,
            is_system=False,
        )
        self.session.add(group)
        await self.session.flush()  # 获取 group.id

        # 插入规则
        clean_keywords = await self.repo.replace_rules(group.id, keywords or [])

        await self.session.commit()
        await self.session.refresh(group)

        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "sort_order": group.sort_order,
            "is_system": bool(group.is_system),
            "rule_count": len(clean_keywords),
            "matched_stock_count": 0,
            "keywords": clean_keywords,
        }

    # ============== update_group ==============

    async def update_group(
        self,
        group_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """更新监控组字段及/或关键词。

        Args:
            group_id: 监控组ID
            name: 新组名（如变更需保证唯一）
            description: 新描述
            keywords: 新关键词列表（如提供则整体替换）

        Returns:
            更新后的分组详情（snake_case）

        Raises:
            LookupError: 分组不存在
            ValueError: 新组名与其他组冲突
        """
        group = await self.repo.get_by_id_with_rules(group_id)

        if name is not None and name != group.name:
            conflict = await self.repo.get_by_name(name)
            if conflict is not None and conflict.id != group.id:
                raise ValueError("组名已存在")
            group.name = name

        if description is not None:
            group.description = description

        if keywords is not None:
            await self.repo.replace_rules(group.id, keywords)

        await self.session.commit()
        # expire_on_commit=False：expunge 让 identity map 失效，确保 get_by_id_with_rules
        # 重新加载最新 rules（否则 selectinload 返回缓存中的旧关键词，响应体陈旧）
        self.session.expunge_all()
        # 重新查询以获取最新规则
        group = await self.repo.get_by_id_with_rules(group_id)

        rule_keywords = [rule.keyword for rule in group.rules]
        matched_stock_count = await self._count_matched_stocks(rule_keywords)

        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "sort_order": group.sort_order,
            "is_system": bool(group.is_system),
            "rule_count": len(rule_keywords),
            "matched_stock_count": matched_stock_count,
            "keywords": rule_keywords,
        }

    # ============== delete_group ==============

    async def delete_group(self, group_id: int) -> None:
        """删除监控组（CASCADE 自动删除关联规则）。

        Args:
            group_id: 监控组ID

        Raises:
            LookupError: 分组不存在
        """
        group = await self.repo.get_by_id_with_rules(group_id)
        await self.session.delete(group)
        await self.session.commit()

    # ============== preview_match ==============

    async def preview_match(
        self,
        keywords: list[str],
        exclude_group_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """预览给定关键词在最新报告期匹配的去重股票数。

        Args:
            keywords: 关键词列表
            exclude_group_id: 预留参数（暂不参与 SQL 过滤）

        Returns:
            {"matched_stock_count": int}
        """
        matched = await self._count_matched_stocks(keywords, exclude_group_id)
        return {"matched_stock_count": matched}

    # ============== preview_match_breakdown（plan-01 新增）==============

    async def preview_match_breakdown(
        self,
        keywords: list[str],
        exclude_group_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """逐关键词查询匹配的去重股票数（AC-01 / AC-07 后端语义）。

        与 `preview_match` 的差异：返回每个关键词单独匹配的股数，
        而非所有关键词合并后的去重总数。

        降级（ADR-5）：单个关键词查询失败不抛错到整体，失败 item 返回
        `matched_stock_count: None`，其他 item 正常。

        安全（架构 §8.3）：
        - 关键词长度超 200 字符直接返回 None（避免超大 pattern 拖垮 DB）
        - 关键词经 `_escape_like_keyword` 转义 % 和 _

        Args:
            keywords: 关键词列表（前端按逗号分隔字符串 split 后传入）
            exclude_group_id: 预留参数（与 `preview_match` 保持一致占位）

        Returns:
            {"items": [{"keyword": str, "matched_stock_count": int | None}, ...]}
            返回字典使用 snake_case（路由层 `_dict_to_camel` 转 camelCase）
        """
        items: list[dict[str, Any]] = []
        period = await self._get_latest_report_period()
        logger.info(
            "preview_match_breakdown called, keywords=%d, period=%s",
            len(keywords),
            period,
        )

        for kw in keywords:
            clean = (kw or "").strip()
            if not clean:
                # 空 kw 不返回 item（前端按索引映射会跳过空行）
                continue
            if len(clean) > 200:
                logger.error(
                    "preview_match_breakdown keyword too long, skip: %s",
                    clean[:50],
                )
                items.append({"keyword": kw, "matched_stock_count": None})
                continue
            if period is None:
                items.append({"keyword": kw, "matched_stock_count": 0})
                continue
            try:
                cnt = await self._count_matched_stocks_single(clean, period)
                items.append({"keyword": kw, "matched_stock_count": cnt})
            except Exception as e:  # noqa: BLE001 — ADR-5 单关键词失败降级
                logger.exception(
                    "preview_match_breakdown single kw failed: %s", e
                )
                items.append({"keyword": kw, "matched_stock_count": None})
        return {"items": items}

    # ============== list_keyword_matches（plan-01 新增）==============

    async def list_keyword_matches(
        self,
        keyword: str,
        page: int,
        page_size: int,
        exclude_group_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """查询单个关键词匹配的明细列表（AC-03 ~ AC-05）。

        全量查询后 Python 层分页（架构 §6.2）；total 用 `len(rows)` 与列表
        行数口径一致（同股票多股东按分行计入）。

        Args:
            keyword: 单关键词（路由层保证已 strip 非空）
            page: 页码（1-based，路由层保证 ≥ 1）
            page_size: 每页条数（路由层保证 1 ≤ page_size ≤ 100）
            exclude_group_id: 预留参数（与 `preview_match_breakdown` 一致占位）

        Returns:
            {
                "items": [{"symbol": str, "stock_name": str | None, "holder_name": str}, ...],
                "total": int,
                "page": int,
                "page_size": int,
            }
            返回字典使用 snake_case（路由层 `_dict_to_camel` 转 camelCase）
        """
        period = await self._get_latest_report_period()
        if period is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        rows = await self._get_keyword_matches(keyword, period)
        total = len(rows)
        offset = (page - 1) * page_size
        page_rows = rows[offset : offset + page_size]
        items = [
            {
                "symbol": r.symbol,
                "stock_name": r.stock_name,
                "holder_name": r.holder_name,
            }
            for r in page_rows
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
