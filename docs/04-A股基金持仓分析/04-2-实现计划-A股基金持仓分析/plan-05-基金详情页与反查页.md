---
feat_id: "plan-05"
title: "基金详情页与反查页"
dimension: frontend
phase: 3
status: review
depends_on: ["plan-02", "plan-04"]
---

# plan-05: 基金详情页与反查页

## 功能概要

- **目标**: 在 `/dashboard/funds/[ts_code]` 路由实现基金详情页（基本信息卡 + 最新一期持仓明细表），在 `/dashboard/funds/reverse-lookup` 路由实现股票反查页（按股票代码查询重仓基金列表）。两个页面都正确处理"暂无持仓数据"的两种场景（数据源未收录 vs 当前报告期未披露），并提供清晰的空状态文案与操作按钮。
- **完成后可观察结果**:
  - **详情页**：从列表点击"华泰柏瑞沪深 300ETF（510300.SH）"后跳转 `/dashboard/funds/510300.SH`，顶部展示基金基本信息卡（代码、名称、类型、管理人、成立日期、跟踪标的），下方展示"最新报告期 2024-12-31"持仓明细表格，按"占净值比"降序排列，列含股票代码、名称、持仓市值、股数、占净值比、占流通比。若该基金无任何持仓数据，详情页展示"暂无最新持仓数据（数据源未收录该基金）" + "返回列表"按钮；若存在旧期但最新期未披露，展示"暂无最新一期持仓数据（当前报告期尚未披露，请稍后再试）" + "返回列表" + "触发同步"按钮。
  - **反查页**：从列表顶部"按股票反查"输入"600519"回车后跳转 `/dashboard/funds/reverse-lookup?symbol=600519`，展示"最新一期报告期 2024-12-31 重仓持有贵州茅台的基金"列表（占净值比 ≥ 1%），按占净值比降序，列含基金代码、名称、持仓市值、股数、占净值比、占流通比。点击某基金跳转其详情页。若无结果，展示"最新一期暂无基金披露重仓持有该股票"。
- **依赖**: plan-02（业务 API）、plan-04（列表页跳转入口与反查入口）
- **关联验收标准**: [AC-03, AC-04, AC-05]
- **涉及架构模块**: FundUI（架构 §4.2）
- **前置条件**:
  - plan-02 已完成（业务 API 上线，含 `isPortfolioEmpty` / `hasPortfolio` / `latestReportPeriod` 元信息）
  - plan-04 已完成（列表页与反查入口可跳转）
  - shadcn/ui 表格组件（Table）已就绪
