---
feat_id: "plan-04"
title: "指数监控面板与前端集成"
dimension: mixed
phase: 2
status: done
depends_on: ["plan-03"]
---

# plan-04: 指数监控面板与前端集成

## 功能概要

- **目标**: 改造主页（is_admin 条件渲染指数面板）、新建 5 个前端组件（总览卡片/走势图/估值图/权重表）、新建数据管理页指数数据 Tab（同步+关注管理）、集成 collector 日更步骤 9、补 ETF 跳转 useSearchParams。
- **完成后可观察结果**: 管理员登录后主页直接看到 14 只指数的总览卡片网格（涨跌幅红涨绿跌），可滚动查看走势对比图、估值水位图、成分权重表；点击 ETF 资金跳转到 ETF 监控页自动按指数筛选；数据管理页新增「指数数据」Tab 可同步数据和增减关注指数；非管理员登录主页看到原有通用内容。交易日收盘后 collector 自动增量同步指数数据。
- **依赖**: plan-03（查询 API 全部端点可用）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-08c, AC-08d, AC-10, AC-11, AC-12, AC-13]
- **涉及架构模块**: IndexMonitorPage、IndexOverviewCards、IndexTrendChart、IndexValuationChart、IndexWeightTable、IndexSyncPanel、Collector（扩展步骤9）
- **前置条件**: plan-03 完成（6 个查询端点可用）、plan-02 完成（admin 同步端点可用）
- **不在范围**: 数据模型（plan-01）、采集服务（plan-02）、查询 API（plan-03）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|------|------|------|
| modify | `server/src/services/data_updater/collector.py` | run_daily_update 加步骤 9 _update_index_daily() |
| modify | `server/src/services/scheduler/job_manager.py` | 新增指数日更 job（注释停用） |

### 前端维度

| 动作 | 路径 | 说明 |
|------|------|------|
| create | `web/src/types/indexMonitorTypes.ts` | TS 类型定义 |
| modify | `web/src/lib/api.ts` | 新增 indexMonitorApi + admin initIndex 方法 + TaskType 常量 |
| modify | `web/src/app/dashboard/page.tsx` | is_admin 条件渲染 IndexMonitorPage |
| create | `web/src/components/index-monitor/IndexMonitorPage.tsx` | 面板容器 |
| create | `web/src/components/index-monitor/IndexOverviewCards.tsx` | 总览卡片网格 |
| create | `web/src/components/index-monitor/IndexTrendChart.tsx` | ECharts 走势对比 |
| create | `web/src/components/index-monitor/IndexValuationChart.tsx` | ECharts 估值水位 |
| create | `web/src/components/index-monitor/IndexWeightTable.tsx` | 成分权重表 |
| create | `web/src/components/index-monitor/IndexSyncPanel.tsx` | 数据管理页指数Tab内容 |
| create | `web/src/components/index-monitor/helpers.ts` | 格式化/颜色/单位工具 |
| modify | `web/src/app/dashboard/admin/data/page.tsx` | 新增「指数数据」Tab |
| modify | `web/src/components/admin/TaskMonitorPanel.tsx` | 补 3 个指数 task_type 中文映射 |
| modify | `web/src/components/etf-monitor/EtfMonitorPage.tsx` | 加 useSearchParams 读 index_code |

## 实现规格

### 后端部分

#### 1. Collector 日更集成（collector.py）

在 `run_daily_update` 步骤 8（ETF）后加步骤 9，范式对齐步骤 8（try/except 不中断主流程）：

```python
# results dict 加键
'index_daily_updated': 0,

# 步骤 9
try:
    results['index_daily_updated'] = await self._update_index_daily()
except Exception as e:
    logger.error(f"[数据更新] 指数当日采集失败: {e}")
    results['errors'].append(f"index_daily: {e}")
```

新增 `_update_index_daily()` 方法：
```python
async def _update_index_daily(self) -> int:
    from src.services.data_init_index import IndexDataInitService
    service = IndexDataInitService()
    service.set_session(self._session)
    result = await service.sync_index_daily(date.today())
    return result.get('daily_records', 0)
```

#### 2. Scheduler job（job_manager.py）

新增 `_index_daily_update` job（注释停用，与 `_etf_daily_snapshot` 一致）：
```python
# self._scheduler.add_job(
#     self._index_daily_update, CronTrigger(hour=18, minute=30),
#     id="index_daily_update", ...
# )
```

