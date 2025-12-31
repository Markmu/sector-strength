# Tech-Spec: 板块强度分析散点图页面

**Created:** 2025-12-29
**Status:** Ready for Development
**Author:** Barry (Quick Flow Solo Dev)

---

## Overview

### Problem Statement

当前系统已有完整的板块强度计算和排名功能，但缺少直观的**多维度强度分析视图**。用户需要：
- 同时观察多个维度的强度指标（短期、中期、长期）
- 快速识别不同强度特征的板块（如"强势持续"、"反弹机会"等）
- 通过交互式图表进行深度分析

### Solution

创建一个**独立的板块强度分析页面**，使用**散点图**展示各板块在多维强度空间中的分布。

**散点图设计:**
- **X轴:** 短期强度 (short_term_score) - 反映近期走势
- **Y轴:** 中期强度 (medium_term_score) - 反映中期趋势
- **气泡大小:** 强势股占比 (strong_stock_ratio) - 板块内部强度分布
- **气泡颜色:** 长期强度 (long_term_score) - 使用热力色谱（绿=强，红=弱）
- **气泡形状:** 行业板块=圆形，概念板块=菱形（视觉区分类型）

**交互功能:**
- 悬停显示完整板块信息和强度详情
- 点击气泡跳转到板块详情页
- 筛选器：板块类型（行业/概念/全部）、强度等级滑块筛选
- 切换维度：可选择不同的X/Y轴组合
- 缩放和平移：支持大数据量场景的手动缩放和拖拽

**时间对比功能（Phase 2）:**
- 支持对比两个时点的数据（今天 vs 历史日期）
- 双层数据显示：旧数据半透明背景，新数据实心前景
- 移动箭头连线显示板块移动方向和距离

### Scope (In/Out)

**包含:**
- 散点图可视化组件（基于 ECharts）
- 行业/概念板块视觉区分（不同符号形状）
- 板块强度数据聚合 API
- 独立分析页面路由 (`/dashboard/analysis`)
- 交互控制面板（类型筛选、维度切换、强度等级滑块）
- 大规模数据支持（缩放、平移、分页）
- 数据缺失处理（默认值策略、完整性指示）
- 响应式设计（桌面端优先，移动端优化）
- **Phase 2:** 时间对比功能（双层数据、移动箭头）

**不包含:**
- 个股散点图分析（未来扩展）
- 导出图表功能（Phase 3）
- 实时数据推送（使用现有的 SWR 轮询）
- 配置持久化（用户偏好保存，Phase 3）

---

## Context for Development

### Codebase Patterns

#### 后端架构
- **异步模式:** 所有数据库操作使用 `AsyncSession` + `select()` + `await session.execute()`
- **服务层:** 业务逻辑放在 `server/src/services/` 下
- **响应模式:** 使用 Pydantic Schema 定义响应，遵循 `{ success: true, data: {...} }` 格式
- **错误处理:** 使用 `src/api/exceptions.py` 中的自定义异常类

#### 前端架构
- **路由:** App Router (Next.js 16) - `app/` 目录结构
- **组件:** 函数组件 + React Hooks + TypeScript
- **数据获取:** SWR (`useSWR`, `useSWRConfig`)
- **样式:** TailwindCSS + 自定义 UI 组件
- **图表:** ECharts + `echarts-for-react`

#### 数据模型参考
```python
# server/src/models/strength_score.py:10-45
class StrengthScore(Base):
    # 核心强度字段
    score: Numeric(10, 4)              # 综合强度得分
    short_term_score: Numeric(10, 2)   # 短期强度
    medium_term_score: Numeric(10, 2)  # 中期强度
    long_term_score: Numeric(10, 2)    # 长期强度

    # 板块特有字段
    strong_stock_ratio: Numeric(5, 4)  # 强势股占比
```

### Files to Reference

**后端:**
- `server/src/api/v1/sectors.py` - 现有板块 API 结构
- `server/src/api/schemas/strength.py` - 强度数据 Schema
- `server/src/services/strength_service_v2.py` - 强度计算服务

**前端:**
- `web/src/lib/api.ts` - API 客户端定义
- `web/src/components/dashboard/SectorHeatmap.tsx` - 图表组件参考
- `web/src/app/dashboard/page.tsx` - Dashboard 页面结构
- `web/src/hooks/useSectorRanking.ts` - 数据获取 Hook 模式

