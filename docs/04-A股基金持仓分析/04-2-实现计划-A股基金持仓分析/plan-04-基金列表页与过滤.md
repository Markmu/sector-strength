---
feat_id: "plan-04"
title: "基金列表页与过滤"
dimension: frontend
phase: 2
status: review
depends_on: ["plan-02"]
---

# plan-04: 基金列表页与过滤

## 功能概要

- **目标**: 在 `/dashboard/funds/` 路由下提供基金列表页，含基金搜索框、股票反查入口（仅入口，跳转逻辑在 plan-05）、市场与基金类型过滤、分页表格。
- **完成后可观察结果**: 普通用户登录后，从仪表盘"基金分析"入口进入基金列表页。页面顶部有"按基金代码/名称"搜索框与"按股票代码/名称"反查搜索框；左侧过滤面板含"市场（场内/场外）"与"基金类型（股票型/混合型/债券型/QDII）"复选项。输入"沪深 300"后，列表展示所有名称含此关键字的基金（不区分大小写），过滤项与搜索词同时生效。点击某只基金跳转 `/dashboard/funds/{ts_code}`（由 plan-05 实现详情页）。空列表/无结果展示对应文案。分页 pageSize=20，列表加载 < 2s。
- **依赖**: plan-02（`GET /api/v1/funds` 业务 API 已就绪）
- **关联验收标准**: [AC-01, AC-02]
- **涉及架构模块**: FundUI（架构 §4.2）
- **前置条件**:
  - plan-02 已完成（业务 API 已上线）
  - shadcn/ui + Tailwind v4 + SWR 框架已就绪
  - 现有 `web/src/app/dashboard/sector-analysis/` 路由可作为同级独立模块的参考
  - 现有仪表盘导航（`web/src/app/dashboard/page.tsx`）需添加"基金分析"入口
