# 开发计划检查报告（Recheck — 修复后复审）

## 一、检查对象

- 架构文档：`docs/07-股东分组匹配明细/07-1-架构文档-股东分组匹配明细.md`（status: done）
- 需求基线：`docs/07-股东分组匹配明细/07-0-需求设计-股东分组匹配明细.md`
- 实现计划：`docs/07-股东分组匹配明细/07-2-实现计划-股东分组匹配明细/`
- 功能数：2（plan-01 后端 + plan-02 前端）
- 上一轮报告：`reviews/dev-plan-check-20260614.md`（5 阻塞 + 4 建议项）

代码级核查范围（recheck 重点）：
- 后端路由链路：`server/main.py:113`、`server/src/api/router.py:29`、`server/src/api/admin/__init__.py:26,37`、`server/src/api/admin/shareholder_groups.py:22,81-98`
- 后端 service：`server/src/services/shareholder_group_service.py`、`server/src/services/shareholder_analysis_service.py`
- 后端测试：`server/tests/test_shareholder_group_admin_api.py`
- 前端 API：`web/src/lib/api.ts:5,8,437,534,539,618-628`
- 前端 E2E 现有 helpers：`web/tests/e2e/helpers/mock-shareholder-api.ts`（实际导出的函数签名）
- 前端 E2E 现有 spec：`web/tests/e2e/shareholder-groups.spec.ts`

## 二、总评

- **结论：通过（有 1 项轻度建议项需修补）**
- 阻塞问题数：**0**（上一轮 5 个全部消除）
- 建议项数：**1**（README 现有快照描述残留旧 helper 名）
- 潜在执行风险（非阻塞）：**1**（mockShareholderGroupPreview 前缀匹配的 LIFO 顺序）

与上一轮对比：5 个阻塞（B-1~B-5）全部修复彻底，无新引入的契约不一致。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✓ | line 2 |
| README frontmatter `org_mode: feature` | ✓ | line 6 |
| README frontmatter `status: review_ready` | ✓ | line 3，合法枚举 |
| README `execution_order: [plan-01, plan-02]` | ✓ | line 14，引用真实 plan |
| README `total_tasks: 2` 与 plan 文件数一致 | ✓ | 2 个 plan-*.md |
| README 必备章节齐全（10 项） | ✓ | line 19-199 |
| 验收标准追踪矩阵表头格式正确 | ✓ | line 74-84，6 列结构 |
| plan-01 frontmatter `feat_id: "plan-01"` 与文件名一致 | ✓ | line 2 |
| plan-02 frontmatter `feat_id: "plan-02"` 与文件名一致 | ✓ | line 2 |
| plan-01/02 `status: ready-to-dev` 合法 | ✓ | 均在合法枚举 |
| plan-01/02 必备 8 章节齐全 | ✓ | 全部齐备 |
| Task 状态全部 `todo` | ✓ | plan-01 9 项 / plan-02 11 项 |
| `depends_on` 引用真实存在功能 | ✓ | plan-01=[]、plan-02=["plan-01"] |

## 四、修复彻底性验证（Recheck 重点）

按上一轮报告 B-1~B-5 标识符全量 grep，确认应改处全改、应留处未误伤：

| 上一轮标识符 | 状态 | 证据 |
| --- | --- | --- |
| `page.goto('/admin/shareholder-groups')`（B-1 路径缺前缀） | ✓ 全改 | plan-02 §3 #9 全部 5 场景统一改用 `ADMIN_GROUPS_PAGE` 常量（现有 spec line 14 已含 `/dashboard` 前缀） |
| `createTestGroup(...)`（B-2 工厂不存在） | ✓ 全改 | plan-02 §3 #9 全部改用 `createSocialGroup()` / `createSocialGroupWithEmptyAndZero()`；唯一残留只在「禁用对照表」(line 424, 426, 677, 825) 作为反例引用 |
| `mockShareholderGroupsSuccess(...)`（B-3 helper 不存在） | ✓ 全改 | plan-02 §3 #9 全部改用 `mockShareholderGroupsList(page, [groups])`（嵌套数组）；plan-02 自身**无残留**。**但 README.md line 58 的现有代码快照描述仍写 `mockShareholderGroupsSuccess`**（见建议项 S-1） |
| `mockPreviewMatchSuccess` / `mockPreviewMatchError`（B-4 helper 不存在） | ✓ 全改 | plan-02 §3 #9 场景 1/2/3 改用 `mockShareholderGroupPreview(page, count)`；场景 4 改用 `mockShareholderGroupsListError(page)`；plan-02 自身无残留 |
| `mockPreviewBreakdownSuccess/Error` / `mockKeywordMatchesSuccess/Error`（B-5 命名冲突） | ✓ 全改 | plan-02 §3 #8 命名规则段（line 412-426）明确禁用 `mockXxxSuccess` 风格；实际新增命名 `mockShareholderGroupPreviewBreakdown` / `mockShareholderGroupPreviewBreakdownError` / `mockShareholderGroupPreviewBreakdownSequence` / `mockShareholderGroupKeywordMatches` / `mockShareholderGroupKeywordMatchesError`，与现有 `mockShareholderGroup*` 系列一致 |
| Task 列表 #2 helper 实现要求 | ✓ 同步更新 | plan-02 §4 Task #2（line 866）从「4 个 mock helper」改为「5 个 mock helper + 2 个测试工厂」，命名与新规则一致 |
| §2 文件清单 helper 列表 | ✓ 同步更新 | plan-02 §2（line 43）helper 列表同步更新为新命名 |

