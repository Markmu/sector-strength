---
feat_id: "plan-03"
title: "管理端同步入口"
dimension: mixed
phase: 3
status: done
depends_on: ["plan-02"]
---

# plan-03: 管理端同步入口

## 功能概要

- **目标**: 在管理后台新增十大流通股东同步的触发入口，包括 Admin API 端点和前端"股票持仓同步"面板。管理员可选择报告期、触发同步、实时查看进度、查看同步结果统计。
- **完成后可观察结果**: 管理员登录后进入"数据管理 → 数据初始化"tab，在页面中看到"股票持仓同步"区块（分隔线 + 报告期下拉 + 同步按钮 + 上次同步信息）。选择报告期点击同步后，按钮变为"同步中…（X / Y）"并显示进度条。同步完成后展示"新增 X 条 / 跳过 Y 只 / 失败 Z 只股票"统计。下方任务记录表中追加一条记录。重复同步同一报告期不产生重复数据。
- **依赖**: plan-02（同步服务和任务处理器已就绪）
- **关联验收标准**: [AC-01, AC-03, AC-05, AC-07]
- **涉及架构模块**: Admin API `/admin/init/top10-holders`, 前端 StockTop10SyncPanel 组件, adminApi 客户端方法
- **前置条件**: plan-02 已完成（SYNC_TOP10_HOLDERS 任务已注册），后端和前端开发环境就绪
- **不在范围**: 面向用户的展示页、定时调度、断点续传

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/admin/init_top10_holders.py` | Admin API 路由（POST /init/top10-holders） |
| modify | `server/src/api/admin/__init__.py` | 注册新路由 |

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 新增 `adminApi.initStockTop10Holders()` 方法和 `TaskType.SYNC_TOP10_HOLDERS` |
| create | `web/src/components/admin/StockTop10SyncPanel.tsx` | 股票持仓同步面板组件 |
| create | `web/src/app/dashboard/admin/top10-holder-init/page.tsx` | 股票持仓同步独立页面（仿照 fund-init/page.tsx） |
| modify | `web/src/components/admin/AdminSidebar.tsx` | 添加"股票持仓同步"导航项 |

## 实现规格

### 后端部分

#### 1. 创建 Admin API 端点

文件：`server/src/api/admin/init_top10_holders.py`

参考 `server/src/api/admin/init_funds.py` 中的 `init_fund_portfolio` 端点模式。

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix="/init", tags=["Admin - Stock Top10 Holders Init"])

class InitTop10HoldersRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{8}$", description="报告期，YYYYMMDD 格式")

@router.post("/top10-holders")
async def init_top10_holders(request: InitTop10HoldersRequest, ...):
    """触发十大流通股东同步"""
```

实现要点：
- **并发保护**：查询是否已有 `SYNC_TOP10_HOLDERS` 类型的 running/pending 任务（参考 `init_fund_portfolio` 的并发保护逻辑）
- **创建任务**：`TaskManager.create_task(task_type=TaskType.SYNC_TOP10_HOLDERS.value, params={"period": request.period}, timeout_seconds=3600)`
- **请求体字段来源**: `period` 为 `user_input`（管理员手动选择）
- **返回**：`ApiResponse(success=True, data={"task_id": task.task_id}, message=f"股票持仓同步任务已创建（报告期: {request.period}）")`

**安全要求（架构 §8.3）**:
- 复用 `require_admin` 依赖，仅管理员可触发
- `period` 字段通过 Pydantic `pattern=r"^\d{8}$"` 校验，防止注入

**可观测性（架构 §8.5）**: 无额外日志要求，任务执行过程的日志由 plan-02 的 Service 层和 TaskManager 负责。

#### 2. 注册路由

文件：`server/src/api/admin/__init__.py`

在现有路由注册列表中添加：
```python
from server.src.api.admin.init_top10_holders import router as init_top10_holders_router
admin_router.include_router(init_top10_holders_router)
```

