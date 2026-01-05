# Tech-Spec: 板块分析图表功能

**创建日期:** 2025-01-01
**状态:** ✅ 已完成
**优先级:** 中
**实际工作量:** 1 天
**完成日期:** 2025-01-01

---

## 概述

### 问题陈述

当前系统在"强度分析"页面点击板块后只能显示 alert 弹窗，无法查看板块的历史趋势和均线数据。用户需要更直观的方式分析板块的强度变化和均线走势。

### 解决方案

1. 创建独立的"板块分析"页面，显示该板块的强度历史曲线图和多均线曲线图
2. 在强度分析页面点击板块后跳转到板块分析页面
3. 左右分栏布局展示两个图表
4. 支持时间范围选择和均线显示/隐藏控制

### 范围

**包含:**
- 板块强度历史曲线图（可调整时间范围，默认 2 个月）
- 多均线曲线图（MA5/10/20/30/60/120/240，可通过多选框控制）
- 均线图叠加当前价格曲线（虚线样式）
- 图表交互：鼠标悬停显示详细数值、Y 轴缩放
- 均线金叉/死叉标记（MA5/10/20/30/60 交叉信号）
- 板块分析页面路由 `/dashboard/sector-analysis/[sectorId]`
- 导航菜单新增"板块分析"入口
- 后端 API: 获取板块强度历史数据和均线数据

**不包含（未来迭代）:**
- 实时数据更新（手动刷新）
- 数据/图表导出功能
- 成交量柱状图叠加
- 重大事件标注（如政策变化）
- 个股的均线图表（仅板块）
- 移动端深度优化（仅响应式适配）

---

## 开发上下文

### 代码库模式

**前端架构:**
- **框架:** Next.js 14 (App Router) + TypeScript
- **图表库:** ECharts + echarts-for-react
- **UI 组件:** shadcn/ui + Tailwind CSS
- **数据获取:** 自定义 hooks + SWR
- **路由:** 文件系统路由 (`/dashboard/sector-analysis/[sectorId]`)

**后端架构:**
- **框架:** FastAPI + Python 3.11+
- **数据库:** PostgreSQL 14+
- **ORM:** SQLAlchemy

### 需要引用的文件

**前端参考:**
- `web/src/components/dashboard/SectorHeatmap.tsx` - ECharts 使用模式
- `web/src/components/dashboard/MarketIndexDisplay.tsx` - 折线图配置
- `web/src/app/dashboard/analysis/page.tsx` - 板块点击处理
- `web/src/components/dashboard/DashboardLayout.tsx` - 菜单配置
- `web/src/hooks/useSectorHeatmapData.ts` - Hook 模式

**后端参考:**
- `server/src/routers/sector.py` - 现有板块 API
- `server/src/models/strength_score.py` - StrengthScore 模型定义（强度数据）
- `server/src/models/moving_average_data.py` - MovingAverageData 模型定义（均线数据）
- `docs/database-schema-ma-system.md` - 数据库表结构

### 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 图表库 | ECharts | 已在项目中使用，功能强大，支持交互 |
| 路由方式 | 动态路由 `[sectorId]` | 符合 Next.js 最佳实践，SEO 友好 |
| 数据获取 | 自定义 Hook + SWR | 与现有模式一致，自动缓存和重验证 |
| 状态管理 | Zustand store | 管理多图表状态同步，避免 prop drilling |
| 时间范围选择 | 按钮组（预设选项） | 更直观，与现有板块类型选择器一致 |
| 均线控制 | 多选框组 | 简单清晰的交互方式 |
| 布局 | 左右分栏（各 50%） | 充分利用宽屏空间，方便对比 |
| 金叉显示 | MVP 仅 MA5×20 | 避免视觉混乱，后续可配置扩展 |
| 色彩区分 | 颜色为主，线型为辅（P2） | 平衡可访问性和实现复杂度 |

---

## 实现计划

### 任务列表

- [x] **Task 1: 后端 API 开发**
  - [x] 1.1 创建 GET `/api/v1/sectors/{sector_id}/strength-history` 端点（从 `strength_scores` 表查询）
  - [x] 1.2 创建 GET `/api/v1/sectors/{sector_id}/ma-history` 端点（从 `moving_average_data` 表查询，JOIN `strength_scores` 获取价格）
  - [x] 1.3 添加时间范围参数验证（start_date, end_date）
  - [x] 1.4 添加单元测试

