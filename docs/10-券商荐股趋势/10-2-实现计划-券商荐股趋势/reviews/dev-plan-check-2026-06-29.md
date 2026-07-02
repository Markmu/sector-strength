# 开发计划检查报告（复审）

## 一、检查对象

| 项 | 内容 |
|---|---|
| 架构文档（基准） | `docs/10-券商荐股趋势/10-1-架构文档-券商荐股趋势.md`（status: done，arch-check 100% 通过） |
| 实现计划目录（被检） | `docs/10-券商荐股趋势/10-2-实现计划-券商荐股趋势/` |
| README | `README.md`（frontmatter status: review_ready） |
| FEAT 文件 | `plan-01-后端趋势聚合与API.md`（backend，status: draft，无依赖）；`plan-02-前端推荐趋势视图.md`（frontend，status: draft，depends_on plan-01） |
| 功能数 | 2（plan-01 后端趋势聚合与 API / plan-02 前端推荐趋势视图） |
| 复审轮次 | 第 2 轮（recheck）—— 上一轮（首轮）17 维度全绿，仅 3 条建议项（S-1/S-2/S-3） |
| 代码级核对范围 | 前端 `BrokerRecommendPage.tsx` L150-198（hasNoData 分支 vs 非空 return 的 ViewSwitcher 渲染位置） |

## 二、总评

- **结论：通过**
- 阻塞问题数：**0**
- 建议项数：**0**（首轮 3 条均已彻底修复）
- **修复彻底性**：
  - **S-1（AC 标签）：彻底修复**。该改处（搜索条目 + 趋势聚合验收标题）已由 AC-11 改为 AC-09；该留处（单月 AC-11）未误伤；frontmatter 与 README 追踪矩阵三方一致，无漂移。
  - **S-2（空状态措辞）：彻底修复**。3 处描述（§验收 AC-12、§验收降级回归、§前端边界场景表）均已改为"09 hasNoData 分支仅渲染标题+空状态块、不渲染视图切换器"，与 09 真实代码（L156-178）一致。
  - **S-3（Sparkline testId）：彻底修复**。§3 组件已加可选 `testId` prop 并在两处渲染点透传 `data-testid={testId}`，§4 规范仍为 `broker-trend-sparkline-{symbol}`，调用方约定（§3 末尾 + §4）一致；无残留静态无后缀 testid。

## 三、修复彻底性验证（recheck 重点）

### S-1：AC 标签（搜索 AC-09 / 单月 AC-11）

**grep 结果（plan-01 全量）**：

| 位置 | 行号 | 内容 | 判定 |
|---|---|---|---|
| frontmatter 关联验收标准 | L17 | `[AC-02, AC-03, AC-04, AC-06, AC-07, AC-08, AC-09, AC-11, AC-12]` | ✅ AC-09、AC-11 均在，未因修复丢失 |
| §验收标题「趋势聚合验收」 | L143 | `### 趋势聚合验收（AC-02/03/04/07/09）` | ✅ **该改处已改**（由 11→09） |
| §验收搜索条目 | L149 | `- [ ] AC-09 search 服务端全量重查…` | ✅ **该改处已改**（由 AC-11→AC-09） |
| §验收标题「降级验收」 | L155 | `### 降级验收（AC-11/12）` | ✅ **该留处未误伤**（AC-11=单月，正确保留） |
| §验收单月条目 | L157 | `- [ ] AC-11（单月）仅一个已同步月份时…` | ✅ **该留处未误伤**（单月=AC-11，正确） |
| 后端边界场景表 | L218 | `仅一个已同步月份 …（AC-11）` | ✅ 该留处未误伤（单月=AC-11） |
| 后端边界场景表 | L221 | `搜索无匹配 \| items=[] + total=0（AC-09/11）` | ⚠️ 见四节（首轮已存在、非本修复引入） |

**README 追踪矩阵一致性**：
- AC-09（L80）→ 计划承接 `plan-01, plan-02`，验证 `plan-01 §5 搜索验收 + plan-02 §5 搜索 E2E` ✅ 未漂移
- AC-11（L82）→ 计划承接 `plan-01, plan-02`，验证 `plan-01 §5 单月验收 + plan-02 §5 单月降级 E2E` ✅ 未漂移

