---
feat_id: "plan-03"
title: "前端数据状态标签页"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-02"]
---

# plan-03: 前端数据状态标签页

## 1. 功能概要

- **目标**: 在数据管理页面新增"数据状态"标签页，包含状态卡片、补齐按钮、进度展示的完整前端实现
- **完成后可观察结果**: 管理员打开数据管理页面，默认进入"数据状态"标签页，三张卡片分别展示板块历史数据、均线数据、强度数据的最新日期和状态标记。数据正常时显示绿色"正常"Badge，缺失时显示橙色"缺失"Badge和缺失日期范围。点击"补齐缺失数据"按钮后按钮禁用，卡片切换为进度条展示，每 2 秒自动刷新进度。补齐完成后卡片自动回到正常态，失败时显示红色错误信息和重新补齐按钮。API 请求失败时显示错误态和重试链接。
- **依赖**: plan-02（后端 API 和 task handlers）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06]
- **涉及架构模块**: DataStatusPanel, DataTypeCard, useDataStatus hook
- **前置条件**: plan-02 已完成，后端 API 可访问；Next.js 开发服务器可启动
- **不在范围**: 个股数据状态展示；WebSocket 实时推送；自动定时补齐

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/hooks/useDataStatus.ts` | SWR hook，请求状态 API |
| create | `web/src/components/admin/DataTypeCard.tsx` | 单类数据状态卡片组件 |
| create | `web/src/components/admin/DataStatusPanel.tsx` | 状态面板组件，组装 3 张卡片 |
| modify | `web/src/app/dashboard/admin/data/page.tsx` | 新增"数据状态"标签页 |

## 3. 实现规格

### 前端部分

#### 1. 新建 useDataStatus.ts hook

创建 `web/src/hooks/useDataStatus.ts`：

```typescript
import useSWR from 'swr'
import { fetcher } from '@/lib/fetcher'

interface MissingRange {
  start: string
  end: string
}

interface ActiveTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total: number
  error_message: string | null
}

