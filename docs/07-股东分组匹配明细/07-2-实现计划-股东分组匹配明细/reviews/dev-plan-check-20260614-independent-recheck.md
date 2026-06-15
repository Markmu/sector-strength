# 开发计划检查报告（第三轮 · 独立上下文复审）

## 一、检查对象

- 架构文档：`docs/07-股东分组匹配明细/07-1-架构文档-股东分组匹配明细.md`（status: done）
- 需求文档：`docs/07-股东分组匹配明细/07-0-需求设计-股东分组匹配明细.md`
- 实现计划：`docs/07-股东分组匹配明细/07-2-实现计划-股东分组匹配明细/`
  - `README.md`（status: review_ready）
  - `plan-01-后端逐关键词股数与明细查询API.md`（status: ready-to-dev）
  - `plan-02-前端编辑弹窗逐关键词股数与明细下钻.md`（status: ready-to-dev）
- 功能数：2
- 本轮检查方式：独立上下文（不复用前两轮报告的视角），从代码与文档出发做完整 17 维度核查

## 二、总评

- **结论：需要修改**（1 个 blocker）
- 阻塞问题数：1
- 建议项数：0
- 潜在风险：0

**本轮 2 项修复彻底性核查结论**：
- ✅ **S-1 修复彻底**：`README.md` line 58 已改为 `mockShareholderGroupsList`，全 docs 树（除 reviews 目录中的历史报告原文摘抄）无 `mockShareholderGroupsSuccess` 残留。
- ⚠️ **R-1 修复"加提示"到位，但 §3 #9 场景代码未同步修改**：plan-02 §3 #8 line 644 加的 LIFO 注册顺序提示（先 `mockShareholderGroupPreview` 再 `mockShareholderGroupPreviewBreakdown`）逻辑正确，但 §3 #9 场景 1（line 686-691）的实际代码违反了这条提示（顺序颠倒）—— 详见 B-1。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ | line 2 |
| README frontmatter `org_mode: feature` | ✅ | line 6 |
| README `status: review_ready` 合法 | ✅ | line 3 |
| `execution_order: [plan-01, plan-02]` 引用真实 plan | ✅ | line 14 |
| `total_tasks: 2` 与 `plan-*.md` 数量一致 | ✅ | line 9 |
| README 必备章节齐全（`feature_readme_required_sections`） | ✅ | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 全部存在 |
| 验收标准追踪矩阵表头固定 | ✅ | `AC-ID | 需求原文 | 架构承接 | 计划承接 | 验证方式 | 当前状态` |
| plan-01 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-01` |
| plan-02 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-02` |
| plan-01/02 frontmatter `status: ready-to-dev` 合法 | ✅ | 在 `task_file_status` 枚举内 |
| plan-01/02 必备章节齐全（`feature_task_required_sections`） | ✅ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 全部存在 |
| Task 列表 status 全为 `todo` | ✅ | 无非法状态 |
| `depends_on` 引用真实 plan | ✅ | plan-02 depends_on: ["plan-01"] |
| 边界场景表 status 全为 `todo` | ✅ | 无 `waived` 需原因的情况 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 每个非空关键词展示单独匹配的去重股票数 | plan-01, plan-02（§3 表 line 76） | plan-01 §3 #8 用例 1 / §5；plan-02 §3 #9 场景 1 | ✅ |
| AC-02 | 保留所有关键词合并匹配总数 | plan-02（§3 表 line 77） | plan-01 §3 #8 用例 12（回归）/ §5；plan-02 §3 #9 场景 1 | ✅ |
| AC-03 | 点击「查看明细」展示该关键词的明细列表 | plan-01, plan-02（§3 表 line 78） | plan-01 §3 #8 用例 3, 6 / §5；plan-02 §3 #9 场景 2 | ✅ |
| AC-04 | 同一股票被多个匹配股东持有时按股东分行展示 | plan-01, plan-02（§3 表 line 79） | plan-01 §3 #8 用例 4 / §5；plan-02 §3 #9 场景 2 | ✅ |
| AC-05 | 明细按股票代码升序，同股票多股东相邻 | plan-01, plan-02（§3 表 line 80） | plan-01 §3 #8 用例 5 / §5；plan-02 §3 #9 场景 2 | ✅ |
| AC-06 | 修改关键词后股数与明细实时刷新 | plan-02（§3 表 line 81） | plan-02 §3 #9 场景 3 | ✅ |
| AC-07 | 预览或明细查询失败均降级且不阻塞编辑与保存 | plan-01, plan-02（§3 表 line 82） | plan-01 §3 #8 用例 8 / §5；plan-02 §3 #9 场景 4 | ✅ |
| AC-08 | 空关键词不显示股数与明细入口 | plan-02（§3 表 line 83） | plan-02 §3 #9 场景 5 | ✅ |
| AC-09 | 关键词匹配数为 0 时查看明细入口置灰 | plan-02（§3 表 line 84） | plan-02 §3 #9 场景 5 | ✅ |