**结论**：S-1 彻底修复。该改处（标题 L143 + 搜索条目 L149）已改；该留处（降级验收 L155/L157 单月 AC-11、边界表 L218 单月 AC-11）均正确保留未被误伤；frontmatter（L17）与 README 矩阵（L80/L82）三方 AC 集合一致，无因改标签导致的集合漂移。

### S-2：空状态措辞

**3 处声称修复位置逐一核对（plan-02）**：

| 位置 | 行号 | 修复后内容 | 与 09 代码一致性 |
|---|---|---|---|
| §验收 AC-12 | L242 | `…（复用 09，09 hasNoData 分支仅渲染标题+空状态块，不渲染视图切换器，趋势视图同样不展示）` | ✅ |
| §验收降级回归 | L267 | `整页空状态（mock hasData=false）：09 hasNoData 分支仅渲染标题+空状态块、不渲染视图切换器，趋势视图同样不展示、不发趋势请求` | ✅ |
| §前端边界场景表（注：plan-02 为前端边界表，非后端） | L323 | `复用 09 整页空状态（hasNoData）：09 hasNoData 分支仅渲染标题+空状态块、不渲染视图切换器…（AC-12）` | ✅ |

**09 真实代码核对（`BrokerRecommendPage.tsx` L150-198）**：
- `if (hasNoData)` 分支（L156-178）：`return` 一个仅含 `<header>`（标题"券商每月荐股"+ 副标题）+ `<div data-testid="broker-empty-state">`（空状态卡片"暂无券商金股数据…请联系管理员同步"）的片段。**不渲染 ViewSwitcher / MonthSelector / 板块筛选**。
- ViewSwitcher 实际渲染位置：在 `hasNoData` 分支之后的非空 `return`（L180+）中，位于 L196 `<ViewSwitcher value={view} onChange={handleViewChange} />`，与 MonthSelector 同处 header 右侧（L190-197）。

**结论**：S-2 彻底修复。3 处描述均已修正为"仅渲染标题+空状态块、不渲染视图切换器"，与 09 代码 L156-178（hasNoData 分支无 ViewSwitcher，ViewSwitcher 在 L196 非空 return）完全一致。原"视图切换器仍可见但不发请求"的错误措辞已被全部清除，无残留。

### S-3：Sparkline testId

**§3 组件 vs §4 规范一致性（plan-02）**：

| 位置 | 行号 | 内容 | 判定 |
|---|---|---|---|
| §3 SparklineProps | L130 | `testId?: string  // 由调用方传入（如 broker-trend-sparkline-${symbol}）` | ✅ 新增可选 prop |
| §3 组件函数签名 | L133 | `Sparkline({ values, width=80, height=24, color='currentColor', testId })` | ✅ 解构 testId |
| §3 空序列渲染点 | L135 | `return <div … data-testid={testId} />` | ✅ 透传（动态） |
| §3 svg 渲染点 | L147 | `<svg … data-testid={testId}>` | ✅ 透传（动态） |
| §3 调用方约定 | L155 | `调用方（BrokerTrendRanking 表格行）渲染时传 testId={`broker-trend-sparkline-${item.symbol}`}` | ✅ 与 §4 命名一致 |
| §4 data-testid 规范 | L166 | `… / broker-trend-sparkline-{symbol}（折线图，便于 E2E 定位）` | ✅ 规范未变（带 symbol 后缀） |

**残留静态 testid 核查**：grep `data-testid="broker-trend-sparkline"`（无后缀）在 plan-02 全文 → **无匹配**（0 残留）。原静态写法已清除。

**结论**：S-3 彻底修复。§3 组件现已通过可选 `testId` prop 动态接收 testid，§4 规范仍为 `broker-trend-sparkline-{symbol}`，两处命名一致；§3 内部两个渲染点（空 div / svg）均正确透传 `data-testid={testId}`；无残留静态无后缀 testid。

## 四、新不一致排查

逐项排查修复是否引入新的契约/文档不一致：

1. **S-1 改 AC 标签 → checklist / README 矩阵 / frontmatter AC 集合一致性**：无新不一致。plan-01 frontmatter（L17，含 AC-09 与 AC-11）、README 矩阵（AC-09→plan-01/02、AC-11→plan-01/02）、plan-01 §验收（搜索归 AC-09、单月归 AC-11）三方集合一致。改标签未导致任何 AC 在矩阵中"失承接"或"双承接"。