### 前端部分

#### 3. TS 类型定义（indexMonitorTypes.ts）

定义类型对齐架构 §7.2 API 响应 Schema：
- `IndexOverviewItem`（tsCode/name/close/pctChg/amount/peTtm/tradeDate）
- `IndexOverviewData`（indices + tradeDate）
- `IndexTrendSeries`（tsCode/name/points）
- `IndexTrendData`（series + hasData）
- `IndexValuationPoint`（tradeDate/peTtm/pb/turnoverRate）
- `IndexValuationData`（tsCode/points/hasData）
- `IndexWeightItem`（conCode/name/weight）
- `IndexWeightData`（indexCode/tradeDate/weights/concentration）
- `IndexWatchlistItem`（tsCode/name/market/hasValuation）

#### 4. API 客户端（api.ts）

**indexMonitorApi**（范式对齐 etfMonitorApi）：

**路径拼接确认**：endpoint `/index-monitor/overview` × baseURL `${API}/api/v1` = `/api/v1/index-monitor/overview` ✓

```typescript
export const indexMonitorApi = {
  getOverview: () =>
    apiClient.get<{ success: boolean; data: IndexOverviewData }>('/index-monitor/overview'),
  getTrend: (tsCodes: string[], startDate?: string, endDate?: string) =>
    apiClient.get<{ success: boolean; data: IndexTrendData }>('/index-monitor/trend', {
      ts_codes: tsCodes.join(','), start_date: startDate, end_date: endDate,
    }),
  getValuation: (tsCode: string, startDate?: string, endDate?: string) =>
    apiClient.get<{ success: boolean; data: IndexValuationData }>('/index-monitor/valuation', {
      ts_code: tsCode, start_date: startDate, end_date: endDate,
    }),
  getWeights: (indexCode: string, topN: number = 20) =>
    apiClient.get<{ success: boolean; data: IndexWeightData }>('/index-monitor/weights', {
      index_code: indexCode, top_n: topN,
    }),
  getWatchlist: () =>
    apiClient.get<{ success: boolean; data: { watchlist: IndexWatchlistItem[] } }>('/index-monitor/watchlist'),
  updateWatchlist: (tsCodes: string[]) =>
    apiClient.put<{ success: boolean; data: { updated: number } }>('/index-monitor/watchlist', { ts_codes: tsCodes }),
}
```

**query 参数命名确认**：`ts_codes` / `start_date` / `ts_code` / `index_code` / `top_n` 全部 snake_case，后端接收一致 ✓

**adminApi 新增方法**：
```typescript
initIndexBasic: () => adminApiClient.post<{task_id: string}>('/admin/init/index-basic'),
initIndexHistory: (startDate: string, endDate: string) =>
  adminApiClient.post<{task_id: string}>('/admin/init/index-history', { start_date: startDate, end_date: endDate }),
initIndexDaily: () => adminApiClient.post<{task_id: string}>('/admin/init/index-daily'),
```

**TaskType 常量新增**（与 L707-721 格式一致）：
```typescript
SYNC_INDEX_BASIC: 'sync_index_basic',
BACKFILL_INDEX_HISTORY: 'backfill_index_history',
SYNC_INDEX_DAILY: 'sync_index_daily',
```

#### 5. helpers.ts

```typescript
// 涨跌幅颜色：红涨绿跌（中国市场惯例）
export const getChangeColor = (pctChg: number | null): string =>
  pctChg === null ? 'text-gray-500' : pctChg > 0 ? 'text-red-600' : pctChg < 0 ? 'text-green-600' : 'text-gray-500'

// 成交额格式化：千元 → 亿元
export const formatAmount = (amount: number | null): string =>
  amount === null ? '--' : `${(amount / 10000).toFixed(2)} 亿`

// PE 格式化
export const formatPe = (peTtm: number | null): string =>
  peTtm === null ? '暂无估值' : peTtm.toFixed(2)
```

**序列化确认**：后端 amount 已 ÷10000 转亿元输出（plan-03 Task 2），helpers 这里不需再除。但如后端返回的是千元则需除——以后端实际输出为准。pctChg/peTtm 经 `_serialize_value` 转 float，前端直接数值运算 ✓。