**类型定义:**
- `web/src/lib/ranking/types.ts` - 现有类型定义参考

### Technical Decisions

1. **散点图库选择:** 继续使用 **ECharts**（已安装）
   - 优势：与现有热力图一致、功能丰富、性能好
   - 替代方案：Recharts（更轻量但功能较少）、D3.js（太底层）

2. **数据聚合策略:** 后端提供专用聚合端点
   - 前端一次性获取所有板块的散点图数据
   - 避免多次 API 调用导致的 N+1 问题

3. **维度切换设计:** 使用配置化映射
   ```typescript
   const AXIS_CONFIG = {
     short: { field: 'short_term_score', label: '短期强度' },
     medium: { field: 'medium_term_score', label: '中期强度' },
     long: { field: 'long_term_score', label: '长期强度' },
     composite: { field: 'score', label: '综合强度' }
   }
   ```

4. **响应式处理:**
   - 桌面端：固定高度容器 + 宽度自适应
   - 移动端：简化交互（禁用 tooltip 以外的交互）

5. **板块类型视觉区分:**
   - 行业板块：圆形符号 (`symbol: 'circle'`)
   - 概念板块：菱形符号 (`symbol: 'diamond'`)
   - 图例显示在右上角，支持点击快速筛选

6. **大数据量处理:**
   - ECharts `dataZoom` 组件：缩放和平移
   - 后端分页：`offset/limit` 参数（默认 limit=200）
   - 超过 500 个板块时启用智能采样

