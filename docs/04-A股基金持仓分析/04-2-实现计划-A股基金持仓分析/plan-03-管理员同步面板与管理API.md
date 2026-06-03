---
feat_id: "plan-03"
title: "管理员同步面板与管理 API"
dimension: mixed
phase: 2
status: review
depends_on: ["plan-01"]
---

# plan-03: 管理员同步面板与管理 API

## 功能概要

- **目标**: 在管理后台"数据采集/基金"页面提供手动同步入口（基本信息 + 指定报告期持仓），后端暴露 2 个 POST 端点创建 `AsyncTask`，前端组件展示同步进度与统计。同步失败时弹窗提示原因，旧数据保留。
- **完成后可观察结果**: 管理员登录后进入 `管理/数据采集/基金` 页面，看到"基金基本信息/手动同步"按钮和"基金持仓/同步指定报告期"控件。点击同步后按钮变为"同步中…"并禁用，前端轮询任务状态；同步完成后页面展示"新增 X / 更新 Y / 失败 Z"统计，并在同步记录表中追加一条执行记录。若 Tushare 返回异常，弹窗提示错误原因，已加载的基金列表与详情页仍可正常访问。
- **依赖**: plan-01（`TaskType.SYNC_FUND_BASIC` / `SYNC_FUND_PORTFOLIO` 已注册，handler 可被 TaskExecutor 调度）
- **关联验收标准**: [AC-06, AC-07]
- **涉及架构模块**: FundAdminAPI、FundTaskHandler、FundSyncPanel（架构 §4.2）
- **前置条件**:
  - plan-01 已完成（任务枚举与 handler 已注册）
  - 现有管理端 UI 框架（`web/src/components/admin/` 目录）已就绪
  - 现有 `useTaskStatus` SWR hook 可复用做任务状态轮询
  - 现有 `TaskMonitorPanel` 组件可作为同步记录展示的参考
- **不在范围**:
  - 自动定时同步（架构 §2.2 明确不做）
  - 基金业务 API 端点（由 plan-02 负责）
  - 业务查询页 UI（由 plan-04、plan-05 负责）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/admin/init_funds.py` | 新建 fund init admin router，2 个 POST 端点 |
| modify | `server/src/api/admin/__init__.py` 或 `router.py` | 注册新 router |

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/components/admin/FundSyncPanel.tsx` | 同步面板组件，含按钮、报告期选择、进度、统计、同步记录表 |
| create | `web/src/lib/api.ts`（append） | 在 `ApiClient` 上添加 `initFundBasic()` 与 `initFundPortfolio(period)` 方法 |
| create | `web/src/hooks/useFunds.ts`（**实际由 plan-04 创建**；本 plan 仅声明所有权：复用现成的 `useTaskStatus` 做任务轮询，不新增任何 SWR hook） | 复用 `useTaskStatus`（`web/src/hooks/useTaskStatus.ts`），无新数据源 |
| modify | `web/src/components/admin/AdminSidebar.tsx` | 同步面板导航入口 |
| modify | `web/src/app/dashboard/admin/init/page.tsx`（如存在）或新建 | 把 FundSyncPanel 接入管理后台初始化页 |

## 实现规格

### 后端部分

#### 1. 管理员 API（`server/src/api/admin/init_funds.py`）

- `router = APIRouter(prefix="/init", tags=["Admin - Fund Init"])`
- 2 个 POST 端点：

| 端点 | 入参 | 出参 |
| --- | --- | --- |
| `POST /init/funds` | 无 | `ApiResponse[dict]` `{task_id: str}`（架构 §7.3） |
| `POST /init/fund-portfolio` | `InitFundPortfolioRequest { period: str }` | `ApiResponse[dict]` `{task_id: str}` |

- 都用 `_admin = Depends(require_admin)` 强制管理员权限（架构 §8.3 RBAC）
- 内部调用 `TaskManager.create_task(TaskType.SYNC_FUND_BASIC, params={})` 或 `create_task(TaskType.SYNC_FUND_PORTFOLIO, params={"period": period})`
- 并发保护：参考 `server/src/api/admin/init.py` 中的 `_running_tasks` set 模式，避免同一类任务并发
- `period` 入参格式：YYYYMMDD（架构 §7.3 frontend_computed 字段定义）；后端可选做格式校验（length == 8 且全数字）

#### 2. 注册路由

- 修改 `server/src/api/admin/__init__.py`（或 `router.py`）：`from src.api.admin.init_funds import router as init_funds_router` + `include_router(init_funds_router)`

#### 3. 安全要求（架构 §8.3）

- 所有 admin 端点走 `Depends(require_admin)`
- `period` 字段做 Pydantic 校验（`Field(..., pattern=r"^\d{8}$")`）

### 前端部分

#### 4. API 客户端扩展（`web/src/lib/api.ts`）

- 在 `ApiClient` 类添加：
  - `async initFundBasic(): Promise<{task_id: string}>`：`POST /init/funds`
  - `async initFundPortfolio(period: string): Promise<{task_id: string}>`：`POST /init/fund-portfolio`，body = `{ period }`