- [x] **Task 2: 前端数据层**
  - [x] 2.1 创建 `useSectorStrengthHistory` Hook
  - [x] 2.2 创建 `useSectorMAHistory` Hook
  - [x] 2.3 定义 TypeScript 类型
  - [x] 2.4 创建 `useChartState` Zustand store（管理时间范围、均线显示状态）

- [x] **Task 3: 图表组件**
  - [x] 3.1 创建 `SectorStrengthChart` 组件（强度曲线 + tooltip）
  - [x] 3.2 创建 `SectorMAChart` 组件（均线 + 价格曲线 + 金叉死叉标记 + tooltip）
  - [x] 3.3 添加时间范围按钮组（1周/1月/2月/3月/6月/1年）
  - [x] 3.4 添加均线多选框控制（支持 MA5/10/20/30/60/90/120/240，动态检测数据可用性）
  - [x] 3.5 实现优化的金叉检测算法（MVP 仅 MA5×20，单次遍历）
  - [x] 3.6 添加金叉辅助线（贯穿整个图表的垂直线）
  - [x] 3.7 Y 轴缩放功能（P1，dataZoom 组件）

- [x] **Task 4: 页面集成**
  - [x] 4.1 创建 `/dashboard/sector-analysis/[sectorId]/page.tsx`
  - [x] 4.2 修改强度分析页面的点击处理（跳转而非 alert）
  - [x] 4.3 添加导航菜单"板块分析"入口
  - [x] 4.4 添加面包屑导航

- [x] **Task 5: 测试和优化**
  - [x] 5.1 前端组件单元测试
  - [x] 5.2 E2E 测试（关键流程）
  - [x] 5.3 性能优化（数据缓存、图表渲染）
  - [x] 5.4 响应式适配

### 验收标准

- [x] **AC 1:** Given 用户在强度分析页面点击某个板块，When 点击发生，Then 跳转到 `/dashboard/sector-analysis/{sectorId}` 页面
- [x] **AC 2:** Given 用户访问板块分析页面，When 页面加载，Then 左侧显示板块强度历史曲线图，右侧显示多均线曲线图
- [x] **AC 3:** Given 用户在板块分析页面，When 页面加载，Then 时间范围默认显示最近 2 个月数据
- [x] **AC 4:** Given 用户选择不同时间范围，When 选择改变，Then 两个图表同时更新为选定时间范围的数据
- [x] **AC 5:** Given 用户在均线图表区域，When 取消勾选某个均线（如 MA10），Then 该均线从图表中消失
- [x] **AC 6:** Given 用户访问板块分析页面，When 数据加载失败，Then 显示友好的错误提示和重试按钮
- [x] **AC 7:** Given 导航菜单，When 用户查看菜单，Then 显示"板块分析"菜单项
- [x] **AC 8:** Given 用户鼠标悬停在图表上，When 悬停发生，Then 显示该日期的详细数值（日期、强度/均线值、价格）
- [x] **AC 9:** Given 用户查看均线图，When 图表加载，Then 叠加显示当前价格曲线（虚线样式，灰色）
- [x] **AC 10:** Given 用户选择时间范围，When 查看时间范围控制器，Then 显示 6 个按钮（1周/1月/2月/3月/6月/1年）
- [x] **AC 11:** Given 用户查看均线图，When MA5 上穿 MA20，Then 显示金叉标记（向上三角图标 + 垂直辅助线）
- [x] **AC 12:** Given 用户查看均线图，When MA5 下穿 MA20，Then 显示死叉标记（向下三角图标 + 垂直辅助线）
- [x] **AC 13:** (P1) Given 用户在图表区域使用鼠标滚轮，When 滚动发生，Then Y 轴缩放以查看细节
- [x] **AC 14:** Given 用户查看均线复选框，When MA90/MA120/MA240 数据不足，Then 对应复选框显示为禁用状态
- [x] **AC 15:** Given 用户切换时间范围，When 选择改变，Then 两个图表同时更新（通过 Zustand store 同步）

---

## 额外上下文

### 数据库查询

**强度历史数据查询:**
```sql
SELECT date, score, current_price
FROM strength_scores
WHERE entity_type = 'sector'
  AND entity_id = :sector_id
  AND period = 'all'
  AND date BETWEEN :start_date AND :end_date
ORDER BY date ASC;
```