7. **数据缺失处理策略:**
   - `strong_stock_ratio` 为 null：使用固定中等大小 (symbolSize=20)
   - `long_term_score` 为 null：使用中性灰色 (#94a3b8)
   - 返回 `data_completeness` 字段指示数据完整度
   - 前端显示不完整数据的特殊标记

---

## Implementation Plan

### Tasks

#### Phase 1: 后端 API 开发

- [ ] **Task 1.1: 创建散点图数据聚合 Schema**
  - 文件: `server/src/api/schemas/strength.py`
  - 添加 `SectorScatterData` 和 `SectorScatterResponse` 类型
  - 包含字段：symbol, name, sector_type, x, y, size (strong_stock_ratio), color_value (long_term_score), data_completeness, full_data

- [ ] **Task 1.2: 实现数据聚合 Service**
  - 文件: `server/src/services/strength_scatter_service.py` (新建)
  - 实现 `get_scatter_data()` 方法
  - 支持筛选：sector_type, strength_grade_range, compare_date (Phase 2)
  - 支持分页：offset, limit（默认 limit=200）
  - 从 `strength_scores` 表联查 `sectors` 表获取完整数据
  - 数据缺失处理：null 值替换为默认值

- [ ] **Task 1.3: 添加 API 端点**
  - 文件: `server/src/api/v1/analysis.py` (新建)
  - 路由: `GET /api/v1/analysis/sector-scatter`
  - 查询参数: `sector_type`, `min_grade`, `max_grade`, `x_axis`, `y_axis`, `offset`, `limit`, `compare_date` (Phase 2)
  - 返回: `SectorScatterResponse`

#### Phase 2: 前端页面开发

- [ ] **Task 2.1: 创建散点图组件**
  - 文件: `web/src/components/analysis/SectorScatterPlot.tsx` (新建)
  - 使用 `echarts-for-react` 实现
  - 配置散点图：symbolSize 基于 data.size，visualMap 基于 data.color_value
  - 行业板块使用圆形，概念板块使用菱形
  - 添加 dataZoom 组件（缩放和平移）
  - 实现 tooltip 格式化显示（包含数据完整度指示）
  - 实现 click 事件处理（跳转到板块详情）
  - **Phase 2:** 支持双层数据显示（旧数据半透明背景）

- [ ] **Task 2.2: 创建控制面板组件**
  - 文件: `web/src/components/analysis/AnalysisControls.tsx` (新建)
  - 板块类型切换器（行业/概念/全部）- 图标 + 标签
  - 维度选择器（X轴/Y轴下拉选择）
  - 强度等级滑块筛选（双滑块：min ~ max）
  - **Phase 2:** 日期对比选择器

- [ ] **Task 2.3: 创建数据获取 Hook**
  - 文件: `web/src/hooks/useSectorScatterData.ts` (新建)
  - 使用 SWR 获取散点图数据
  - 支持参数变化时的自动重新获取
  - 支持分页加载（加载更多按钮）
  - 错误处理和加载状态
  - **Phase 2:** 支持对比日期参数

- [ ] **Task 2.4: 创建分析页面**
  - 文件: `web/src/app/dashboard/analysis/page.tsx` (新建)
  - 布局：Header + 控制面板 + 散点图 + 图例
  - 集成 SWR 的 mutate 刷新功能
  - 响应式样式（移动端简化）
  - 添加板块类型图例（右上角，可点击筛选）

#### Phase 3: 集成和优化

- [ ] **Task 3.1: 添加导航链接**
  - 在 Sidebar 添加"强度分析"入口
  - 路由: `/dashboard/analysis`

- [ ] **Task 3.2: 性能优化**
  - 后端：添加 Redis 缓存（5 分钟 TTL）
  - 后端：添加查询响应头 `X-Cache-Status`
  - 前端：支持分页加载（offset/limit 参数）
  - ECharts 配置：关闭动画以提升大数据量渲染性能
  - **Phase 2:** 预计算机制（每次数据更新后预先聚合）

- [ ] **Task 3.3: 数据缺失处理**
  - 后端：null 值替换为默认值的逻辑
  - 前端：不完整数据的视觉标记（虚线边框）
  - 前端：空状态占位符组件

- [ ] **Task 3.4: 测试**
  - 单元测试：Service 层数据聚合逻辑
  - 单元测试：数据缺失处理逻辑
  - 集成测试：API 端点响应格式
  - 集成测试：分页功能
  - E2E 测试：基本交互流程
  - **Phase 2:** 时间对比功能测试

#### Phase 4: 时间对比功能（可选扩展）

- [ ] **Task 4.1: 后端对比数据支持**
  - Service 支持双日期查询（calc_date + compare_date）
  - 返回两组数据用于对比显示

- [ ] **Task 4.2: 前端对比视图**
  - 双层数据系列配置（旧数据背景层，新数据前景层）
  - 移动箭头连线（markLine）显示方向和距离
  - 对比日期选择器组件

- [ ] **Task 4.3: 趋势分析**
  - 筛选出变化最大的板块（移动距离阈值）
  - 识别"趋势转折点"（强度象限变化）
  - 添加"快速变化"视图

### Acceptance Criteria

#### 基础功能 (Phase 1-3)

- [ ] **AC1:** 散点图正确显示所有板块，位置基于选定的 X/Y 维度
- [ ] **AC2:** 气泡大小反映 `strong_stock_ratio`，颜色反映长期强度
- [ ] **AC3:** 行业板块显示为圆形，概念板块显示为菱形
- [ ] **AC4:** 悬停显示板块名称、代码、各维度得分、数据完整度
- [ ] **AC5:** 点击气泡跳转到板块详情页（或触发回调）
- [ ] **AC6:** 筛选器实时生效（板块类型、强度等级），无全页面刷新
- [ ] **AC7:** 强度等级滑块筛选正常工作（双滑块范围选择）
- [ ] **AC8:** 支持缩放和平移（dataZoom 组件）
- [ ] **AC9:** 移动端可用（简化交互，图表自适应）
- [ ] **AC10:** API 响应时间 < 500ms（使用缓存）
- [ ] **AC11:** 代码通过 ESLint/Prettier 检查
- [ ] **AC12:** 数据缺失时正确显示（默认大小/颜色，不崩溃）
- [ ] **AC13:** 支持 500+ 板块流畅渲染（通过分页和采样）
- [ ] **AC14:** 图例正确显示行业/概念类型，支持点击筛选

#### 时间对比功能 (Phase 4 - 可选)

- [ ] **AC15:** 支持选择对比日期（默认 7 天前）
- [ ] **AC16:** 双层数据正确显示（旧数据半透明，新数据实心）
- [ ] **AC17:** 移动箭头连线正确显示板块移动方向和距离
- [ ] **AC18:** 对比视图下 tooltip 正确显示两个时点的数据对比
- [ ] **AC19:** "快速变化"筛选正确识别移动距离最大的板块

---

## Additional Context

### Dependencies

**后端依赖（已安装）:**
- `fastapi` - Web 框架
- `sqlalchemy` - ORM
- `pydantic` - 数据验证

**前端依赖（已安装）:**
- `echarts@^6.0.0` - 图表库
- `echarts-for-react@^3.0.5` - React 封装
- `swr@^2.3.8` - 数据获取
- `next@16.0.7` - 框架

### Testing Strategy

**后端测试:**
```python
# server/tests/api/test_analysis_api.py
async def test_get_sector_scatter_data():
    """测试散点图数据获取"""
    response = await client.get("/api/v1/analysis/sector-scatter")
    assert response.status_code == 200
    data = response.json()
    assert "scatter_data" in data["data"]
    assert len(data["data"]["scatter_data"]) > 0
```

**前端测试:**
```typescript
// web/src/components/analysis/__tests__/SectorScatterPlot.test.tsx
describe('SectorScatterPlot', () => {
  it('renders chart with data', () => {
    const mockData = [/* ... */]
    render(<SectorScatterPlot data={mockData} xAxis="short" yAxis="medium" />)
    // 验证 ECharts 实例创建
  })
})
```

### Notes

**散点图配置参考:**
```javascript
const scatterOption = {
  xAxis: {
    name: '短期强度',
    min: 0, max: 100,
    nameLocation: 'middle',
    nameGap: 30
  },
  yAxis: {
    name: '中期强度',
    min: 0, max: 100,
    nameLocation: 'middle',
    nameGap: 40
  },
  // 颜色映射：基于长期强度
  visualMap: {
    min: 0, max: 100,
    inRange: { color: ['#ef4444', '#eab308', '#22c55e'] }, // 红-黄-绿
    text: ['强', '弱'],
    dimension: 2  // color_value 索引
  },
  // 缩放和平移
  dataZoom: [
    { type: 'slider', xAxisIndex: 0, filterMode: 'none' },
    { type: 'slider', yAxisIndex: 0, filterMode: 'none' },
    { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
    { type: 'inside', yAxisIndex: 0, filterMode: 'none' }
  ],
  // 两个系列：行业板块和概念板块
  series: [
    {
      name: '行业板块',
      type: 'scatter',
      symbol: 'circle',
      symbolSize: (data) => {
        const size = data[2]  // strong_stock_ratio
        return size != null ? Math.max(size * 50, 10) : 20  // 默认 20
      },
      data: industryData,  // [x, y, size, color_value, name, ...]
      label: {
        show: true,
        formatter: '{b}',  // 板块名称
        position: 'top'
      }
    },
    {
      name: '概念板块',
      type: 'scatter',
      symbol: 'diamond',
      symbolSize: (data) => {
        const size = data[2]  // strong_stock_ratio
        return size != null ? Math.max(size * 50, 10) : 20  // 默认 20
      },
      data: conceptData,  // [x, y, size, color_value, name, ...]
      label: {
        show: true,
        formatter: '{b}',
        position: 'top'
      }
    }
  ],
  // 图例
  legend: {
    data: ['行业板块', '概念板块'],
    top: 10,
    right: 10
  }
}
```

**数据缺失处理示例:**
```python
# 后端 Service 处理
if score.strong_stock_ratio is None:
    size = 20  # 默认中等大小
else:
    size = score.strong_stock_ratio * 50

if score.long_term_score is None:
    color_value = 50  # 中性灰色对应值
else:
    color_value = score.long_term_score

data_completeness = {
    'has_strong_ratio': score.strong_stock_ratio is not None,
    'has_long_term': score.long_term_score is not None,
    'completeness_percent': calculate_percent(...)  # 0-100
}
```

**时间对比模式配置（Phase 2）:**
```javascript
// 双层数据显示
series: [
  {
    name: '历史数据',
    type: 'scatter',
    symbol: 'circle',
    itemStyle: { opacity: 0.3 },  // 半透明
    data: historicalData,
    z: 1  // 背景层
  },
  {
    name: '当前数据',
    type: 'scatter',
    symbol: 'circle',
    itemStyle: { opacity: 1.0 },  // 实心
    data: currentData,
    z: 2,  // 前景层
    // 移动箭头连线
    markLine: {
      symbol: ['none', 'arrow'],
      data: calculateMovementArrows(historicalData, currentData),
      lineStyle: { color: '#64748b', type: 'dashed' }
    }
  }
]
```

**强度等级定义（参考现有代码）:**
- S+: 90-100, S: 80-89, A+: 70-79, A: 60-69
- B+: 50-59, B: 40-49, C: 30-39, D: <30

**相关 Epic/Story:**
- Epic 10: MA 系统强度重构（已完成强度计算）
- 如需关联 PRD，参考 `docs/prd/` 目录

---

## API Contract Preview

### GET /api/v1/analysis/sector-scatter

**Query Parameters:**
```typescript
{
  sector_type?: 'industry' | 'concept' | null  // 板块类型筛选
  min_grade?: string                           // 最低等级 (如 "B")
  max_grade?: string                           // 最高等级 (如 "S+")
  x_axis?: 'short' | 'medium' | 'long' | 'composite'  // X轴维度
  y_axis?: 'short' | 'medium' | 'long' | 'composite'  // Y轴维度
  offset?: number                              // 分页偏移（默认 0）
  limit?: number                               // 每页数量（默认 200，最大 500）
  compare_date?: string                        // 对比日期 YYYY-MM-DD (Phase 2)
}
```

**Response:**
```typescript
{
  success: true,
  data: {
    scatter_data: {
      industry: Array<{
        symbol: string           // 板块代码
        name: string            // 板块名称
        sector_type: 'industry' // 板块类型
        x: number               // X轴数值
        y: number               // Y轴数值
        size: number            // 气泡大小 (strong_stock_ratio，默认20)
        color_value: number     // 颜色值 (long_term_score，默认50)
        data_completeness: {    // 数据完整度
          has_strong_ratio: boolean
          has_long_term: boolean
          completeness_percent: number  // 0-100
        }
        full_data: {            // 完整数据（tooltip 使用）
          score: number
          short_term_score: number
          medium_term_score: number
          long_term_score: number
          strong_stock_ratio: number | null
          strength_grade: string
        }
      }>,
      concept: Array<{ /* 同上，sector_type: 'concept' */ }>
    },
    total_count: number,      // 总板块数（分页前）
    returned_count: number,   // 返回的板块数
    filters_applied: {
      sector_type: string | null,
      grade_range: [string, string] | null,
      axes: [string, string],
      pagination: { offset: number, limit: number }
    },
    cache_status: 'hit' | 'miss'  // 缓存状态
  }
}
```

**Phase 2 - 对比模式响应:**
```typescript
{
  success: true,
  data: {
    scatter_data: {
      industry: [...],
      concept: [...]
    },
    comparison_data: {  // 新增：对比数据
      compare_date: string,
      industry: [...],   // 对比日期的散点数据
      concept: [...]
    },
    movement_analysis: {  // 新增：移动分析
      top_movers: Array<{
        symbol: string
        name: string
        distance: number  // 移动距离
        direction: 'up' | 'down' | 'left' | 'right' | 'diagonal'
      }>
    },
    // ... 其他字段同上
  }
}
```

---

## 工时估算

### Phase 1: 后端 API 开发
- Task 1.1: Schema 定义 ~2h
- Task 1.2: Service 实现 ~6h
- Task 1.3: API 端点 ~2h
**小计: 10h**

### Phase 2: 前端页面开发
- Task 2.1: 散点图组件 ~8h
- Task 2.2: 控制面板 ~4h
- Task 2.3: 数据 Hook ~3h
- Task 2.4: 分析页面 ~3h
**小计: 18h**

### Phase 3: 集成和优化
- Task 3.1: 导航链接 ~1h
- Task 3.2: 性能优化 ~5h
- Task 3.3: 数据缺失处理 ~3h
- Task 3.4: 测试 ~6h
**小计: 15h**

### Phase 4: 时间对比功能（可选）
- Task 4.1-4.3 ~12h
**小计: 12h**

---

**总计:**
- **核心功能 (Phase 1-3):** 43 小时（约 5-6 个工作日）
- **完整功能 (含 Phase 4):** 55 小时（约 7 个工作日）

---

**下一步:** 运行 `/bmad:bmm:workflows:quick-dev` 开始实施此 Tech-Spec