- 端点 baseURL 已是 `${API_BASE_URL}/api/v1`，admin 端点需加 `/admin` 前缀；按需在 `request` 中通过 params 或独立方法处理

#### 5. 同步面板组件（`web/src/components/admin/FundSyncPanel.tsx`）

- 布局对照架构 §3.1 UX 线框图"管理端同步页"：
  - 顶部"基金基本信息同步"区：标题 + `[手动同步]` 按钮 + "上次成功：YYYY-MM-DD HH:MM 共 X 条"
  - 中部"基金持仓明细同步"区：标题 + 报告期下拉选择 + `[同步指定报告期]` 按钮 + `同步今日新披露` 按钮（**计划层新增，架构 §3.1 流程 C 未提及；复用现有 sync 逻辑的快捷入口**）+ "上次成功：..."
  - 底部"同步记录"表格：列（时间 / 任务 / 结果 / 新增 / 更新 / 失败）
- 状态：
  - 同步中：按钮变"同步中…"并 disabled；显示进度（依赖 `useTaskStatus`）
  - 同步完成：从 `AsyncTask.result` 读取 `{added, updated, failed}`，在面板顶部 toast 展示，并在同步记录表追加一行
  - 同步失败：从 `AsyncTask.error_message` 读取错误，弹窗（或页面顶部 alert）展示
- 复用现有 `useTaskStatus`（`web/src/hooks/useTaskStatus.ts`）做任务轮询
- 报告期下拉：默认展示最近 8 个季度（可由后端查询 `SELECT DISTINCT report_period FROM fund_portfolio ORDER BY report_period DESC LIMIT 8`，或前端硬编码最近 8 个季度）
- "同步今日新披露"按钮：调用 `initFundPortfolio(<最新已存在 report_period>)`，复用现有 sync 逻辑

#### 6. 集成入口

- 在 `web/src/components/admin/AdminSidebar.tsx` 添加"数据采集 / 基金"菜单项
- 在管理后台"数据采集"页面（或新建 `web/src/app/dashboard/admin/fund-init/page.tsx`）引入 `<FundSyncPanel />`

#### 7. 可观测性（架构 §8.5 传播）

- 同步结果 toast 与同步记录表是前端层可观测性
- 后端 admin 端点不写日志（创建 task 的动作已由 TaskExecutor 在 handler 内部记录到 AsyncTaskLog）

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 admin init_funds router | backend | done | 2 个 POST 端点 + 管理员权限校验 |
| 2 | 注册 admin router | backend | done | `server/src/api/admin/__init__.py` |
| 3 | ApiClient 添加 2 个方法 | frontend | done | `initFundBasic` / `initFundPortfolio` |
| 4 | 创建 FundSyncPanel 组件 | frontend | done | 含按钮、报告期、进度、统计、记录表 |
| 5 | AdminSidebar 添加导航 | frontend | done | 菜单项"基金同步" |
| 6 | 接入管理后台页面 | frontend | done | 创建 `web/src/app/dashboard/admin/fund-init/page.tsx`，渲染 `<FundSyncPanel />` |

## 验收标准

### 后端验收

- [ ] AC-06 `POST /api/v1/admin/init/funds`（带管理员 token）返回 200，body 含 `task_id`；AsyncTask 表新增一条 `task_type='sync_fund_basic'`、`status='pending'` 记录
- [ ] AC-06 `POST /api/v1/admin/init/fund-portfolio` 带 `{period: '20241231'}` 返回 200，AsyncTask 表新增一条 `task_type='sync_fund_portfolio'`、`params={'period': '20241231'}` 记录
- [ ] AC-07 Tushare 返回 401（mock 错误）时，AsyncTask 最终 `status='failed'`，`error_message` 含"Tushare 权限不足"或具体错误
- [ ] **未带管理员 token** 调用上述端点返回 403
- [ ] `period` 字段格式错误（length != 8 或非数字）返回 422

### 前端验收

- [ ] AC-06 管理员登录后，`管理 / 数据采集 / 基金` 页面可见"手动同步"和"同步指定报告期"按钮；普通用户不可见
- [ ] AC-06 点击"手动同步"后按钮 disabled 且显示"同步中…"
- [ ] AC-06 同步完成后顶部 toast 展示"新增 X / 更新 Y / 失败 Z"统计
- [ ] AC-06 同步记录表追加一行展示本次执行结果
- [ ] AC-07 同步失败时弹窗（或 alert）展示错误原因；已加载的基金列表与详情页仍可正常访问
- [ ] AC-07（L4 降级）Tushare 完全不可用时，管理端同步面板展示"数据源暂时不可用"提示，已有基金数据正常查询（架构 §8.2 L4）
- [ ] E2E-TDD：管理端同步流程的 red 证据先存在（实现前预期失败），green 证据在实现后通过（`tests/e2e/admin-fund-sync.spec.ts`，路径锚定 `web/tests/e2e/`）
- [ ] `npm run build` 通过；`npm run lint` 通过
- [ ] 复用现有 `useTaskStatus` 轮询任务状态（无新数据源）

### 性能验收（架构 §8.1）