#### 6. 主页改造（dashboard/page.tsx）

```tsx
// 顶部 import
import { useAuth } from '...';  // 获取 is_admin（参考现有 auth context）
import { IndexMonitorPage } from '@/components/index-monitor/IndexMonitorPage';

// 条件渲染
{isAdmin ? <IndexMonitorPage /> : (
  <>
    {/* 原有内容：快捷入口 + 市场强度 + 板块热力图 + 排名列表 + 免责声明 */}
  </>
)}
```

#### 7. IndexMonitorPage.tsx — 面板容器

- SWR 获取 overview + watchlist
- 顶部 DashboardHeader（title="关键指数监控"）
- 垂直排列：IndexOverviewCards → IndexTrendChart → IndexValuationChart → IndexWeightTable
- 空状态：overview.indices 为空时显示"指数数据未初始化"+ 跳转数据管理页按钮（AC-08）

#### 8. IndexOverviewCards.tsx — 总览卡片网格

- 响应式网格 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- 每张卡片：指数名称 / 收盘价 / 涨跌幅（getChangeColor 红绿）/ 成交额（formatAmount）/ PE（formatPe 或"暂无估值"）
- ETF 资金跳转按钮：`<Link href={`/dashboard/etf-monitor?index_code=${tsCode}`}>ETF 资金 ▸</Link>`（AC-05）
- 个别卡片数据错误时独立显示"数据获取失败"（AC-13）

#### 9. IndexTrendChart.tsx — ECharts 走势对比

- 多选指数（从 watchlist 选择，最少1最多6只）
- 归一化开关（基准日=100）
- ECharts line chart，双轴（量级不同可分别对比）
- SWR 调 `indexMonitorApi.getTrend(tsCodes, start, end)`

#### 10. IndexValuationChart.tsx — ECharts 估值水位

- 单选指数
- 指标：市盈率TTM / 市净率 时间序列
- 前端计算分位：对返回 peTtm 序列排序，当前值百分位（AC-03）
- 无估值指数：hasData=false 时显示"该指数暂无估值数据"（AC-03 异常分支）
- SWR 调 `indexMonitorApi.getValuation(tsCode)`

#### 11. IndexWeightTable.tsx — 成分权重表

- 单选指数 + top_n 选择器（10/20/30）
- 表格：排名 / 成分股名称 / 权重% / 个股分析跳转
- 集中度：前5合计 / 前10合计
- 成分股点击跳转 `/dashboard/stock-analysis/[conCode]`（AC-06）
- SWR 调 `indexMonitorApi.getWeights(indexCode, topN)`

#### 12. IndexSyncPanel.tsx — 数据管理页指数Tab

范式对齐 `web/src/components/admin/EtfSyncPanel.tsx`。

**三同步卡片**（含 isAnySyncRunning 互斥锁）：
- 卡片1 清单同步：`adminApi.initIndexBasic()` → useTaskStatus 轮询
- 卡片2 历史回填：日期选择器 + `adminApi.initIndexHistory(start, end)`
- 卡片3 当日采集：`adminApi.initIndexDaily()`
- 互斥：`const isAnySyncRunning = basicLoading || historyLoading || dailyLoading`，所有按钮 disabled={isAnySyncRunning}（AC-08c）
- 进度：useTaskStatus onProgress 回调更新进度条（AC-08c）
- 失败：onFailed 显示错误 + 重试按钮（AC-08d）

**关注管理区**：
- 搜索框 + checkbox 列表（全量 index_basic）
- 保存按钮 → `indexMonitorApi.updateWatchlist(selectedCodes)`（AC-07）
- 前置依赖：清单未同步时关注管理区禁用 + 提示"请先同步指数清单"

**同步记录表**：
- SWR 拉 `/admin/tasks?task_types=sync_index_basic,backfill_index_history,sync_index_daily`
- 列：时间 / 操作中文 / 状态徽章 / 详情

**useTaskStatus 调用细节**：
```typescript
import { useTaskStatus } from '@/hooks/useTaskStatus'
const { task, isPolling } = useTaskStatus(taskId, {
  enabled: !!taskId, pollInterval: 2000,
  onProgress: (t) => setProgress(t.progress || 0),
  onComplete: (t) => { setLoading(false); refetchRecords(); },
  onFailed: (t) => { setLoading(false); setError(t.errorMessage); },
})
```