**新引入的不一致排查**：
- grep 全部新 helper 名（`mockShareholderGroupPreviewBreakdown`、`mockShareholderGroupKeywordMatches`、`createSocialGroup`、`createSocialGroupWithEmptyAndZero`）在 plan-02 §3 #8、§3 #9、§2、§4 Task #2 四处出现完全一致，无拼写差异
- README §2.3 line 58 现有快照描述残留 `mockShareholderGroupsSuccess` —— **不属于 plan-02 修复范围，但作为 README 自身的现状描述错误需要修补**（见 S-1）

## 五、维度 17 代码级契约核查（四件套）

### 5.1 路径前缀拼接

**核查方式**：实际打开后端路由链路 + 前端 baseURL

| 层 | 实际代码 | 验证 |
| --- | --- | --- |
| 应用挂载 | `server/main.py:113` `app.include_router(api_router, prefix="/api")` | ✓ |
| v1 router | `server/src/api/router.py:29` `router.include_router(admin_router, prefix="/v1/admin")` | ✓ |
| admin router | `server/src/api/admin/__init__.py:26` `router = APIRouter(tags=["Admin"])`（**无前缀**，依赖子 router） | ✓ |
| 子 router | `server/src/api/admin/shareholder_groups.py:22` `APIRouter(prefix="/shareholder-groups")` | ✓ |
| 最终后端路径 | `/api/v1/admin/shareholder-groups/preview-breakdown` 与 `/api/v1/admin/shareholder-groups/keyword-matches` | ✓ |
| 前端 baseURL | `web/src/lib/api.ts:8` `API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1` | ✓ |
| 前端 AdminApiClient | `web/src/lib/api.ts:437-439` `AdminApiClient extends ApiClient { super(API_BASE_WITH_PREFIX) }` | ✓ |
| 前端 endpoint | plan-02 §3 #1/#2 写 `/admin/shareholder-groups/preview-breakdown` 与 `/admin/shareholder-groups/keyword-matches` | ✓ |
| 拼接结果 | `${API_BASE_URL}/api/v1` + `/admin/shareholder-groups/...` = `${API_BASE_URL}/api/v1/admin/shareholder-groups/...` | **✓ 无重复前缀** |

**结论**：路径前缀代码级核查通过，与架构 §4.2 复用声明、plan-01 §3 #6/#7、plan-02 §3 #1/#2 完全一致。

### 5.2 HTTP 方法存在性与鉴权

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 前端 `adminApiClient.get<T>` 存在 | ✓ | plan-01 §3 #6/#7、plan-02 §3 #1/#2 均用 GET；现有 `previewShareholderGroupMatch`（line 618-627）也用 get |
| 后端 `@router.get("/preview-breakdown")` / `@router.get("/keyword-matches")` | ✓ | plan-01 §3 #6/#7 声明，与架构 §7.3 API 边界一致 |
| 鉴权 `Depends(require_admin)` | ✓ | plan-01 §3 #6/#7 line 270、306；与现有 `preview` 端点 line 88 一致 |
| 三方一致（前端方法 / 后端声明 / 架构描述） | ✓ | GET 方法三方一致 |

**结论**：HTTP 方法与鉴权代码级核查通过。

### 5.3 query 参数命名