2. **S-3 加 testId prop → §4 调用描述对齐**：无新不一致。Sparkline 唯一调用方为 BrokerTrendRanking（§4 行渲染），§3 末尾（L155）已显式约定该调用方传 `broker-trend-sparkline-${item.symbol}`。无遗漏调用点（全仓 grep `Sparkline` 在 plan-02 内仅 BrokerTrendRanking 一处消费）。

3. **跨文档契约影响**：S-3 的 `testId` 为前端组件内部 prop，不进入 API 请求/响应字段，维度 9（数据模型与契约）无影响。

**首轮已存在、非本修复引入的观察（不构成新问题，仅记录备查）**：
- plan-01 后端边界场景表 L221「搜索无匹配 | items=[] + total=0（AC-09/11）」将"搜索无匹配"同时挂 AC-09 与 AC-11。AC-11 语义为"仅单月数据可用"（仍返回 items），与"搜索无匹配（items=[]）"无直接因果。此为首轮已存在的标签松耦合，**非 S-1 修复范围（S-1 仅涉 §验收标题与 checklist 项），亦未被本轮修复触碰**，属轻微可读性问题，不影响实现正确性。
- 架构 §6.3（L309）基线措辞仍为"整页空状态（复用 09），视图切换器仍可见但不发请求"。plan-02 现已更正为"不渲染视图切换器"以贴合 09 真实代码（hasNoData 分支无 ViewSwitcher）。这是 plan 向真实代码靠拢的更准描述；架构基线该句为轻微理想化表述（架构本身仅以"复用 09 整页空状态"为实质约束，未在验收层承诺切换器可见）。plan 作为实现 SSOT 对齐真实代码正确，**不构成阻塞**；如追求文档绝对一致，可后续同步修订架构 §6.3 L309 措辞，但不在本轮 3 修复范围。

## 五、维度复核

仅展开 3 个修复点涉及的维度，其余维度（首轮全绿的 1/2/3/5/6/7/8/10/11/12/14/15/16/17）快速确认无回归。

| 维度 | 首轮 | 本轮复核 | 回归判定 |
|---|---|---|---|
| **4. 验收标准防漂移** | 通过（含 S-1 瑕疵） | AC-09（搜索）→ plan-01 §验收搜索条目（L149）+ README 矩阵 plan-01/02；AC-11（单月）→ plan-01 §验收降级条目（L157）+ README 矩阵 plan-01/02；AC-12（空状态）→ plan-02 §验收（L242）+ README 矩阵 plan-02。三处 AC 在 plan-01/plan-02/README 一致，S-1 瑕疵已清除 | ✅ 无回归 |
| **9. 数据模型与契约** | 通过 | S-3 的 `testId` 为纯前端组件 prop，不进入 API 字段；TrendRankingItem/Response 字段、GET /trend-ranking 参数（search/page/page_size，无 month）、camelCase 转换、`{success,data}` 包裹均未改动 | ✅ 无回归 |
| **13. 功能拆分** | 通过 | 文件清单未变：plan-01 仍 3 个 modify（repository/service/api）；plan-02 仍 2 create（Sparkline/BrokerTrendRanking）+ 4 modify（ViewSwitcher/useBrokerRecommend/api.ts/BrokerRecommendPage）。Task 步数未变：plan-01 6 步、plan-02 7 步（均 ≤12）。依赖 DAG plan-01→plan-02 无环 | ✅ 无回归 |

**其他维度快速确认**：frontmatter status（README review_ready / plan-01/02 draft）、Task step status（全 todo）、Contract 字段、ADR 护栏、复用声明链路、前后端 API 契约四件套等首轮全绿维度，本轮 3 修复均未触碰其相关内容，无回归。

## 六、问题清单

无。

（四节记录的两条"首轮已存在、非本修复引入"的轻微观察不列入问题清单：均不阻塞、不影响实现正确性，且不在本轮 3 修复的 scope 内。）

## 七、结论

**通过，可进入开发。**

首轮 3 条建议项（S-1 AC 标签 / S-2 空状态措辞 / S-3 Sparkline testId）经 grep 全量核查 + 09 真实代码核对，**均已彻底修复**：该改处全改、该留处未误伤、未引入新的契约或文档不一致。3 个修复点涉及维度（4 验收防漂移 / 9 数据契约 / 13 功能拆分）无回归；首轮全绿的其他维度亦无回归。零阻塞、零建议项，实现计划可按 README §9.2 执行顺序（plan-01 → plan-02）进入开发。