**均线历史数据查询:**
```sql
SELECT
    date,
    current_price,
    MAX(CASE WHEN period = '5d' THEN ma_value END) AS ma5,
    MAX(CASE WHEN period = '10d' THEN ma_value END) AS ma10,
    MAX(CASE WHEN period = '20d' THEN ma_value END) AS ma20,
    MAX(CASE WHEN period = '30d' THEN ma_value END) AS ma30,
    MAX(CASE WHEN period = '60d' THEN ma_value END) AS ma60,
    MAX(CASE WHEN period = '120d' THEN ma_value END) AS ma120,
    MAX(CASE WHEN period = '240d' THEN ma_value END) AS ma240
FROM (
    SELECT
        mad.date,
        mad.period,
        mad.ma_value,
        ss.current_price
    FROM moving_average_data mad
    LEFT JOIN strength_scores ss
        ON ss.entity_type = mad.entity_type
        AND ss.entity_id = mad.entity_id
        AND ss.date = mad.date
        AND ss.period = 'all'
    WHERE mad.entity_type = 'sector'
      AND mad.entity_id = :sector_id
      AND mad.period IN ('5d', '10d', '20d', '30d', '60d', '120d', '240d')
      AND mad.date BETWEEN :start_date AND :end_date
) AS ma_data
GROUP BY date, current_price
ORDER BY date ASC;
```

### API 规范

**获取板块强度历史:**
```
GET /api/v1/sectors/{sector_id}/strength-history

Query Parameters:
  - start_date: string (ISO 8601 date, optional, default: 2 months ago)
  - end_date: string (ISO 8601 date, optional, default: today)

Response:
{
  "sector_id": "string",
  "sector_name": "string",
  "data": [
    {
      "date": "2024-12-01",
      "score": 65.5,
      "current_price": 1234.56
    }
  ]
}
```

**获取板块均线历史:**
```
GET /api/v1/sectors/{sector_id}/ma-history

Query Parameters:
  - start_date: string (ISO 8601 date, optional)
  - end_date: string (ISO 8601 date, optional)

Response:
{
  "sector_id": "string",
  "sector_name": "string",
  "data": [
    {
      "date": "2024-12-01",
      "current_price": 1235.00,
      "ma5": 1200.00,
      "ma10": 1210.00,
      "ma20": 1220.00,
      "ma30": 1230.00,
      "ma60": 1240.00,
      "ma120": 1250.00,
      "ma240": 1260.00
    }
  ]
}
```

### 时间范围预设

| 选项 | 范围 |
|------|------|
| 1 周 | 7 天前至今 |
| 1 个月 | 30 天前至今 |
| 2 个月 | 60 天前至今（默认） |
| 3 个月 | 90 天前至今 |
| 6 个月 | 180 天前至今 |
| 1 年 | 365 天前至今 |

### 均线颜色配置

| 均线 | 颜色 | 线型 | 默认显示 |
|------|------|------|----------|
| 当前价格 | #9CA3AF (灰) | 虚线 (2px) | ✅ |
| MA5 | #EF4444 (红) | 实线 | ✅ |
| MA10 | #F59E0B (橙) | 实线 | ✅ |
| MA20 | #FBBF24 (黄) | 实线 | ✅ |
| MA30 | #10B981 (绿) | 实线 | ✅ |
| MA60 | #3B82F6 (蓝) | 实线 | ✅ |
| MA120 | #8B5CF6 (紫) | 实线 | ❌ |
| MA240 | #EC4899 (粉) | 实线 | ❌ |

### 金叉/死叉检测逻辑

**定义:**
- **金叉 (Golden Cross):** 短期均线上穿长期均线（看涨信号）
- **死叉 (Death Cross):** 短期均线下穿长期均线（看跌信号）

**MVP 范围:**
- **仅检测 MA5 × MA20 交叉**（最重要且最常用的信号）
- 未来迭代可扩展支持：MA10×20、MA20×60

**算法实现（优化版 - 单次遍历）:**
```typescript
// 同时检测金叉和死叉，单次遍历
function detectCrossesOptimized(data: MAPoint[]): CrossPoint[] {
  const crosses: CrossPoint[] = []

  for (let i = 1; i < data.length; i++) {
    const ma5_prev = data[i - 1].ma5
    const ma20_prev = data[i - 1].ma20
    const ma5_curr = data[i].ma5
    const ma20_curr = data[i].ma20

    // 处理 null/undefined 值
    if (!ma5_prev || !ma20_prev || !ma5_curr || !ma20_curr) continue

    // 检测金叉: 昨日 MA5 < MA20，今日 MA5 > MA20
    if (ma5_prev < ma20_prev && ma5_curr > ma20_curr) {
      crosses.push({
        date: data[i].date,
        type: 'golden',
        value: ma5_curr
      })
    }

    // 检测死叉: 昨日 MA5 > MA20，今日 MA5 < MA20
    if (ma5_prev > ma20_prev && ma5_curr < ma20_curr) {
      crosses.push({
        date: data[i].date,
        type: 'death',
        value: ma5_curr
      })
    }
  }

  return crosses
}
```