参考现有的 `init_funds_router` 注册模式。

### 前端部分

#### 3. 扩展 API 客户端

文件：`web/src/lib/api.ts`

**3a. 在 `tasksApi.TaskType` 中新增**：
```typescript
SYNC_TOP10_HOLDERS: "sync_top10_holders"
```
（参考现有的 `SYNC_FUND_BASIC` 和 `SYNC_FUND_PORTFOLIO`）

**3b. 在 `adminApi` 中新增方法**：
```typescript
async initStockTop10Holders(period: string): Promise<ApiResponse<{ task_id: string }>> {
    return this.post('/admin/init/top10-holders', { period });
}
```
（参考 `adminApi.initFundPortfolio(period)` 的实现模式）

#### 4. 创建 StockTop10SyncPanel 组件

文件：`web/src/components/admin/StockTop10SyncPanel.tsx`

参考 `web/src/components/admin/FundSyncPanel.tsx` 的组件模式，创建"股票持仓同步"面板。

**组件结构**：

1. **报告期选择器**：
   - 下拉框展示最近 8 个季度末日期（ADR-4）
   - 硬编码生成函数（参考 FundSyncPanel 中的 `getRecentQuarters`）
   - 默认选中最近一个季度
   - 支持手动输入

2. **同步按钮**：
   - 未同步时：显示"同步"
   - 同步中：显示"同步中…（X / Y）"并禁用（X=progress, Y=total）
   - 使用 `useTaskStatus` hook 轮询任务状态

3. **上次同步信息**：
   - 从最近一条 `sync_top10_holders` 类型的 completed 任务中读取
   - 显示：报告期、完成时间、记录数
   - 使用 `tasksApi.listTasks({ task_types: 'sync_top10_holders', page_size: 1 })` 获取

4. **进度展示**（同步中显示）：
   - 进度条：`progress / total` 百分比
   - 实时统计："新增 X 条 | 失败 Z 只股票"
   - 使用 `useTaskStatus` 的 `onProgress` 回调更新

5. **同步结果展示**（完成后显示）：
   - "新增 X 条 / 跳过 Y 只 / 失败 Z 只股票"
   - 从任务日志中解析统计信息

6. **错误展示**：
   - 任务失败时显示错误信息（AC-07）

**组件 Props**：无特殊 props，组件自管理状态。

#### 5. 创建独立页面并注册导航

**5a. 创建页面文件**

文件：`web/src/app/dashboard/admin/top10-holder-init/page.tsx`

仿照 `web/src/app/dashboard/admin/fund-init/page.tsx`，创建独立页面：

```tsx
'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import StockTop10SyncPanel from '@/components/admin/StockTop10SyncPanel';

export default function Top10HolderInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="股票持仓同步"
        subtitle="十大流通股东数据采集和手动同步管理"
      />
      <StockTop10SyncPanel />
    </AdminLayoutWithSidebar>
  );
}
```

**5b. 在 AdminSidebar 添加导航项**

文件：`web/src/components/admin/AdminSidebar.tsx`

在现有导航列表中，找到基金同步导航项的位置，在其后添加"股票持仓同步"导航项：

```tsx
{
  name: '股票持仓同步',
  href: '/dashboard/admin/top10-holder-init',
  icon: UsersIcon,  // 或其他合适图标
}
```

参考现有基金同步导航项的注册模式（路径 `/dashboard/admin/fund-init`）。

### 性能验收（架构 §8.1 目标）