#### 13. 数据管理页 Tab（data/page.tsx）

Tab 枚举加 `'index-data'`：
```typescript
type DataTab = 'data-status' | 'init' | 'ma-calc' | 'strength-calc' | 'broker-recommend' | 'index-data'
```
Tab 按钮加 `<button data-testid="tab-index-data" ...>指数数据</button>`
内容区加 `{activeTab === 'index-data' && <IndexSyncPanel />}`

#### 14. TaskMonitorPanel 中文映射（TaskMonitorPanel.tsx）

在 TaskRow 的 JSX `&&` 链（L197-202）补：
```tsx
{task.taskType === 'sync_index_basic' && '同步指数清单'}
{task.taskType === 'backfill_index_history' && '回填指数历史'}
{task.taskType === 'sync_index_daily' && '采集指数当日'}
```

#### 15. ETF 跳转 useSearchParams（EtfMonitorPage.tsx）

```typescript
import { useSearchParams } from 'next/navigation'
const searchParams = useSearchParams()
const indexCode = searchParams.get('index_code')
// 如有 indexCode，自动展开对应指数详情
```
注意：Next.js 需在 Client Component 内用 useSearchParams，如 build 报 Suspense 警告则用 `<Suspense>` 包裹。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|------|------|------|------|
| 1 | collector 加步骤 9 _update_index_daily | backend | done | try/except 不中断 |
| 2 | job_manager 加指数日更 job（注释停用） | backend | done | 仿 etf_daily_snapshot |
| 3 | 创建 indexMonitorTypes.ts | frontend | done | TS 类型 |
| 4 | api.ts 加 indexMonitorApi + admin + TaskType | frontend | done | 6查询+3admin+3常量 |
| 5 | 创建 helpers.ts | frontend | done | 颜色/格式化 |
| 6 | 创建 IndexMonitorPage.tsx | frontend | done | 面板容器+空状态 |
| 7 | 创建 IndexOverviewCards.tsx | frontend | done | 卡片网格+ETF跳转 |
| 8 | 创建 IndexTrendChart.tsx | frontend | done | ECharts 走势+归一化 |
| 9 | 创建 IndexValuationChart.tsx | frontend | done | ECharts 估值+分位 |
| 10 | 创建 IndexWeightTable.tsx | frontend | done | 权重表+集中度+跳转 |
| 11 | 创建 IndexSyncPanel.tsx | frontend | done | 同步+关注管理+记录 |
| 12 | 改造 dashboard/page.tsx | frontend | done | is_admin 条件渲染 |
| 13 | 改造 data/page.tsx 加指数Tab | frontend | done | Tab枚举+渲染 |
| 14 | 补 TaskMonitorPanel 中文映射 | frontend | done | 3个task_type |
| 15 | 补 EtfMonitorPage useSearchParams | frontend | done | 读index_code |
| 16 | pnpm type-check + build | frontend | done | 类型+构建通过 |

## 验收标准

### 总览验收（AC-01）

- [ ] AC-01 管理员登录主页 → 看到 ≥14 只指数总览卡片网格
- [ ] AC-01 涨跌幅红涨绿跌，成交额亿元，有估值展示 PE 无估值显示"暂无估值"
- [ ] AC-08 数据未同步时主页显示空状态+跳转入口
- [ ] AC-13 某指数失败时该卡片独立错误态，其余正常

### 走势验收（AC-02）

- [ ] AC-02 选择多只指数后图表展示走势，归一化可切换

### 估值验收（AC-03）

- [ ] AC-03 有估值指数展示 PE/PB 曲线+分位标注
- [ ] AC-03 无估值指数显示"该指数暂无估值数据"

### 权重验收（AC-04）

- [ ] AC-04 权重表展示前N成分股+集中度
- [ ] AC-06 点击成分股跳转个股分析页

### ETF 跳转验收（AC-05）

- [ ] AC-05 点击卡片"ETF资金"跳转 etf-monitor 页且自动按指数筛选（useSearchParams 生效）

### 关注管理验收（AC-07）

- [ ] AC-07 数据管理页指数Tab→关注管理区增减指数→保存→主页同步更新

### 同步验收（AC-08c/08d）