- **不在范围**:
  - 历史多期对比（架构 §2.2 明确不做）
  - 持仓变动提醒（架构 §2.2 明确不做）
  - 行业聚合分析（架构 §2.2 明确不做）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/app/dashboard/funds/[ts_code]/page.tsx` | 基金详情页（动态路由） |
| create | `web/src/app/dashboard/funds/reverse-lookup/page.tsx` | 反查结果页 |
| create | `web/src/components/funds/FundInfoCard.tsx` | 基金基本信息卡片组件 |
| create | `web/src/components/funds/FundPortfolioTable.tsx` | 持仓明细表格组件 |
| create | `web/src/components/funds/ReverseLookupTable.tsx` | 反查结果表格组件 |
| create | `web/src/components/funds/EmptyPortfolioState.tsx` | 暂无持仓数据空态组件（含两种场景区分） |
| modify | `web/src/hooks/useFunds.ts` | 新增 `useFundDetail`、`useFundPortfolio`、`useReverseLookup` 三个 SWR hooks |
| modify | `web/src/lib/api.ts` | `ApiClient` 添加 `getFund(tsCode)`、`getFundPortfolio(tsCode, params)`、`reverseLookup(symbol, params)` 三个方法 |

### 后端维度

无。

## 实现规格

### 前端部分

#### 1. API 客户端扩展（`web/src/lib/api.ts`）

- `getFund(tsCode: string): Promise<Fund>`：`GET /funds/{tsCode}`
- `getFundPortfolio(tsCode: string, params: { page, pageSize }): Promise<PortfolioResponse>`：`GET /funds/{tsCode}/portfolio`
- `reverseLookup(symbol: string, params: { page, pageSize }): Promise<PaginatedResponse<ReverseLookupItem>>`：`GET /funds/reverse-lookup?symbol=...`

#### 2. SWR hooks（`web/src/hooks/useFunds.ts` 追加）

- `useFundDetail(tsCode)`：`useSWR(['fundDetail', tsCode], () => api.getFund(tsCode))`
- `useFundPortfolio(tsCode, params)`：`useSWR(['fundPortfolio', tsCode, params], () => api.getFundPortfolio(tsCode, params))`
- `useReverseLookup(symbol, params)`：`useSWR(['reverseLookup', symbol, params], () => api.reverseLookup(symbol, params))`；symbol 为空时不请求

#### 3. 详情页（`web/src/app/dashboard/funds/[ts_code]/page.tsx`）

- 顶部"← 返回列表"链接 → `router.push('/dashboard/funds')`
- 并行获取基本信息与持仓（`useFundDetail` + `useFundPortfolio`）
- 加载中：骨架占位
- 错误态（如 tsCode 不存在）：展示"基金不存在" + "返回列表"按钮
- 内容布局对照架构 §3.1 UX 线框图"基金详情页"：
  - 顶部 `<FundInfoCard fund={data} />` 展示基本信息
  - 下方标题"最新报告期：YYYY-MM-DD（公告日 YYYY-MM-DD），持仓明细（共 X 条）"——报告期与公告日均取自 API 返回的 `latestReportPeriod` / `latestAnnDate` 字段；若 `latestAnnDate` 为 NULL 则省略"（公告日 ...）"片段
  - `<FundPortfolioTable items={data.data} total={data.total} />`
  - 分页（默认前 20 条 + "全部持仓" 展开完整列表）

#### 4. 基本信息卡（`web/src/components/funds/FundInfoCard.tsx`）

- 字段展示：代码、名称、类型（含投资风格，如"股票型 / 被动指数型"）、管理人、成立日期、跟踪标的（来自 `benchmark` 字段）
- 跟踪标的展示规则：被动指数型展示"XXX 指数"；无单一跟踪指数显示"—"（架构 BR-10）
- 货币与单位：持仓市值后端已统一为"元"，前端可按需格式化为"X.X 亿"（BR-09）

#### 5. 持仓明细表（`web/src/components/funds/FundPortfolioTable.tsx`）

- 列：股票代码、名称（`stockName` 为 NULL 时显示"—"，BR-09）、持仓市值、持股数、占净值比、占流通比
- 排序：API 已按 `stkMkvRatio` DESC 排序
- 分页：默认前 20 条；提供"全部持仓"展开按钮（加载完整列表）
- 占比格式：保留两位小数（BR-09）
- 占流通比为 NULL 时显示"—"（BR-09 / 港股境外标的）

#### 6. 空持仓空态组件（`web/src/components/funds/EmptyPortfolioState.tsx`）

- 根据 `isPortfolioEmpty` 与 `hasPortfolio` 区分两种场景（架构 §6.2 修复项）：
  - 场景 A（`isPortfolioEmpty=true, hasPortfolio=false`）：文案"暂无最新持仓数据（数据源未收录该基金）"，按钮"返回列表"
  - 场景 B（`isPortfolioEmpty=true, hasPortfolio=true`）：文案"暂无最新一期持仓数据（当前报告期尚未披露，请稍后再试）"，按钮"返回列表" + "触发同步"（"触发同步"链接到 plan-03 管理面板 `/dashboard/admin/fund-init`）

#### 7. 反查结果页（`web/src/app/dashboard/funds/reverse-lookup/page.tsx`）

- 顶部"← 返回基金分析"链接
- 标题区：展示股票代码 + 名称（取自 API 返回的 `stockName` 元信息）+ "反查结果：最新报告期 YYYY-MM-DD 持有该股的基金"（报告期取自 `reportPeriod` 元信息）+ "共 X 只基金重仓持有（占净值比 ≥ 1%）"
- `<ReverseLookupTable items={data.data} total={data.total} />`
- 分页
- 空结果：表格区显示"最新一期暂无基金披露重仓持有该股票"
- 加载中：骨架占位
- symbol 缺失（直接访问 `/dashboard/funds/reverse-lookup` 无 query）：提示"请输入股票代码" + 返回列表按钮

#### 8. 反查结果表（`web/src/components/funds/ReverseLookupTable.tsx`）

- 列：基金代码、基金名称、持仓市值、持股数、占净值比、占流通比
- 排序：API 已按 `stkMkvRatio` DESC 排序
- 点击基金代码 / 名称跳转到 `/dashboard/funds/{tsCode}`（详情页）

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | ApiClient 添加 3 个方法 | frontend | done | `getFund` / `getFundPortfolio` / `reverseLookup` |
| 2 | 新增 3 个 SWR hooks | frontend | done | `useFundDetail` / `useFundPortfolio` / `useReverseLookup` |
| 3 | 创建 `FundInfoCard` 组件 | frontend | done | 展示基金基本信息 |
| 4 | 创建 `FundPortfolioTable` 组件 | frontend | done | 持仓表 + 分页 + 全部展开 |
| 5 | 创建 `EmptyPortfolioState` 组件 | frontend | done | 两种空持仓场景 |
| 6 | 创建详情页 `[ts_code]/page.tsx` | frontend | done | 动态路由 + 并行请求 |
| 7 | 创建 `ReverseLookupTable` 组件 | frontend | done | 反查结果表 |
| 8 | 创建反查页 `reverse-lookup/page.tsx` | frontend | done | 反查结果展示 |

## 验收标准

### 前端验收

#### 详情页
- [ ] AC-03 普通用户登录后从列表点击"华泰柏瑞沪深 300ETF（510300.SH）"跳转 `/dashboard/funds/510300.SH`
- [ ] AC-03 顶部展示基金基本信息（代码、名称、类型、管理人、成立日期、跟踪标的）
- [ ] AC-03 下方展示"最新报告期"与持仓明细表，按"占净值比"降序
- [ ] AC-03 表格列含股票代码、名称、持仓市值、股数、占净值比、占流通比
- [ ] AC-03 持仓数据按"全部持仓"展开后能加载完整列表（无分页）
- [ ] AC-05 场景 A：某基金无任何持仓记录 → 展示"暂无最新持仓数据（数据源未收录该基金）" + "返回列表"按钮（`isPortfolioEmpty=true, hasPortfolio=false`）
- [ ] AC-05 场景 B：某基金有旧期但最新期未披露 → 展示"暂无最新一期持仓数据（当前报告期尚未披露，请稍后再试）" + "返回列表" + "触发同步"按钮（`isPortfolioEmpty=true, hasPortfolio=true`）
- [ ] 跟踪标的无数据时显示"—"
- [ ] 港股 / 境外标的占流通比为 NULL 时显示"—"
- [ ] **E2E 强化（动态路由）**：`tests/e2e/fund-detail.spec.ts` 必须覆盖"URL 含 `.` 能正确解析"用例（`page.goto('/dashboard/funds/510300.SH')` 成功且 ts_code 完整保留为 `510300.SH`，未被截断为 `510300`）

#### 反查页
- [ ] AC-04 列表页顶部"按股票反查"输入"600519"回车后跳转 `/dashboard/funds/reverse-lookup?symbol=600519`
- [ ] AC-04 展示"最新一期报告期 + 持有该股的基金"列表（占净值比 ≥ 1%）
- [ ] AC-04 表格按"占净值比"降序，列含基金代码、名称、持仓市值、股数、占净值比、占流通比
- [ ] AC-04 点击某基金跳转其详情页 `/dashboard/funds/{tsCode}`
- [ ] 反查无结果：表格区显示"最新一期暂无基金披露重仓持有该股票"
- [ ] 直接访问 `/dashboard/funds/reverse-lookup` 无 symbol 参数：提示"请输入股票代码" + 返回列表按钮
- [ ] E2E-TDD：详情页/反查页流程 red 证据先存在（实现前预期失败），green 证据在实现后通过（`tests/e2e/fund-detail.spec.ts` + `tests/e2e/fund-reverse-lookup.spec.ts`，路径锚定 `web/tests/e2e/`）
- [ ] `npm run build` 通过；`npm run lint` 通过

### 性能验收（架构 §8.1）

- [ ] 详情页持仓表加载（前 20 条）< 3s
- [ ] 反查页加载（pageSize=20）< 3s

### 降级回归验收（架构 §8.2 L1）

- [ ] 详情页"无持仓"两种场景文案与按钮符合架构 §6.2 修复项规定

## 验证命令

```bash
# 启动前后端
cd server && uvicorn server.main:app --port 8000 &
cd web && npm run dev