- [ ] `POST /admin/init/top10-holders` 响应时间 ≤ 500ms（DevTools Network 面板人工确认）
- [ ] 前端进度刷新延迟 ≤ 3 秒（2s 轮询间隔）

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 Admin API 端点 `POST /init/top10-holders` | backend | done | 参考 init_funds.py 的 init_fund_portfolio |
| 2 | 在 admin `__init__.py` 注册新路由 | backend | done | 参考 init_funds_router 注册 |
| 3 | 在 api.ts 新增 `TaskType.SYNC_TOP10_HOLDERS` 和 `adminApi.initStockTop10Holders()` | frontend | done | 参考现有基金同步 API 方法 |
| 4 | 创建 StockTop10SyncPanel 组件 | frontend | done | 参考 FundSyncPanel 组件模式 |
| 5 | 创建 top10-holder-init 独立页面并在 AdminSidebar 添加导航 | frontend | done | 仿照 fund-init/page.tsx 创建页面 + Sidebar 导航项 |

## 验收标准

### 全流程验收（US 覆盖矩阵）

> 架构文档 §2.3 定义的成功标准：US-01 ~ US-05 全部可正常走通。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 选择报告期并触发"股票持仓同步" | plan-03 | AC-01 验收：点击同步 → 按钮状态变更 |
| US-02 | 同步过程中看到实时进度（已处理 X / 共 Y） | plan-03 | AC-03 验收：进度条和数字实时更新 |
| US-03 | 同步完成后看到统计结果（新增、失败数量） | plan-03 | AC-05 验收：统计数字正确展示 |
| US-04 | 个别股票失败不中断整体任务 | plan-02 | AC-04 验收：任务完成 + 统计含失败数 |
| US-05 | 重复同步不产生重复数据 | plan-02 | AC-06 验证：两次同步记录数一致 |

- [ ] US-01 ~ US-05 全部可在当前实现下正常走通（最终集成回归）

### 后端验收

- [ ] AC-01 `POST /admin/init/top10-holders` 返回 `{ success: true, data: { task_id: "xxx" } }`，任务正确创建
- [ ] AC-07 并发保护生效：已有 running 的 `sync_top10_holders` 任务时，再次调用返回失败
- [ ] AC-01 `period` 格式校验：非 YYYYMMDD 格式返回 422 错误
- [ ] AC-07 非管理员调用返回 401/403

### 前端验收

- [ ] AC-01 通过 AdminSidebar 可导航至"股票持仓同步"独立页面，页面中包含报告期下拉和同步按钮
- [ ] AC-01 报告期下拉展示最近 8 个季度末日期，默认选中最近一个
- [ ] AC-03 点击同步后按钮变为"同步中…（X / Y）"并禁用，进度条和数字实时更新
- [ ] AC-05 同步完成后展示"新增 X 条 / 跳过 Y 只 / 失败 Z 只股票"统计
- [ ] AC-05 "上次同步信息"正确显示最近一次成功同步的报告期、时间和记录数
- [ ] AC-07 同步失败时弹窗展示错误信息
- [ ] `npm run build` 通过
- [ ] `npm run lint` 通过

### 性能验收（架构 §8.1 目标）

- [ ] `POST /admin/init/top10-holders` 响应时间 ≤ 500ms（DevTools Network 面板人工确认）
- [ ] 前端进度刷新延迟 ≤ 3 秒（2s 轮询间隔，观察进度数字是否平滑更新）

## 验证命令

```bash
# 后端 API 验证
# 前提：后端服务运行中

# 0. 获取 admin_token
# 方式 A：从浏览器 DevTools → Application → localStorage 复制 accessToken
# 方式 B：通过登录 API 获取
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your_password>"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")

# 1. 验证 API 端点存在
curl -X POST http://localhost:8000/api/admin/init/top10-holders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"period": "20241231"}'

# 2. 验证参数校验
curl -X POST http://localhost:8000/api/admin/init/top10-holders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"period": "invalid"}'
# 期望: 422 错误

# 前端验证
cd web && npm run build && npm run lint

# 手动端到端验证
# 1. 启动前端：cd web && npm run dev
# 2. 启动后端：cd server && uvicorn server.main:app --reload --port 8000
# 3. 登录管理后台，通过 AdminSidebar 进入"股票持仓同步"页面
# 4. 选择报告期 "2024-12-31"，点击"同步"
# 5. 观察按钮状态 → 进度条 → 完成统计
# 6. 确认下方任务记录表中有新记录
# 7. 再次同步同一报告期，确认数据不重复
```