- **不在范围**:
  - 基金详情页（由 plan-05 负责）
  - 反查结果页（由 plan-05 负责）
  - 管理端同步面板（由 plan-03 负责）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/app/dashboard/funds/page.tsx` | 基金列表页（含搜索/过滤/分页布局） |
| create | `web/src/components/funds/FundListTable.tsx` | 基金列表表格组件 |
| create | `web/src/components/funds/FundSearchBar.tsx` | 搜索栏（含基金搜索 + 股票反查入口） |
| create | `web/src/components/funds/FundFilterPanel.tsx` | 过滤面板（市场 + 类型多选） |
| create | `web/src/components/funds/Pagination.tsx` | 通用分页组件（或复用现有） |
| create | `web/src/hooks/useFunds.ts` | SWR hook：`useFundList(params)` |
| modify | `web/src/lib/api.ts` | `ApiClient` 添加 `getFunds(params)` 方法 |
| modify | `web/src/app/dashboard/page.tsx` | 仪表盘添加"基金分析"入口卡片 |

### 后端维度

无。

## 实现规格

### 前端部分

#### 1. API 客户端扩展（`web/src/lib/api.ts`）

- 在 `ApiClient` 类添加 `getFunds(params: { search?: string; market?: string; fundType?: string; page: number; pageSize: number }): Promise<PaginatedResponse<Fund>>`
- 复用现有 ApiResponse 包装与认证头

#### 2. SWR hook（`web/src/hooks/useFunds.ts`）

- `useFundList(params)`：使用 SWR `useSWR(['fundList', params], () => api.getFunds(params))`
- 入参变化时自动重新请求
- 返回 `{ data, isLoading, error, mutate }`
- 缓存：默认 30s 重新校验（与现有 `useSectorRanking` 等保持一致）

#### 3. 搜索栏（`web/src/components/funds/FundSearchBar.tsx`）

- 两个输入框：
  - "按基金代码/名称"：受控 input，placeholder = "输入基金代码或名称"
  - "按股票代码/名称"：受控 input，placeholder = "按股票反查"
- 基金搜索：输入回车或 300ms debounce 后触发 `onSearch(value)`（由列表页接收并更新 URL query）
- 股票反查：输入回车后跳转 `/dashboard/funds/reverse-lookup?symbol=<value>`（plan-05 实现目标页）

#### 4. 过滤面板（`web/src/components/funds/FundFilterPanel.tsx`）

- 复选框组（多选）：
  - 市场：场内 ETF、场外
  - 基金类型：股票型、混合型、债券型、QDII
- 状态提升：过滤项变化时 `onChange({ market: string[], fundType: string[] })` 通知父组件
- 内部映射：market `场内` → `E`，`场外` → `O`；fundType 直接使用中文值

#### 5. 列表表格（`web/src/components/funds/FundListTable.tsx`）

- 列：代码、名称、类型、跟踪标的、管理人、成立日期、操作（"详情"链接）
- 排序：默认按代码升序（API 已排序，前端不再二次排序）
- 空状态：
  - 加载中：骨架占位
  - 搜索无结果：表格区显示"未找到匹配基金，请调整搜索词或清除过滤项"
  - 列表为空：表格区显示"暂无基金数据，请管理员先在管理后台执行同步"
- 点击行 / "详情"链接 → `router.push('/dashboard/funds/' + tsCode)`

#### 6. 列表页（`web/src/app/dashboard/funds/page.tsx`）

- 布局对照架构 §3.1 UX 线框图"基金列表页"：
  - 顶部 `<FundSearchBar />`
  - 左侧 `<FundFilterPanel />`，右侧 `<FundListTable />` + 分页
- URL query 同步：`?search=xxx&market=E,O&fundType=股票型&page=1&pageSize=20`
  - 搜索 / 过滤 / 分页变化时更新 URL（便于分享与刷新保留）
  - 初始挂载时从 URL 恢复
- 数据获取：调用 `useFundList({ search, market, fundType, page, pageSize })`
- 性能：搜索做 300ms debounce，避免每次按键都发请求

#### 7. 仪表盘入口（`web/src/app/dashboard/page.tsx`）

- 在现有入口卡片区域新增"基金分析"卡片，跳转 `/dashboard/funds`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | ApiClient 添加 `getFunds` | frontend | done | `web/src/lib/api.ts` |
| 2 | 创建 `useFundList` SWR hook | frontend | done | `web/src/hooks/useFunds.ts` |
| 3 | 创建 `FundSearchBar` 组件 | frontend | done | 含基金搜索 + 股票反查入口 |
| 4 | 创建 `FundFilterPanel` 组件 | frontend | done | 市场 + 类型多选复选框 |
| 5 | 创建 `FundListTable` 组件 | frontend | done | 表格 + 空态 + 加载骨架 |
| 6 | 创建 `Pagination` 组件 | frontend | done | 通用分页（或复用现有） |
| 7 | 创建列表页 `page.tsx` | frontend | done | 组合以上组件 + URL 同步 |
| 8 | 仪表盘添加"基金分析"入口 | frontend | done | `web/src/app/dashboard/page.tsx` |

## 验收标准

### 前端验收

- [ ] AC-01 普通用户登录后能进入 `/dashboard/funds`，看到搜索框、过滤面板、列表表格
- [ ] AC-01 输入"沪深 300"后，列表展示所有名称含此关键字的基金（不区分大小写）
- [ ] AC-01 列表项含代码、名称、类型、跟踪标的、管理人、成立日期、操作列
- [ ] AC-01 点击某只基金的"详情"链接跳转到 `/dashboard/funds/{tsCode}`（由 plan-05 实现详情页）
- [ ] AC-02 勾选"场内 ETF"与"股票型"两个过滤项后，列表仅展示"市场 = 场内"且"基金类型 = 股票型"的基金
- [ ] AC-02 过滤项与搜索词同时生效（搜索 + 过滤组合查询）
- [ ] 搜索无结果：表格区显示"未找到匹配基金，请调整搜索词或清除过滤项"
- [ ] 列表为空：表格区显示"暂无基金数据，请管理员先在管理后台执行同步"
- [ ] 搜索使用 300ms debounce，避免每次按键都发请求
- [ ] URL query 同步：刷新页面后搜索/过滤/分页状态保留
- [ ] E2E-TDD：列表/搜索/过滤流程 red 证据先存在（实现前预期失败），green 证据在实现后通过（`tests/e2e/fund-list.spec.ts`，路径锚定 `web/tests/e2e/`）
- [ ] `npm run build` 通过；`npm run lint` 通过

### 性能验收（架构 §8.1）

- [ ] 列表页首次加载（pageSize=20）< 2s（DevTools Network 面板计时确认）

### 降级回归验收（架构 §8.2 L1/L2）

- [ ] L1 降级：某基金无持仓数据时，列表中该基金行内标注"暂无数据"（**基于 API 返回的 `hasPortfolio=false` 字段**，由 plan-02 §1 L1 降级子查询提供）
- [ ] L2 降级：管理员未同步过基本信息时，列表展示"暂无基金数据，请管理员先同步"（架构 §3.2 分支）

## 验证命令

```bash
# 启动前后端
cd server && uvicorn server.main:app --port 8000 &
cd web && npm run dev