**结论**：9 条 AC 全部映射到 README 矩阵 + 至少一个 plan，无漂移、无弱化。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ | 0 | README §2.1 复述架构 §1 的 Keyword→Match→Detail 闭环 |
| 2 范围与非目标 | ✅ | 0 | plan-01/02 不在范围与架构 §2.2 完全对齐 |
| 3 成功标准 | ✅ | 0 | plan-01 §5 性能验收 + plan-02 §5 Playwright 全覆盖 |
| 4 验收标准防漂移 | ✅ | 0 | 9 条 AC 全部映射，E2E-TDD red/green 双阶段证据要求齐全 |
| 5 ADR 约束 | ✅ | 0 | ADR-1~5 全部在 README §2.2 护栏 + plan 实现规格呼应 |
| 6 用户流程与状态机 | ✅ | 0 | plan-02 §3 #3/#5 状态机与架构 §3.3 一致 |
| 7 模块职责与系统上下文 | ✅ | 0 | README §4 模块地图与架构 §4.2 一一对应 |
| 8 运行链路 | ✅ | 0 | 架构 §6.1-6.4 在 plan-01 §3 #3/#4 + plan-02 §3 #4/#5 落地 |
| 9 数据模型与契约 | ✅ | 0 | Pydantic 模型 4 个 + TS interface 与架构 §7.2/§7.3 一致 |
| 10 非功能需求 | ✅ | 0 | 性能/安全/降级/可观测性全部映射 |
| 11 实施建议与技术选型 | ✅ | 0 | FastAPI + SQLAlchemy + Next.js + Playwright 与架构一致 |
| 12 风险与未决策项 | ✅ | 0 | README §8 无开放问题，与架构 §5.6 一致 |
| 13 功能拆分质量 | ✅ | 0 | 2 个 FEAT（backend / frontend）依赖 DAG 无循环 |
| 14 可执行性 | ✅ | 0 | 文件清单具体到行号，验证命令可运行 |
| 15 状态与报告契约 | ✅ | 0 | frontmatter 状态合法 |
| 16 复用声明链路验证 | ✅ | 0 | 见维度 16 详述 |
| 17 前后端 API 契约一致性（代码级） | ⚠️ | 1 | 见维度 17 详述：B-1 场景 1 mock 注册顺序违反 R-1 LIFO 提示 |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| **B-1**（blocker） | `plan-02-...md` §3 #9 场景 1（line 686-691） | **场景 1 mock 注册顺序违反 §3 #8 line 644 加的 LIFO 提示**。<br><br>**链路分析**：现有 `mockShareholderGroupPreview`（`web/tests/e2e/helpers/mock-shareholder-api.ts:293-314`）使用 `matchApiPathPrefix(url, '/api/v1/admin/shareholder-groups/preview')` —— **前缀匹配**，会捕获 `/preview`、`/preview-breakdown`、`/preview-anything` 等所有以 `/preview` 开头的 pathname。<br><br>**plan-02 §3 #9 场景 1 的实际代码**（line 686-691）：<br>```ts<br>await mockShareholderGroupsList(page, [group])<br>await mockShareholderGroupPreviewBreakdown(page, [...])  // 先注册（精确匹配）<br>await mockShareholderGroupPreview(page, 3)               // 后注册（前缀匹配）<br>```<br><br>**问题**：Playwright `page.route` 是 LIFO（后注册的先执行）。此顺序下，发往 `/api/v1/admin/shareholder-groups/preview-breakdown` 的请求会先命中后注册的 `mockShareholderGroupPreview`（前缀匹配），返回 `{ success: true, data: { matchedStockCount: 3 } }`，**完全绕过精确匹配的 `mockShareholderGroupPreviewBreakdown`**。前端组件拿不到 `items` 数组，perKeywordCounts 始终为空 → 场景 1 的断言「关键词行有 X 只标签」必然失败。<br><br>**为什么是本轮新发现而非前两轮已知**：R-1 在 §3 #8 加的 LIFO 提示要求"先 Preview 后 PreviewBreakdown"，但 §3 #9 场景 1 的代码示例没按提示修。前两轮没把"提示与代码示例同步"作为阻塞项核查。 | 把场景 1 的两行调换顺序：<br>```ts<br>await mockShareholderGroupsList(page, [group])<br>await mockShareholderGroupPreview(page, 3)               // 先注册（前缀匹配）<br>await mockShareholderGroupPreviewBreakdown(page, [...])  // 后注册（精确匹配）—— LIFO 优先生效<br>```<br><br>**验证方法**：在场景 1 注释里加一句「**注册顺序遵循 §3 #8 LIFO 规则**：先 Preview（前缀匹配），后 PreviewBreakdown（精确匹配），让精确匹配在 LIFO 中先捕获 `/preview-breakdown`」。<br><br>**场景 2/3/5 不受影响**：它们只注册 preview-breakdown（无 Preview），无 LIFO 冲突；场景 4 注册的是 PreviewBreakdownError（精确匹配），无 Preview，也无冲突。<br><br>**根本原因**：架构 §4.2 系统上下文把 `preview-breakdown` 和 `preview` 列为并存端点，没考虑现有 mock helper 用前缀匹配会导致 URL 命中冲突；plan-02 §3 #8 line 644 的 LIFO 提示是正确的修复方向，但 §3 #9 场景代码未同步落地。 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-01 §3 #2 line 119-125 | SQLAlchemy `.distinct(*cols)` 不可用时的子查询备选方案 | 架构 §6.2 SQL 语义的实现技术风险预案，符合 brownfield 项目"优先尝试主方案，失败再切换" |
| plan-01 §3 #2 line 82 | 「若文件未 import 需新增 `from src.models import Stock`」注释 | 验证后 shareholder_group_service.py:17-18 当前确实未 import Stock，注释是必要的代码定位提示 |
| plan-02 §3 #8 line 426 | 测试数据工厂 `createSocialGroupWithEmptyAndZero()`（无参，跟随 `createQFiiGroup` 风格） | 与现有 helper 系列命名一致，比 `createTestGroup(partial)` 风格更贴合现有约定 |
| plan-02 §3 #8 line 464 | `mockShareholderGroupPreviewBreakdownSequence` helper（callIndex 模式） | 复用现有 `mockShareholderGroupsList:147-168` 模式，符合现有 spec 风格 |