- [ ] AC-08c 同步任务运行时其他按钮禁用+进度展示
- [ ] AC-08d 同步失败时显示错误+可重试

### 日更验收（AC-10）

- [ ] AC-10 collector run_daily_update 含步骤9，交易日执行后数据更新（查日志 index_daily_updated > 0）

### 权限验收（AC-11）

- [ ] AC-11 非管理员登录主页不展示指数面板（看原有通用内容）

### 降级验收（AC-12）

- [ ] AC-12 非交易日/未更新时卡片显示最近交易日+角标注日期

### 构建验收

- [ ] `pnpm type-check` 通过
- [ ] `pnpm build` 通过

### 全流程验收（US 覆盖矩阵）

> 架构文档引用 PRD 用户故事 US-01~US-10

| US | 简述 | 承接 | 验证 |
|----|------|------|------|
| US-01 | 主页看指数行情 | plan-04 #7 | AC-01 |
| US-02 | 多指数走势对比 | plan-04 #8 | AC-02 |
| US-03 | PE/PB 分位 | plan-04 #9 | AC-03 |
| US-04 | ETF 资金跳转 | plan-04 #7,#15 | AC-05 |
| US-05 | 成分权重 | plan-04 #10 | AC-04 |
| US-06 | 增减关注指数 | plan-04 #11 | AC-07 |
| US-07 | 自动更新 | plan-04 #1 | AC-10 |
| US-08 | 成分股跳转 | plan-04 #10 | AC-06 |

## 验证命令

```bash
cd web

# 类型检查
pnpm type-check

# 构建
pnpm build

# 启动开发服务器手动验证
pnpm dev
# → 管理员登录 /dashboard → 看指数面板
# → /dashboard/admin/data → 指数数据Tab → 同步/关注管理
# → 非管理员登录 /dashboard → 原有内容
```

后端日更验证：
```bash
cd server && source ../.venv/bin/activate
python -c "
import asyncio
from src.services.data_updater.collector import DataCollector
c = DataCollector()
result = asyncio.run(c.run_daily_update())
print(result.get('index_daily_updated'))
"
```

## 交接上下文

- **架构章节**: §3.1（主流程）、§6.4（主页查询链路）、§4.2（模块职责）、§9 Phase C
- **相关代码**: `web/src/components/admin/EtfSyncPanel.tsx`（同步面板锚点）、`web/src/app/dashboard/admin/data/page.tsx`（Tab 页锚点）、`server/src/services/data_updater/collector.py`（日更锚点）
- **契约/数据对象**: indexMonitorApi 全部方法（见实现规格 #4）、useTaskStatus 接口
- **下游消费方**: 无（最终集成功能）

## 风险与边界

- **执行顺序**: 后端先（Task 1-2），前端组件先创建再接线（Task 3-11 → 12-15），最后构建验证（Task 16）
- **验证失败排查方向**: type-check 错误检查类型定义与 API 响应是否匹配；build 错误检查 Next.js 动态导入/useSearchParams Suspense；ECharts 不渲染检查 SWR 数据是否正确解包
- **允许修改的额外文件**: auth context（如需确认 is_admin 获取方式）
- **暂停条件**: is_admin 获取方式不明确时暂停确认（检查现有 auth context 实现）
- **响应解包确认**：apiClient.get 返回的 response，外层 `{success, data}` 由 AdminApiClient.request 自动剥壳（adminApi），但 indexMonitorApi 走 apiClient 需确认解包层级——泛型写 `{success, data}` 时组件消费 `res.data`（即内层 data）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|------|---------|------|
| 日更步骤9 失败 | try/except 记 error，不中断主流程 | todo |
| 非交易日执行 | collector 交易日守卫在步骤1已拦截，步骤9不执行 | todo |

### 前端边界场景

| 场景 | 处理方式 | 状态 |
|------|---------|------|
| overview 数据为空 | 空状态组件+跳转数据管理入口 | todo |
| 估值无数据 | 估值区显示"暂无估值数据" | todo |
| 权重成分股无名称 | 显示 con_code | todo |
| 同步任务运行中 | 所有同步按钮禁用+进度展示 | todo |
| useSearchParams build 警告 | Suspense 包裹 | todo |
| 非管理员访问主页 | is_admin=false 渲染原有内容 | todo |