## 交接上下文

- **架构章节**: §6.1 触发同步任务、§6.3 前端进度展示、§7.3 API 边界、§7.6 命名规则、§9 Phase C、ADR-3/ADR-4
- **相关代码**:
  - `server/src/api/admin/init_funds.py` — Admin API 端点模式参考（并发保护、任务创建、参数校验）
  - `server/src/api/admin/__init__.py` — 路由注册模式参考
  - `web/src/components/admin/FundSyncPanel.tsx` — 前端同步面板组件模式参考（报告期选择、useTaskStatus、进度条、统计展示）
  - `web/src/hooks/useTaskStatus.ts` — 任务状态轮询 hook
  - `web/src/lib/api.ts` — `adminApi.initFundPortfolio()` 和 `tasksApi.TaskType` 参考
- **契约 / 数据对象**:
  - API 请求：`{ period: string }`（YYYYMMDD，user_input）
  - API 响应：`{ success: boolean, data: { task_id: string }, message: string }`
  - 前端任务类型：`"sync_top10_holders"`（与后端 TaskType.value 一致）
- **上游依赖**: plan-02 的 `SYNC_TOP10_HOLDERS` 任务处理器已注册
- **下游消费方**: 无（本期最终功能）

## 风险与边界

- **执行顺序**: 先完成 Admin API（Task 1-2），再完成前端 API 方法（Task 3），最后完成前端组件（Task 4-5）
- **验证失败排查方向**:
  - API 404：检查 `__init__.py` 路由注册
  - 前端 API 调用失败：检查 `NEXT_PUBLIC_API_URL` 环境变量、API 路径拼接
  - 进度不更新：检查 `useTaskStatus` hook 的 pollInterval（应为 2000ms）
  - 组件未渲染：检查 StockTop10SyncPanel 是否正确导入到 DataInitPanel 或父级页面
- **允许修改的额外文件**: 无
- **暂停条件**: 前端编译失败或 API 路由 404 时，暂停排查
- **E2E 不适用说明**: 本功能为管理端入口，E2E 通过手动验证覆盖（需 Tushare 环境和 admin 登录）。自动化 E2E 需要 mock Tushare API，首版不要求。后续可补充 Playwright 管理端 E2E 用例确保同步触发→进度→统计的回归测试。
- **ADR-3 偏差说明**: 架构 ADR-3 原文说"不创建独立组件文件"，但 brownfield 验证发现 FundSyncPanel 本身即为独立组件文件（16KB），且渲染在独立页面 `fund-init/page.tsx` 而非 DataInitPanel 中。StockTop10SyncPanel 遵循相同模式创建独立组件 + 独立页面。建议后续更新架构 ADR-3 使其与实际代码模式一致。
- **风险备注**:
  - 上次同步信息依赖 `tasksApi.listTasks` 的 `task_types` 过滤功能，确认该参数已实现

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 已有 running 的同步任务 | API 返回失败，提示"已有任务正在运行" | done |
| period 格式非法 | Pydantic 校验返回 422 错误 | done |
| 非管理员调用 | `require_admin` 依赖返回 401/403 | done |

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 同步中刷新页面 | 重新加载后通过 listTasks 检测到 running 任务，恢复进度展示 | done |
| 同步中切换 tab | 组件卸载但任务继续执行，切回来后恢复状态 | done |
| 无历史同步记录 | "上次同步信息"区域显示"暂无同步记录" | done |
| 报告期手动输入非法格式 | 同步按钮点击后 API 返回 422，展示错误提示 | done |
| 同步中点击同步 | 按钮已禁用，防止重复触发 | done |