| 参数 | 前端写法 | 后端 `Query` | 一致 |
| --- | --- | --- | --- |
| `keywords`（preview-breakdown） | `params['keywords']`（snake，但单字段本身无 underscore，等价 camelCase） | `Query(keywords: str)` | ✓ |
| `exclude_group_id`（preview-breakdown） | `params['exclude_group_id']`（snake） | `Query(exclude_group_id: Optional[int])`（snake） | ✓ |
| `keyword`（keyword-matches） | `query['keyword']` | `Query(keyword: str)` | ✓ |
| `page` | `query['page']` | `Query(page: int)` | ✓ |
| `page_size` | `query['page_size']`（**snake，非 pageSize**） | `Query(page_size: int)`（snake） | ✓ |
| `exclude_group_id`（keyword-matches） | `query['exclude_group_id']`（snake） | `Query(exclude_group_id: Optional[int])`（snake） | ✓ |

**结论**：query 参数命名代码级核查通过。plan-02 §3 #1/#2 显式区分了「query 用 snake_case，response 字段用 camelCase」，与现有 `preview` 端点（line 81-98）的 `Query(exclude_group_id)` 风格一致。MEMORY「dev-plan-check 路径前缀验证」+「query/response 风格区分」均通过。

### 5.4 响应字段命名

| 后端 Pydantic 字段（snake） | `to_camel` 输出（camel） | 前端 TS 类型 | 一致 |
| --- | --- | --- | --- |
| `matched_stock_count: Optional[int]` | `matchedStockCount` | `matchedStockCount: number \| null` | ✓ |
| `stock_name: Optional[str]` | `stockName` | `stockName: string \| null` | ✓ |
| `holder_name: str` | `holderName` | `holderName: string` | ✓ |
| `page_size: int` | `pageSize` | `pageSize: number` | ✓ |
| `total: int` | `total` | `total: number` | ✓ |
| `page: int` | `page` | `page: number` | ✓ |
| `items: List[...]` | `items` | `items: Array<...>` | ✓ |

**结论**：响应字段命名代码级核查通过。所有 Pydantic 模型声明了 `ConfigDict(alias_generator=to_camel, populate_by_name=True)`（plan-01 §3 #5），与现有 `PreviewMatchResponse`（line 62-67）风格一致。

### 5.5 辅助检查

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 响应包裹结构 | ✓ | 外层 `ApiResponse{ success, data, message }`（架构 §7.3）；前端 `AdminApiClient.request` 自动提取 `data`（plan-02 §3 #1 line 84 引用 api.ts:506） |
| 子 router 挂载方式 | ✓ | `shareholder_groups_router` 在 `admin/__init__.py:37` include，与同目录其他子路由（init / tasks / rbac / users 等）写法一致 |
| 路由声明顺序 | ✓ | plan-01 §3 #6 line 260 显式提示「在 `preview` 之后、`GET ""` 列表之前；必须在 `/{group_id}` 之前」；现有 line 78 也有同样注释 |

## 六、复用声明链路验证（维度 16）

| 复用项 | 数据源 | 写入目标 | 前置依赖 | 代码锚点 | 结论 |
| --- | --- | --- | --- | --- | --- |
| `_escape_like_keyword` | `top10_float_holders.holder_name` | 只读 SELECT | 函数已存在 | `shareholder_group_service.py:86-95` | ✓ |
| `_get_latest_report_period` | `top10_float_holders.report_period` | 只读 SELECT | 函数已存在 | `shareholder_group_service.py:107-111` | ✓ |
| `_count_matched_stocks`（OR 多关键词版） | `top10_float_holders` | 只读 SELECT | 函数已存在；本期不动 | `shareholder_group_service.py:113-154` | ✓ |
| `Stock` 模型 JOIN 模式 | `stocks.symbol` / `stocks.name` | 只读 SELECT | JOIN 模式已有先例 | `shareholder_analysis_service.py:292-344` | ✓ |

**结论**：4 处复用声明均经四要素（数据源/写入目标/前置依赖/代码锚点）验证可行，import 路径、函数签名、JOIN 方式都与现有代码一致。无 MEMORY 典型风险（entity_type 不匹配、依赖表为空、未实现的客户端方法）。

