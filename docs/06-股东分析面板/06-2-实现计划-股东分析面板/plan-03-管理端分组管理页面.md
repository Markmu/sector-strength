---
feat_id: "plan-03"
title: "管理端分组管理页面"
dimension: frontend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-03: 管理端分组管理页面

## 1. 功能概要

- **目标**: 在管理后台新增"股东分组管理"Tab 页，管理员可查看分组列表（组名、描述、规则数、匹配股数）、新增分组、编辑分组（组名、描述、匹配关键词）、删除分组（二次确认）、预览匹配股数。
- **完成后可观察结果**: 管理员从管理后台侧边栏进入"股东分组管理"页面，看到 5 个预定义分组的列表表格。点击"新增分组"弹出编辑表单，填写组名和关键词后保存成功，列表刷新出现新分组。点击"编辑"可修改关键词并实时预览匹配股数。点击"删除"弹出确认对话框，确认后分组从列表消失。
- **依赖**: plan-01（Admin CRUD API 已就绪）
- **关联验收标准**: [AC-06, AC-07, AC-10]
- **涉及架构模块**: GroupManagementPanel（前端组件）, Admin API routes（plan-01 提供）
- **前置条件**: plan-01 的 Admin API 可正常访问
- **不在范围**: 用户侧股东分析页面（plan-04）、数据同步

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/app/dashboard/admin/shareholder-groups/page.tsx` | 管理页面路由入口 |
| create | `web/src/components/admin/ShareholderGroupPanel.tsx` | 分组管理主组件 |
| modify | `web/src/components/admin/AdminSidebar.tsx` | 新增"股东分组管理"导航项 |
| modify | `web/src/lib/api.ts` | 新增 admin API 方法 |

## 3. 实现规格

### 前端部分

#### 1. Admin API 方法

在 `web/src/lib/api.ts` 的 `adminApi` 对象中追加：

```typescript
// 分组管理
getShareholderGroups: () => adminApiClient.get('/admin/shareholder-groups'),
createShareholderGroup: (data: { name: string; description?: string; keywords: string[] }) =>
  adminApiClient.post('/admin/shareholder-groups', data),
updateShareholderGroup: (id: number, data: { name?: string; description?: string; keywords?: string[] }) =>
  adminApiClient.patch(`/admin/shareholder-groups/${id}`, data),
deleteShareholderGroup: (id: number) =>
  adminApiClient.delete(`/admin/shareholder-groups/${id}`),
previewShareholderGroupMatch: (keywords: string, excludeGroupId?: number) => {
  const params = new URLSearchParams({ keywords });
  if (excludeGroupId) params.append('exclude_group_id', String(excludeGroupId));
  return adminApiClient.get(`/admin/shareholder-groups/preview?${params}`);
},
```

#### 2. ShareholderGroupPanel 组件

新建 `web/src/components/admin/ShareholderGroupPanel.tsx`：

**数据获取**：使用 SWR 或 useState + fetch 调用 `adminApi.getShareholderGroups()`

**分组列表表格**（使用 shadcn Table 组件）：
- 列：分组名称 | 描述 | 匹配规则数 | 匹配股数 | 操作
- 操作列：[编辑] [删除] 按钮
- 顶部：[+ 新增分组] 按钮

**编辑表单弹窗**（使用 shadcn Dialog 组件）：
- 分组名称：Input（必填）
- 描述：Input（可选）
- 匹配关键词列表：
  - 每个关键词一行 Input + [删除] 按钮
  - [+ 添加关键词] 按钮追加新 Input
- 预览区域：显示"当前规则匹配到 N 只股票"（关键词变化时调用 preview API）
- 底部：[取消] [保存] 按钮

**删除确认对话框**（使用 shadcn AlertDialog 组件）：
- 提示文案："确定删除分组 '{name}'？删除后用户侧将不再展示该组数据。"
- [取消] [确认删除] 按钮

**交互逻辑**：
- 新增：打开空编辑表单 → 填写 → 保存 → 刷新列表
- 编辑：打开预填充的编辑表单 → 修改 → 保存 → 刷新列表
- 删除：弹出确认 → 确认 → 调用删除 API → 刷新列表
- 预览：编辑表单中关键词变化时 debounce 500ms 调用 preview API，展示匹配股数
- 错误处理：API 失败时用 toast 提示错误信息

#### 3. 管理页面路由

新建 `web/src/app/dashboard/admin/shareholder-groups/page.tsx`，对齐现有 `top10-holder-init/page.tsx` 模式：

```tsx
import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import ShareholderGroupPanel from '@/components/admin/ShareholderGroupPanel';