## 八、维度 16/17 详细说明

### 维度 16：复用声明链路验证

| 复用声明 | 来源 | 代码核查结论 |
| --- | --- | --- |
| `_escape_like_keyword` 模块级私有函数（line 86-95） | plan-01 §3 #1 | ✅ shareholder_group_service.py:86-95 实际位置一致，签名 `def _escape_like_keyword(keyword: str) -> str` |
| `_get_latest_report_period`（line 107-111） | plan-01 §3 #3/#4 | ✅ shareholder_group_service.py:107-111 一致 |
| `_count_matched_stocks` 现有 OR 多关键词版（line 113-154） | plan-01 §3 #1 | ✅ shareholder_group_service.py:113-154 一致，且明确不动 |
| `func.count / func.distinct / select / and_` 已在文件顶部 import | plan-01 §3 #1 | ✅ shareholder_group_service.py:13 `from sqlalchemy import and_, func, or_, select` |
| `Top10FloatHolder` 已在文件顶部 import | plan-01 §3 #1 | ✅ shareholder_group_service.py:18 |
| `Stock` 模型需新增 import | plan-01 §3 #2 | ✅ 验证 server/src/models/stock.py:7 `class Stock(Base)`，且 shareholder_group_service.py 顶部未 import Stock —— 注释合理 |
| `require_admin` + `get_session` + `ApiResponse` 依赖 | plan-01 §3 #6/#7 | ✅ shareholder_groups.py:15-16 实际 import，与现有 `preview` 端点（line 87-88）签名风格一致 |
| `_dict_to_camel` helper（line 70-72） | plan-01 §3 #6 | ✅ shareholder_groups.py:70-72 一致 |
| 现有 `previewShareholderGroupMatch` 端点拼接风格（URLSearchParams） | plan-02 §3 #1 | ✅ api.ts:618-627 完全一致 |
| `AdminApiClient.request` 自动提取 `response.data`（line 506） | plan-02 §3 #1 | ✅ api.ts:506 一致 |
| `adminApiClient` 单例（line 534） | plan-02 §3 #1 | ✅ api.ts:534 一致 |
| 后端路由前缀链路：`main.py /api` × `router.py /v1/admin` × `shareholder_groups.py /shareholder-groups` | plan-01 §3 #6/#7 + plan-02 §3 #1/#2 | ✅ main.py:113 + router.py:29 + admin/__init__.py:37 + shareholder_groups.py:22 完整链路一致 |
| 前端 baseURL `${API_BASE_URL}/api/v1` | plan-02 §3 #1/#2 | ✅ api.ts:8 `API_BASE_WITH_PREFIX` 一致 |