# 浏览器
open http://localhost:3000/dashboard
# 以普通用户身份登录 → 点击"基金分析"入口 → 进入 /dashboard/funds

# E2E（spec 文件路径锚定 web/tests/e2e/）
cd web
pnpm e2e -- tests/e2e/fund-list.spec.ts

# 构建
cd web
npm run build
npm run lint
npm run test -- --testPathPattern=useFunds
```

## 交接上下文

- **架构章节**: §3.1 流程 A、§4.2 模块职责（FundUI）、§6.1 列表加载、§7.3 API 边界
- **相关代码**:
  - 前端：`web/src/lib/api.ts`（ApiClient 扩展点）、`web/src/hooks/useSectorRanking.ts`（参考 SWR hook 模式）、`web/src/app/dashboard/sector-analysis/page.tsx`（参考同级别独立模块的页面布局）、`web/src/app/dashboard/page.tsx`（仪表盘入口位置）
  - 后端：plan-02 实现的 `GET /api/v1/funds`
- **契约 / 数据对象**:
  - `PaginatedResponse<Fund>`：来自 plan-02
  - `Fund` interface（camelCase）：tsCode、name、fundType、benchmark、management、foundDate
  - URL query 格式：`?search=xxx&market=E,O&fundType=股票型&page=1&pageSize=20`（market 多值用逗号分隔）
- **下游消费方**:
  - plan-05（详情页/反查页）依赖本 plan 提供的"基金列表入口"和"反查入口跳转"

## 风险与边界

- **执行顺序**: 按 Task 列表 1→8 顺序；hooks 与 API 客户端先就绪，组件再组合
- **验证失败排查方向**:
  - 列表 401：检查是否登录、token 是否过期
  - 列表为空但数据库有数据：检查 plan-02 的 `GET /funds` 是否被正确调用（DevTools Network）
  - 搜索不生效：检查 debounce 是否被错误实现（每次按键都发请求导致竞态）
  - URL 同步失效：检查 query 解析与 setQuery 的逻辑
- **允许修改的额外文件**: 无
- **暂停条件**:
  - 现有 SWR 缓存策略与本功能要求不匹配时
  - 现有仪表盘结构不允许新增入口卡片时
- **风险备注**:
  - "股票反查"搜索框在本 plan 仅做跳转实现，不做实际查询（plan-05 实现目标页）
  - 大数据量下 LIKE 查询可能慢，依赖 `funds.ts_code` 与 `funds.name` 索引（plan-01 已建）

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 搜索关键词含特殊字符（如 %、_） | URL 编码；后端 SQLAlchemy 参数化查询天然转义 | todo |
| 过滤项全部取消 | 不传 market/fundType 参数（不过滤） | todo |
| 分页超出范围（page=999） | API 返回空数组，UI 正常展示 | todo |
| 网络中断 | SWR 错误态：表格区显示"加载失败，请重试" + 重试按钮 | todo |
| 慢网络（>2s） | 表格区显示骨架占位 | todo |
| 用户未登录直接访问 `/dashboard/funds` | `middleware.ts` 重定向到登录页（项目已有路由守卫） | todo |
| 列表中某基金无持仓数据 | 行内"类型"列旁标注"暂无数据"（架构 §6.2 step 7） | todo |