- [ ] admin API 端点响应时间 < 500ms（创建 task 的轻量操作）

## 验证命令

```bash
# 后端
cd server
uvicorn server.main:app --port 8000

# 验证 admin API（需管理员 token）
TOKEN="<admin_access_token>"
curl -X POST -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/admin/init/funds" | jq
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"period":"20241231"}' "http://localhost:8000/api/v1/admin/init/fund-portfolio" | jq

# 验证非管理员被拒
USER_TOKEN="<normal_user_token>"
curl -X POST -H "Authorization: Bearer $USER_TOKEN" "http://localhost:8000/api/v1/admin/init/funds" -i
# 期望 403

# 验证 period 格式校验
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"period":"abc"}' "http://localhost:8000/api/v1/admin/init/fund-portfolio" -i
# 期望 422

# 验证 TaskExecutor 会调度 task（启动后端服务后等待若干秒）
psql $DATABASE_URL -c "SELECT id, task_type, status, error_message, result FROM async_task ORDER BY id DESC LIMIT 5;"

# 前端
cd web
npm run dev
# 浏览器访问 http://localhost:3000/dashboard/admin/fund-init
# 以管理员身份登录 → 点击"手动同步" → 等待完成 → 检查 toast 与同步记录表

# E2E（spec 文件路径锚定 web/tests/e2e/）
cd web
pnpm e2e -- tests/e2e/admin-fund-sync.spec.ts
```

## 交接上下文

- **架构章节**: §3.1 流程 C、§4.2 模块职责（FundAdminAPI、FundTaskHandler）、§6.4 管理员同步流程、§7.3 API 边界、§8.2 L3 降级、§8.3 RBAC
- **相关代码**:
  - 后端：`server/src/api/admin/init.py`（参照 `POST /init/sectors` 的实现模式）、`server/src/api/deps.py`（`require_admin`）、`server/src/services/task_manager.py`（`create_task`）、`server/src/services/task_handlers.py`（TaskType 枚举）
  - 前端：`web/src/components/admin/DataInitPanel.tsx`（参照同步面板布局）、`web/src/components/admin/TaskMonitorPanel.tsx`（参照任务监控展示）、`web/src/hooks/useTaskStatus.ts`（任务轮询）、`web/src/lib/api.ts`（ApiClient 扩展点）
- **契约 / 数据对象**:
  - 后端入参：`InitFundPortfolioRequest { period: str }`
  - 后端出参：`{task_id: str}`
  - 前端依赖 AsyncTask 的 `result` 字段（`{added, updated, failed}`）与 `error_message` 字段展示统计与错误
- **下游消费方**:
  - 后续 plan-04 / plan-05 不依赖本 plan
  - 本 plan 仅供管理员角色使用

## 风险与边界

- **执行顺序**: 按 Task 列表 1→6 顺序；后端 1-2 与前端 3-6 可并行开发但前端联调需后端先就绪
- **验证失败排查方向**:
  - 端点 403：检查是否带管理员 token；检查 `require_admin` 是否从 `Depends` 正确注入
  - 任务一直 pending：检查 `TaskExecutor` 是否在轮询（启动后端服务）；检查 AsyncTask 表的 `task_type` 字段值是否在 `TaskType` 枚举中
  - 同步记录表无新增行：检查 `useTaskStatus` 轮询是否在 sync 完成后停止；检查结果写入 `AsyncTask.result` 的逻辑
- **允许修改的额外文件**: 无
- **暂停条件**:
  - 现有 `useTaskStatus` 行为与"按钮 disabled 控制"不能直接组合时（需新增状态管理中间层）
  - 现有 `AdminSidebar` 结构不允许新增菜单项（需调整布局）
- **风险备注**:
  - 同步任务可能耗时 10-30 分钟（架构 §8.1），需在前端做"长时间运行"的视觉提示（如进度条 + 取消按钮可选）
  - "同步今日新披露"按钮在最新报告期未同步过的情况下可能无意义（推荐后端检测并提示）
- **E2E 适用说明**: 本功能含明确 UI 触达点（同步面板），必须有 E2E 覆盖（`tests/e2e/admin-fund-sync.spec.ts`，路径锚定 `web/tests/e2e/`）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 重复点击"手动同步"（已有任务 running） | admin API 返回 `ApiResponse(success=False, message="已有同步任务正在运行")` | done |
| period 格式错误 | FastAPI 422 验证错误 | done |
| 管理员 token 过期 | 401，由前端跳登录 | done |
| Tushare 不可用 | task 置 `failed`，`error_message` 记录 | done |

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 同步进行中页面被关闭 | 任务在后台继续，下次进入页面时通过 `useTaskStatus` 显示当前状态 | done |
| 同步进行中点击"取消" | 调 admin 取消端点（如存在）；当前架构未提供取消 UI，仅做 disabled 控制 | done |
| 同步记录表无数据 | 表格空态文案"暂无同步记录" | done |
| 报告期下拉无选项（表为空） | 提示"请先在管理端执行一次同步" | done |
| 网络中断导致轮询失败 | 重试 3 次后提示"无法获取任务状态，请稍后刷新" | done |