**结论**：所有复用声明经代码级核对，**全部成立**。

### 维度 17：前后端 API 契约一致性（代码级四件套）

| 端点 | 路径前缀 | HTTP 方法 | query 参数 | response 字段 | 结论 |
| --- | --- | --- | --- | --- | --- |
| GET `/admin/shareholder-groups/preview-breakdown` | ✅ 前端 endpoint `/admin/shareholder-groups/preview-breakdown` × baseURL `/api/v1` = 后端 `/api/v1/admin/shareholder-groups/preview-breakdown`（无重复前缀） | ✅ 前端 `adminApiClient.get` ↔ 后端 `@router.get` | ✅ `keywords`（逗号分隔）+ `exclude_group_id`（snake_case，前端 plan-02 §3 #1 line 68 与后端 plan-01 §3 #6 line 266-268 完全一致） | ✅ `data.items[].keyword/matchedStockCount`（camelCase，Pydantic alias 转换；前端类型定义 line 73 一致） | ✅ |
| GET `/admin/shareholder-groups/keyword-matches` | ✅ 同上无重复前缀 | ✅ 前端 `adminApiClient.get` ↔ 后端 `@router.get` | ✅ `keyword` + `page` + `page_size`（snake_case）+ `exclude_group_id`（snake_case）—— plan-02 §3 #2 line 99/100 显式注释「query 参数不经 alias 转换」+ plan-01 §3 #7 line 301-304 后端 `Query(page_size: int)` snake_case 完全一致 | ✅ `data.items[].symbol/stockName/holderName` + `data.total/page/pageSize`（camelCase）—— plan-01 §3 #5 line 244-252 Pydantic 模型 + plan-02 §3 #2 line 102-108 TS interface 一致 | ✅ |

**辅助检查**：
- ✅ **响应包裹结构**：所有 admin 端点统一 `ApiResponse{ success, data, message }`，`AdminApiClient.request` 自动提取 `data`（api.ts:506），plan-02 §3 #1 line 84 显式注释「组件消费时 `res.data` 即 `T` 本身」
- ✅ **路由声明位置**：plan-01 §3 #6 明确要求 preview-breakdown 端点声明在 `/{group_id}` 动态路径之前，与现有 `preview` 端点位置约定一致（shareholder_groups.py:78 注释）
- ⚠️ **mock 命中冲突**：见 B-1（场景 1 mock 注册顺序问题）

**结论**：四件套契约（路径/方法/query/response）**全部通过代码级核对**；唯 1 项辅助检查（mock LIFO 命中冲突）阻塞，详见 B-1。

## 八、建议补丁计划

按优先级列出应修改的章节：

1. **[blocker]** `plan-02-...md` §3 #9 场景 1（line 686-691）：把 `mockShareholderGroupPreviewBreakdown` 和 `mockShareholderGroupPreview` 两行的注册顺序调换，让 LIFO 让精确匹配的 helper 优先命中。同时在场景 1 加一句注释引用 §3 #8 LIFO 规则。

修补后无需重新做完整 dev-plan-check，单点 patch 即可。