## 七、验收标准追踪（9 条 AC）

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 每个非空关键词展示单独匹配的去重股票数 | ✓ line 76 | plan-01 §3 #6 + §5 pytest；plan-02 §3 #1+#4+#6+#8 + §5 场景 1 | ✓ |
| AC-02 | 保留所有关键词合并匹配总数 | ✓ line 77 | plan-02 §3 #4「保留现有调 previewShareholderGroupMatch」+ §5 场景 1 | ✓ |
| AC-03 | 点击「查看明细」展示该关键词的明细列表 | ✓ line 78 | plan-01 §3 #7 + §5 pytest；plan-02 §3 #5+#7+#9 + §5 场景 2 | ✓ |
| AC-04 | 同一股票被多个匹配股东持有时按股东分行 | ✓ line 79 | plan-01 §3 #2 SQL `DISTINCT ON (symbol, holder_name)` + §5 用例 4；plan-02 §5 场景 2 | ✓ |
| AC-05 | 明细按股票代码升序 | ✓ line 80 | plan-01 §3 #2 SQL `ORDER BY symbol, holder_name, ann_date DESC NULLS LAST` + §5 用例 5；plan-02 §5 场景 2 | ✓ |
| AC-06 | 修改关键词后股数与明细实时刷新 | ✓ line 81 | plan-02 §3 #4 debounce + §5 场景 3（用 sequence mock） | ✓ |
| AC-07 | 失败降级不阻塞编辑保存 | ✓ line 82 | plan-01 §3 #3 try/except + §5 用例 8；plan-02 §3 #4+#5+#9 + §5 场景 4 | ✓ |
| AC-08 | 空关键词不显示股数与明细入口 | ✓ line 83 | plan-02 §3 #4 `validKeywords` 过滤 + §3 #6「仅当 trimmed 非空时显示」+ §5 场景 5 | ✓ |
| AC-09 | 关键词匹配数为 0 时按钮置灰 | ✓ line 84 | plan-02 §3 #6 `disabled={countItem?.matchedStockCount === 0}` + §5 场景 5 | ✓ |

**结论**：9 条 AC 全部映射到 plan-01/plan-02，每条都有具体验证方式（pytest 用例号或 Playwright 场景号）。

## 八、维度检查结果（汇总）

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✓ | 0 | Keyword→Match→Detail 闭环在 plan-01/02 完整落地 |
| 2. 范围与非目标 | ✓ | 0 | P0 全部承接；非目标（行级入口 / 质量评分 / 导出 / 用户侧改造）在两个 plan §1.6 不在范围呼应 |
| 3. 成功标准 | ✓ | 0 | 性能目标 ≤ 200ms / ≤ 1s 在 plan-01 §5 性能验收 + plan-02 §5 隐含验证 |
| 4. 验收标准防漂移 | ✓ | 0 | 9 条 AC 全部映射；E2E-TDD red/green 两阶段证据要求明确 |
| 5. ADR 约束 | ✓ | 0 | ADR-1~5 全部在 plan-01 §3 / plan-02 §3 体现；护栏（不引入缓存、不抽象引擎、不修改 preview 端点）在两 plan §1.6 不在范围呼应 |
| 6. 用户流程与状态机 | ✓ | 0 | 架构 §3.3 单关键词行状态机在 plan-02 §3 #6 渲染分支 + §8 边界场景表完整呈现 |
| 7. 模块职责与系统上下文 | ✓ | 0 | 模块地图对齐；上下游 depends_on 体现 |
| 8. 运行链路 | ✓ | 0 | 链路 6.1~6.4 在 plan-01 §3 #3/#4 + plan-02 §3 #4/#5/#9 分步落地 |
| 9. 数据模型与契约 | ✓ | 0 | Pydantic 模型 + TS interface 完整；序列化转换（snake→camel）显式声明；响应包裹结构对齐 |
| 10. 非功能需求 | ✓ | 0 | 性能/降级/安全/可观测性全部落到 plan-01 §5 + §8；前端降级链落到 plan-02 §8 |
| 11. 实施建议与技术选型 | ✓ | 0 | FastAPI + SQLAlchemy + Next.js + Playwright 与架构一致；阶段划分 plan-01 → plan-02 符合依赖 |
| 12. 风险与未决策项 | ✓ | 0 | open_questions 为空；架构 §8.6 风险全部在两 plan §8 边界场景表有缓解 |
| 13. 功能拆分质量 | ✓ | 0 | plan-01 后端 9 task + plan-02 前端 11 task；依赖 DAG 无循环；mixed 接口在 plan-01 §3 #6/#7 与 plan-02 §3 #1/#2 对齐 |
| 14. 可执行性 | ✓ | 0 | 文件路径具体；modify 文件真实存在；E2E red→green 顺序可执行；前置条件可验证；契约四件套全部通过代码级核对 |
| 15. 状态与报告契约 | ✓ | 0 | README/FEAT frontmatter 状态合法；展示状态一致；本报告已写入 `reviews/dev-plan-check-{date}-recheck.md` |
| 16. 复用声明链路验证 | ✓ | 0 | 4 处复用全部补全调用细节，与现有代码锚点一致 |
| 17. 前后端 API 契约一致性（代码级） | ✓ | 0 | 四件套全部通过；辅助检查（响应包裹、路由挂载方式、声明顺序）通过 |