**图表标记展示:**
- **三角形标记:** 金叉绿色向上 (▲)，死叉红色向下 (▼)
- **尺寸:** 15-18px（比默认更大以提高可见性）
- **垂直辅助线:** 从交叉点贯穿整个图表高度，方便对齐
- **Tooltip:** 显示"金叉: MA5 上穿 MA20"等描述
- **markLine 配置:**
```typescript
{
  markLine: {
    symbol: ['none', 'none'],  // 不显示箭头
    label: { show: false },
    lineStyle: { type: 'dashed', width: 1 },
    data: crosses.map(c => ({
      xAxis: c.date,
      lineStyle: { color: c.type === 'golden' ? '#10B981' : '#EF4444' }
    }))
  }
}
```

### 依赖项

**前端需要安装的包:**
- 无需新安装（ECharts 已存在）

**后端需要安装的包:**
- 无需新安装

### 测试策略

**前端测试:**
- 组件单元测试：验证图表渲染、交互逻辑
- Hook 测试：验证数据获取、缓存逻辑
- E2E 测试：验证完整用户流程

**后端测试:**
- API 单元测试：验证端点响应、错误处理
- 集成测试：验证数据库查询

### 注意事项

1. **性能优化:**
   - 使用 SWR 缓存数据，减少重复请求
   - 图表使用 `opts={{ renderer: 'canvas' }}` 优化渲染性能
   - 大量数据时考虑数据抽样或分页加载
   - 金叉检测使用单次遍历算法（O(n) 复杂度）

2. **交互功能实现:**
   - **Tooltip:** 使用 ECharts `tooltip` 配置，trigger: 'axis'，显示所有系列数据
   - **Y 轴缩放:** (P1) 启用 `dataZoom` 组件，type: 'inside'，支持鼠标滚轮缩放
   - **金叉/死叉标记:** 使用 `markPoint` + `markLine` 组合（标记点 + 垂直辅助线）
   - **均线显示控制:** 使用 `legend.selected` 控制系列的显示/隐藏状态
   - **时间范围同步:** 通过 Zustand store 确保两个图表的时间范围一致

3. **错误处理:**
   - API 失败时显示友好提示和重试按钮
   - 数据为空时显示"暂无数据"状态
   - 参数验证失败时返回 400 错误
   - 金叉检测时处理 null/undefined 均线值

4. **数据完整性处理:**
   - **MA120/MA240 检测:** 前端检查数据长度，不足 120/240 天时禁用对应复选框
   - **均线数据连续性:** 处理缺失数据点，避免图表渲染异常
   - **API 响应验证:** 验证返回数据的完整性和格式

5. **响应式设计:**
   - **桌面端 (≥1440px):** 左右分栏（各 50%）
   - **标准桌面 (1366-1439px):** 左右分栏，最小宽度 600px/图表
   - **平板 (768-1023px):** 上下堆叠，每个图表高度 400px
   - **移动端 (<768px):** 上下堆叠，图表高度 300px
   - **建议:** 在小屏幕上显示提示"建议使用更大屏幕查看完整图表"

6. **无障碍性:**
   - 图表添加 aria-label
   - 时间范围按钮使用语义化标签
   - 颜色搭配考虑色盲用户
   - 金叉/死叉标记提供文字描述
   - **P2 增强:** 为不同均线添加线型区分（实线/虚线/点线）

---

## 附录

### 相关文件

| 文件路径 | 说明 |
|---------|------|
| `docs/stories/4-4.market-index.md` | 市场指数功能实现参考 |
| `docs/ma-system-strength-indicator-v2.md` | MA 系统设计文档 |
| `docs/database-schema-ma-system.md` | 数据库表结构 |

### 相关 Epic/Story

- Epic 4: 界面开发
- Story 4-2: 板块热力图
- Story 4-3: 排名列表
- Story 4-4: 市场指数

---

*文档生成时间: 2025-01-01*
*最后更新: 2025-01-01 (User Persona Focus Group + Cross-Functional War Room 增强)*