export default function ShareholderGroupsPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader title="股东分组管理" subtitle="监控组与匹配规则管理" />
      <ShareholderGroupPanel />
    </AdminLayoutWithSidebar>
  );
}
```

> 注意：用具名导出 `AdminLayoutWithSidebar`（来自 `@/components/layouts/AdminLayout`，路径是复数 `layouts`）+ `DashboardHeader`（来自 `@/components/dashboard`），与 `top10-holder-init/page.tsx` 一致。

#### 4. 更新 AdminSidebar

修改 `web/src/components/admin/AdminSidebar.tsx` 的 navItems 数组：
- 在"股票持仓同步"和"用户管理"之间新增：`{ id: 'shareholder-groups', label: '股东分组管理', icon: Users, href: '/dashboard/admin/shareholder-groups', description: '股东分组和匹配规则管理' }`（`Users` 图标已在 AdminSidebar 的 lucide-react imports 中）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新增 Admin API 方法到 api.ts | frontend | done | 5 个方法：列表/新增/编辑/删除/预览 |
| 2 | 创建 ShareholderGroupPanel 组件 — 列表表格 | frontend | done | 分组列表 + 操作按钮 |
| 3 | 创建 ShareholderGroupPanel 组件 — 编辑表单弹窗 | frontend | done | 组名/描述/关键词编辑 + 匹配预览 |
| 4 | 创建 ShareholderGroupPanel 组件 — 删除确认 | frontend | done | AlertDialog 二次确认 |
| 5 | 创建管理页面路由 page.tsx | frontend | done | 路由入口 |
| 6 | 更新 AdminSidebar 导航 | frontend | done | 新增"股东分组管理"项 |

## 5. 验收标准

### AC-06 验收：管理员新增监控组

- [ ] AC-06 管理员点击"新增分组"按钮，弹出编辑表单，输入组名"QFII"、添加关键词"瑞士银行"和"摩根大通"，点击保存后新分组出现在列表中
- [ ] 预览区域显示匹配股数（关键词变化时实时更新）

### AC-07 验收：管理员编辑匹配规则

- [ ] AC-07 管理员点击"国家队"分组的"编辑"按钮，表单预填充当前关键词，新增关键词"国新投资"，保存后列表刷新、规则数更新

### AC-10 验收：管理员删除监控组

- [ ] AC-10 管理员点击"QFII"分组的"删除"按钮，弹出确认对话框，确认后分组从列表消失
- [ ] 取消删除时不执行删除操作

### UI 交互验收

- [ ] 分组列表正确展示组名、描述、规则数、匹配股数
- [ ] 关键词编辑支持添加和删除
- [ ] API 错误时展示 toast 错误提示

### 性能验收（架构 §8.1 目标）

- [ ] 管理端页面加载和 CRUD 操作响应时间 < 1s

### 构建验收

- [ ] `npm run build` 通过，无类型错误
- [ ] `npm run lint` 通过

### E2E-TDD 验收（关键路径）

> 架构 §2.3 成功标准 + dev-plan-check 通过标准：用户可观察功能须有 E2E-TDD 验收项（red 预期失败 / green 实现后通过两阶段证据）。

- [ ] **red 阶段**：在 `docs/e2e/06-e2e-用例-股东分组管理.md` 编写 Playwright 用例，覆盖管理员登录 → 分组列表 → 新增分组 → 编辑关键词 + 匹配预览 → 删除二次确认；实现前运行预期失败，证据存 `docs/e2e/evidence/plan-03-e2e-red-{date}.md`
- [ ] **green 阶段**：实现完成后运行同一用例全部通过，证据存 `docs/e2e/evidence/plan-03-e2e-green-{date}.md`

## 6. 验证命令

```bash
# 前端构建
cd web && npm run build

# Lint 检查
cd web && npm run lint

# 启动前端开发服务器
cd web && npm run dev