# 浏览器
# 1. 详情页
open "http://localhost:3000/dashboard/funds/510300.SH"
# 验证基本信息卡 + 持仓表（占净值比降序）

# 2. 详情页空态（场景 A：无任何记录）
open http://localhost:3000/dashboard/funds/000000.OF
# 验证"暂无最新持仓数据（数据源未收录该基金）" + "返回列表"按钮

# 3. 反查页
open http://localhost:3000/dashboard/funds/reverse-lookup?symbol=600519
# 验证反查结果列表（占净值比 ≥ 1%）

# 4. 反查无结果
open http://localhost:3000/dashboard/funds/reverse-lookup?symbol=999999
# 验证"暂无基金披露重仓持有该股票"

# E2E（spec 文件路径锚定 web/tests/e2e/）
cd web
pnpm e2e -- tests/e2e/fund-detail.spec.ts
pnpm e2e -- tests/e2e/fund-reverse-lookup.spec.ts

# 构建
cd web
npm run build
npm run lint
npm run test -- --testPathPattern=useFunds
```

## 交接上下文

- **架构章节**: §3.1 流程 A + 流程 B、§4.2 模块职责（FundUI）、§6.2 详情页加载、§6.3 反查流程、§6.4 实现原则（§6.2 修复项）、§7.3 API 边界
- **相关代码**:
  - 前端：`web/src/hooks/useFunds.ts`（plan-04 已创建 `useFundList`，本 plan 追加 3 个 hooks）、`web/src/lib/api.ts`（ApiClient 扩展点）、`web/src/components/funds/FundListTable.tsx`（plan-04 列表入口）、`web/src/components/funds/FundSearchBar.tsx`（plan-04 反查搜索框）
  - 后端：plan-02 实现的 `GET /funds/{tsCode}`、`GET /funds/{tsCode}/portfolio`、`GET /funds/reverse-lookup`
- **契约 / 数据对象**:
  - `Fund`（camelCase）：tsCode、name、fundType、management、foundDate、benchmark 等
  - `FundPortfolioOut`：tsCode、stockCode、stockName（可空）、marketValue、amount、stkMkvRatio、stkFloatRatio
  - `PortfolioResponse`：含 `data, total, page, pageSize, isPortfolioEmpty, hasPortfolio, latestReportPeriod, latestAnnDate`（plan-02 定义）
  - `ReverseLookupResponse`：含 `data, total, page, pageSize, stockName, reportPeriod`（plan-02 定义）
  - `ReverseLookupItem`：fundTsCode、fundName、fundType、management、marketValue、amount、stkMkvRatio、stkFloatRatio
- **下游消费方**:
  - 无（本 plan 是依赖 DAG 叶子节点）

## 风险与边界

- **执行顺序**: 按 Task 列表 1→8 顺序；hooks 与 API 客户端先就绪，组件再组合
- **验证失败排查方向**:
  - 详情页 404：检查 tsCode 参数是否被正确解析（Next.js 动态路由）；检查 plan-02 详情 API 是否 404
  - 持仓表为空但 API 有数据：检查元信息 `isPortfolioEmpty` / `hasPortfolio` 解析是否正确
  - 反查无结果但 API 有数据：检查 symbol 是否被正确传到 query；检查阈值 1% 是否被后端正确过滤
  - 港股占流通比显示"0%"而非"—"：检查后端 `stkFloatRatio` 是否为 NULL（不是 0）
- **允许修改的额外文件**: 无
- **暂停条件**:
  - 现有 shadcn/ui Table 组件不能直接满足分页 + 全部展开的需求时（需评估使用第三方如 TanStack Table）
  - 反查结果与详情页的"跳转"逻辑与现有项目路由模式冲突时
- **风险备注**:
  - 动态路由 `[ts_code]` 中包含 `.`（如 `510300.SH`）需 Next.js 正确处理；建议在 `router.push` 时使用 `encodeURIComponent`
  - 反查结果按"占净值比 ≥ 1%"过滤在 API 端，前端不要再二次过滤
  - **E2E 验收（强化）**：`tests/e2e/fund-detail.spec.ts` 必须覆盖一项"详情页 URL 含 `.` 能正常解析"——通过 `page.goto('/dashboard/funds/510300.SH')` 与 `page.goto('/dashboard/funds/510300.SH/')` 两种写法都能成功进入详情页，且 ts_code 解析为 `510300.SH`（不是被截断为 `510300`）；反查页 `?symbol=600519.SH` 同理
  - **shell escape 提示**：zsh 下 `open http://localhost:3000/dashboard/funds/510300.SH` 的 `.` 不需要转义，但 `&` 与 URL 编码字符需要引号包裹
- **E2E 适用说明**: 本功能含两个明确的用户可见页面，必须有 E2E 覆盖

### 前端边界场景

#### 详情页

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| tsCode 不存在 | 错误态"基金不存在" + "返回列表"按钮 | done |
| 持仓加载失败 | 持仓区显示"加载失败，请重试" | done |
| 基本信息加载失败 | 整页错误态 + 重试按钮 | done |
| 持仓为 NULL 字段 | 全部按"—"显示（不显示 0% 或 0） | done |
| "全部持仓"展开后总条数较少 | 表格直接展示全部，不显示分页 | done |

#### 反查页

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| URL 缺 symbol 参数 | 提示"请输入股票代码" + 返回列表按钮 | done |
| symbol 股票不存在（API 404） | 提示"股票代码无效，请检查后重试" | done |
| 反查无结果（无 ≥1% 重仓基金） | 表格区显示"最新一期暂无基金披露重仓持有该股票" | done |
| 反查结果只有 1 条 | 正常展示 1 条 + 不显示分页 | done |
| 反查结果超 1000 条 | 分页正常（架构 §2.3 未给反查最大数目标，按 API 默认 20/页） | done |