export interface DataTypeStatus {
  type: 'history' | 'ma' | 'strength'
  label: string
  latest_date: string | null
  status: 'normal' | 'missing' | 'no_data'
  missing_range: MissingRange | null
  active_task: ActiveTask | null
}
```

- 使用 `useSWR` 请求 `/api/v1/admin/data/status`
- 条件式 `refreshInterval`：当 data 中存在 active_task 且 status 为 pending/running 时设为 2000，否则为 0
- 返回 `{ data, isLoading, error, mutate }`
- `data` 为 `DataTypeStatus[]`，默认空数组

#### 2. 新建 DataTypeCard.tsx 组件

创建 `web/src/components/admin/DataTypeCard.tsx`：

Props:
```typescript
interface DataTypeCardProps {
  data: DataTypeStatus
  onBackfill: (type: 'history' | 'ma' | 'strength') => void
  backfilling: boolean
}
```

**状态渲染规则**：

| 卡片状态 | 渲染内容 |
|---------|---------|
| `status === 'no_data'` | 灰色 Badge "暂无数据"，不显示补齐按钮 |
| `status === 'normal'` | 绿色 Badge "正常"，显示最新日期 |
| `status === 'missing'` | 橙色 Badge "缺失"，显示最新日期 + 缺失范围 |

**active_task 渲染**：
- `pending`/`running`: 显示进度条（div 宽度 = progress / total * 100%）+ 百分比文字
- `failed`: 红色错误信息 + "重新补齐"按钮
- `completed`: 不显示
- `null`: 不显示任务信息

**UI 元素**：
- 卡片: `border rounded-lg p-4`
- Badge: 绿色(slate-700 bg)、橙色(bg-amber-100 text-amber-700)、灰色(bg-gray-100 text-gray-500)
- 进度条: `bg-blue-100` 容器 + `bg-blue-600` 填充
- 补齐按钮: 蓝色 "补齐缺失数据"，loading 态显示 Loader2 图标
- 缺失范围: `缺失范围：{start} ~ {end}`

#### 3. 新建 DataStatusPanel.tsx 组件

创建 `web/src/components/admin/DataStatusPanel.tsx`：

**职责**：
- 调用 `useDataStatus()` 获取状态数据
- 加载中: 3 张卡片位置显示骨架屏（`animate-pulse`）
- 错误态: 显示错误信息 + "重试"按钮（调用 `mutate()`）
- 正常态: 渲染 3 张 `DataTypeCard`

**轮询逻辑**：
- 轮询由 useDataStatus hook 内的 SWR 条件式 `refreshInterval` 自动管理（ADR-4）
- DataStatusPanel 无需手动管理定时器，直接使用 hook 返回的 data 即可

**补齐按钮处理**：
```typescript
const handleBackfill = async (type: 'history' | 'ma' | 'strength') => {
  setBackfillingType(type)
  try {
    await postFetcher(`/api/v1/admin/data/backfill/${type}`)
    mutate()
  } catch (err) {
    // 处理 409 冲突等错误
  } finally {
    setBackfillingType(null)
  }
}
```

#### 4. 修改 data/page.tsx

修改 `web/src/app/dashboard/admin/data/page.tsx`：

变更：
1. Tab 类型扩展: `'data-status' | 'init' | 'ma-calc' | 'strength-calc'`
2. 默认 tab 改为 `'data-status'`
3. 新增"数据状态"标签按钮（第一个位置），带 `●` 标记
4. 新增条件渲染: `{activeTab === 'data-status' && <DataStatusPanel />}`
5. 导入 `DataStatusPanel` 组件

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 useDataStatus.ts SWR hook | frontend | done | 请求 GET /admin/data/status，导出类型定义 |
| 2 | 创建 DataTypeCard.tsx 状态卡片组件 | frontend | done | 根据 status 渲染不同状态，含进度条和补齐按钮 |
| 3 | 创建 DataStatusPanel.tsx 面板组件 | frontend | done | 组装 3 张卡片，管理轮询和补齐操作 |
| 4 | 修改 data/page.tsx 新增"数据状态"标签 | frontend | done | 扩展 Tab 类型，设为默认标签，渲染 DataStatusPanel |
| 5 | 创建 E2E 测试用例文件 | e2e | done | 创建 `docs/e2e/02-e2e-用例-数据状态标签页.md`，覆盖核心路径；后续 Playwright spec 路径 `web/tests/e2e/data-status.spec.ts` |

## 5. 验收标准

### 前端验收

- [ ] AC-01 页面加载后三张卡片正确展示数据类型名称、最新日期、状态标记
- [ ] AC-01 默认展示"数据状态"标签页
- [ ] AC-01 数据表为空时显示"暂无数据"灰色 Badge，不显示补齐按钮
- [ ] AC-02 缺失时正确显示橙色 Badge 和缺失日期范围（YYYY-MM-DD ~ YYYY-MM-DD）
- [ ] AC-03 点击"补齐缺失数据"按钮后按钮禁用，API 调用成功后立即刷新状态
- [ ] AC-03 补齐 API 调用失败（非 409，如网络超时、500）时显示错误提示，按钮恢复可用
- [ ] AC-04 补齐进行中显示进度条，每 2 秒自动刷新
- [ ] AC-04 补齐完成后卡片自动回到正常态
- [ ] AC-05 补齐失败时显示红色错误信息和重新补齐按钮
- [ ] AC-05 点击重新补齐按钮能再次创建任务
- [ ] AC-06 状态 API 请求失败时显示错误态和重试链接
- [ ] AC-06 点击重试链接能重新请求状态 API
- [ ] 标签页切换正常，不影响现有数据初始化、均线计算、强度计算标签
- [ ] E2E-TDD：创建 `docs/e2e/02-e2e-用例-数据状态标签页.md` 覆盖核心路径（三张卡片状态展示、缺失范围、补齐按钮点击、进度轮询、失败重试、错误态重试）；red 阶段：API 未启动时用例预期失败，截图留证；green 阶段：完整流程通过，截图留证。目标 Playwright spec：`web/tests/e2e/data-status.spec.ts`

## 6. 验证命令

```bash
cd web
npm run dev
# 访问 http://localhost:3000/dashboard/admin/data
# 验证默认展示"数据状态"标签页
# 验证三张卡片状态
# 验证补齐按钮和进度条

npm run build  # 确认构建通过
npm run lint   # 确认 lint 通过
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责, §6.3 进度轮询链路, ADR-4, ADR-5
- **相关代码**:
  - `web/src/lib/fetcher.ts` — fetcher / postFetcher
  - `web/src/app/dashboard/admin/data/page.tsx` — 现有数据管理页面
  - `web/src/components/admin/` — 现有 admin 组件目录
- **契约 / 数据对象**: `DataStatusResponse`、`DataTypeStatus`（架构 §7.2）
- **上游依赖**: plan-02（后端 API）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→4），hook 先于组件
- **验证失败排查方向**: 检查后端 API 是否可访问（`NEXT_PUBLIC_API_URL` 配置）；检查浏览器 Network 面板请求状态
- **允许修改的额外文件**: 无
- **暂停条件**: 后端 API 不可访问；SWR hook 请求持续失败
- **E2E 说明**: 用户可观察功能，Task 5 负责创建 E2E 测试用例 `docs/e2e/02-e2e-用例-数据状态标签页.md`，后续落地为 Playwright spec `web/tests/e2e/data-status.spec.ts`
- **风险备注**: 轮询间隔 2 秒，页面不可见时 SWR 的 revalidateOnFocus 自动暂停；多管理员同时操作时后端 409 冲突已处理

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 状态 API 超时或失败 | 显示错误态 + 重试链接 | done |
| 补齐 API 返回 409 冲突 | 按钮恢复可用，toast 提示已有任务在执行 | done |
| 补齐 API 调用失败（非 409） | 按钮恢复可用，显示错误 toast 提示 | done |
| 页面不可见（切换标签页/最小化） | SWR revalidateOnFocus 自动暂停轮询 | done |
| 多张卡片同时有活跃任务 | 各卡片独立轮询和展示进度 | done |
| active_task.completed 状态 | 卡片回到 normal 态，不显示任务信息 | done |