# 手动验证流程：
# 1. 以管理员登录
# 2. 进入管理后台 → 股东分组管理
# 3. 查看分组列表
# 4. 新增分组 → 编辑 → 删除
```

## 7. 交接上下文

- **架构章节**: §3.1 流程 B（管理员管理监控组）、§6.4 管理员新增/编辑监控组、§6.5 管理员删除监控组
- **路径对齐备注**: 架构 §7.3 写 `/api/admin/shareholder-groups`，但代码实际挂载链为 `/api/v1/admin/*`（`main.py` prefix `/api` × admin router）。前端 `adminApiClient`（baseURL 已含 `/api/v1`）调用 `/admin/shareholder-groups` → `/api/v1/admin/shareholder-groups`，与代码一致；plan 按代码实际挂载链对齐，架构 §7.3 的 `/api/admin/` 前缀为文档笔误，不影响执行。
- **相关代码**:
  - `web/src/lib/api.ts` — AdminApiClient 模式
  - `web/src/components/admin/AdminSidebar.tsx` — 导航项定义
  - `web/src/app/dashboard/admin/` — 已有 admin 页面模式参考（如 fund-init/、top10-holder-init/）
- **契约 / 数据对象**:
  - `GroupListItem`: { id, name, description, isSystem, ruleCount, matchedStockCount, keywords }
  - `CreateGroupRequest`: { name, description?, keywords }
  - `UpdateGroupRequest`: { name?, description?, keywords? }
- **下游消费方**: 无（管理端独立页面）
- **实现期 E2E 测试兼容性修复（implement 阶段，按 implementer skill "如确需调整测试，必须说明" 规则记录）**:
  - **mock helper `route.continue()` → `route.fallback()`**：`web/tests/e2e/helpers/mock-shareholder-api.ts`。Playwright `page.route` 按 LIFO 调用 handler，当多个 helper 在同一 URL 注册（list GET + create POST）时，后注册的 POST handler 若用 `route.continue()` 处理 GET 会把请求直接发到网络、跳过先注册的 GET handler → `ERR_CONNECTION_REFUSED`。改用 `route.fallback()` 转交下一个 handler。属测试基建修复，与实现 bug 无关。
  - **删除行选择器歧义**：`shareholder-groups.spec.ts` TC-1.7/1.8/1.9。mock 数据"外资投行"组描述含子串"（QFII）"，与 QFII 组名共用"QFII"，导致 `tr.filter({ hasText: 'QFII' })` 匹配 2 行（strict mode violation）。改为用精确文本 QFII 的 span 向上找 `ancestor::tr` 唯一定位。
  - **AlertDialog role 适配**：TC-1.7/1.8/1.9 把 `getByRole('dialog')` 改为 `getByRole('alertdialog')`。实现按本 plan §3.2 用 shadcn AlertDialog，Radix 强制 `role="alertdialog"`（非 `dialog`）。
  - **组件侧 StrictMode 初始加载去重**：`ShareholderGroupPanel.tsx` 用 `initialFetchedRef` 防止 React StrictMode 在 dev 下对 `useEffect` 的双重调用导致初始列表重复请求（生产无此问题）。显式 `fetchGroups`（保存/删除后刷新）不受影响。此修复让 mock helper 的 callIndex 序列能正确对应"初始加载 / 操作后刷新"两次调用。
- **green 证据**：本步骤只实现到 red spec 转通过（11/11 稳定通过，连续两次 4.1s 内完成），green 证据文档由后续 `test-e2e` 写入 `docs/e2e/evidence/plan-03-e2e-green-{date}.md`。

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（API 方法 → 组件 → 路由 → 导航）
- **验证失败排查方向**:
  1. 页面 404 → 检查路由文件路径和 AdminSidebar 导航项
  2. API 调用 401 → 检查 AdminApiClient token 获取逻辑
  3. API 调用 404 → 检查 plan-01 的 Admin API 路由是否注册
  4. 列表为空 → 检查 plan-01 种子数据是否已写入
- **允许修改的额外文件**: 无
- **暂停条件**: API 返回非预期结构时暂停，需与 plan-01 确认 API 契约
- **E2E 验收**: 管理端关键路径（新增 → 编辑关键词 + 预览 → 删除二次确认）按 §5 E2E-TDD 验收项执行 red/green 两阶段验证，用例入 `docs/e2e/`，证据入 `docs/e2e/evidence/`。

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 分组列表为空 | 展示空表格 + "暂无分组"提示 | done |
| 新增分组组名重复 | API 返回错误，inline 提示"操作失败：组名已存在"（项目无 toast 库，参照 UserManagementPanel 的 inline error banner 模式） | done |
| 编辑时不修改任何字段直接保存 | 正常保存（无变化） | done |
| 关键词为空时保存 | 允许保存（空关键词列表） | done |
| 删除预定义分组 | 正常删除，前端展示确认对话框 | done |
| preview API 返回 0 | 预览区显示"当前规则匹配到 0 只股票" | done |
| API 网络错误 | inline 提示"加载失败"/"操作失败"（项目无 toast 库，用 inline error banner） | done |