## 九、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 建议项 S-1 | `README.md` line 58 | 现有代码快照描述写「`mockShareholderGroupsSuccess` 等 helper」，但实际现有 helper 叫 `mockShareholderGroupsList`（嵌套数组）。这是上一轮 B-3 问题在 README 镜像没改 | 改为「`mockShareholderGroupsList` 等 helper」 |
| 潜在风险 R-1（非阻塞） | `plan-02 §3 #8` | 现有 `mockShareholderGroupPreview`（line 293-314）用 `matchApiPathPrefix(url, '/api/v1/admin/shareholder-groups/preview')` 前缀匹配，会同时捕获 `/preview-breakdown` 路径。新 helper `mockShareholderGroupPreviewBreakdown` 用 `matchApiPath` 精确匹配 + fallback 转交。依赖 Playwright route LIFO 顺序 + 精确匹配 helper 的 fallback 规则。若 implementer 误把 `mockShareholderGroupPreview` 注册在 `mockShareholderGroupPreviewBreakdown` 之后，前缀匹配会先捕获 `/preview-breakdown`，导致新 helper 永远不被调用，场景 1/2/3 失败 | 在 §3 #8 补一句「注册顺序：先注册前缀匹配的 `mockShareholderGroupPreview`，再注册精确匹配的 `mockShareholderGroupPreviewBreakdown`（依赖 LIFO）」（implementer 可参照现有 helper 顶部注释 line 22-29 的 LIFO 说明，但 plan 内显式提示更稳） |

**无阻塞问题。**

## 十、合理扩展（沿用上一轮报告）

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-01 §3 #8 | 13 个 pytest 用例（含 SQL 注入回归） | 覆盖核心 AC + 边界 + 安全回归；超出最小 6 个但每个用例独立有价值 |
| plan-01 §3 #1 | `_count_matched_stocks_single` 不查 MAX，period 由调用方传入 | 避免 N 关键词 N 次查 MAX；性能优化，符合架构 §8.1 性能目标 |
| plan-01 §3 #2 | SQLAlchemy `.distinct(*cols)` + 备选子查询 | PostgreSQL DISTINCT ON 在不同 SQLAlchemy 版本支持度不同；给出 fallback |
| plan-02 §3 #4 | debounce 回调并行调 preview + preview-breakdown | AC-02（合并预览）与 AC-01（逐关键词）并存展示，复用同一 debounce 节奏 |
| plan-02 §3 #6 | 关键词行按索引映射（非字符串值） | 草稿中可能有重复关键词，按索引映射避免错乱 |
| plan-02 §3 #6 | 「X 只」标签 + 「查看明细」按钮的稳定选择器（data-testid） | 遵循 .claude/rules/e2e-playwright-best-practices.md 规则 5/7，避免文案变更导致 spec 脆弱 |
| plan-01 §3 #6/#7 + plan-02 §3 #1/#2 | 「前后端契约校验四件套」显式列出 | 让 implementer 在写代码时即对照四件套，避免事后契约漂移 |

## 十一、建议补丁计划

按优先级列出应修改的位置：

1. **[建议项]** `README.md` line 58：将「`mockShareholderGroupsSuccess`」改为「`mockShareholderGroupsList`」（现状描述与现有 helper 真实命名对齐）
2. **[非阻塞，可选]** `plan-02 §3 #8`：在「注册顺序」段落补一句 LIFO 提示（虽然现有 helper 顶部注释已说明，但 plan 内显式提示更稳）

补丁完成后可推进 plan-01/plan-02 进入 `auto-dev` 流程（red → implement → green → task-review）。

## 十二、整体评价

**✅ 通过，可进入开发执行阶段。**

修复彻底性：上一轮 5 个阻塞全部消除，无新引入契约不一致。
代码级契约：路径前缀、HTTP 方法、query 参数、响应字段四件套全部通过代码级核对。
复用声明：4 处复用全部经四要素验证可行。
AC 追踪：9 条 AC 全部映射到 plan-01/plan-02，每条都有具体验证方式。
仅 1 项轻度建议项（README line 58 现状描述残留旧 helper 名），不影响开发启动。

下一步可推进 `auto-dev` 从 plan-01 开始 red → implement → green → task-review 循环。
