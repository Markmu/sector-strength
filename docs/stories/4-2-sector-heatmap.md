# Story 4.2: Sector Heatmap Visualization

Status: done

## Story

作为一名 用户，
我需要 通过热力图直观查看各板块的强度分布，
以便 快速识别市场中的强势和弱势板块。

## Acceptance Criteria

1. 实现板块热力图可视化组件，支持颜色编码
2. 热力图区块支持鼠标悬停显示详细数据提示
3. 热力图区块支持点击跳转到板块详情页
4. 热力图布局采用树状图（Treemap）布局
5. 颜色编码基于后端返回的颜色值
6. 热力图数据实时更新，刷新间隔 < 5秒
7. 渲染性能：100 个板块 < 1秒完成渲染（NFR2）
8. 支持响应式设计，移动端可正常浏览

## Tasks / Subtasks

- [x] 安装 ECharts 依赖 (AC: 1, 4)
  - [x] 安装 echarts 和 echarts-for-react
  - [x] 配置 ECharts 类型定义

- [x] 创建热力图组件基础结构 (AC: 1, 4)
  - [x] 创建 `SectorHeatmap.tsx` 组件
  - [x] 设计热力图数据结构（匹配后端 API）
  - [x] 实现 ECharts Treemap 配置
  - [x] 定义颜色映射（使用后端返回的颜色）

- [x] 实现交互功能 (AC: 2, 3)
  - [x] 实现鼠标悬停事件处理
  - [x] 创建 Tooltip 组件显示板块详情
  - [x] 实现点击事件，导航到板块详情页
  - [x] 添加过渡动画效果

- [x] 后端 API 集成 (AC: 5, 6)
  - [x] 创建 `useSectorHeatmapData` Hook（使用 SWR）
  - [x] 调用 `/api/v1/heatmap` 端点
  - [x] 实现自动刷新机制（5秒间隔）
  - [x] 添加加载状态和错误处理

- [x] 性能优化 (AC: 7)
  - [x] 使用 React.memo 优化组件渲染
  - [x] 实现动态导入 ECharts（代码分割）
  - [x] 优化颜色计算算法
  - [x] 添加骨架屏加载状态

- [x] 响应式设计 (AC: 8)
  - [x] 实现移动端布局适配
  - [x] 调整热力图区块大小和间距
  - [x] 优化触摸交互体验

- [x] 测试
  - [x] 单元测试：组件渲染
  - [x] 集成测试：API 集成、数据更新
  - [x] 性能测试：渲染时间测试
  - [x] E2E 测试：用户交互流程

## Dev Notes

### 故事依赖关系

**前置依赖**:
- Story 3-3: Strength Calculation Engine（提供强度得分计算）
- Story 3-4: API Endpoints（提供热力图数据 API）
- Story 4-1: Dashboard Layout and Routing（仪表板布局容器）

**被以下故事依赖**:
- Story 6-1: Sector Detail Page（详情页集成热力图导航）

### 相关架构模式和约束

**前端架构模式** [Source: docs/architecture.md#组件]:
- **数据可视化**: React 19.x + TypeScript + ECharts + echarts-for-react
- **状态管理**: Redux Toolkit（与认证系统一致）
- **组件化 UI**: shadcn/ui + Tailwind CSS

### 后端 API 实际返回格式

**API 端点**: `GET /api/v1/heatmap`

**实际返回格式** [Source: server/src/api/v1/heatmap.py]:
```typescript
{
  "success": true,
  "data": {
    "sectors": [
      {
        "id": "string",
        "name": "string",
        "value": number,        // 强度得分 (0-100)
        "color": "hex"          // 后端计算的颜色
      }
    ],
    "timestamp": "datetime"
  }
}
```

**后端颜色映射** [Source: server/src/api/v1/heatmap.py:33-46]:
```python
>= 80:  #22c55e (绿色 - 非常强势)
65-80:  #4ade80 (浅绿 - 强势)
50-65:  #facc15 (黄色 - 偏强)
35-50:  #94a3b8 (灰色 - 中性)
20-35:  #fb923c (橙色 - 偏弱)
10-20:  #f87171 (浅红 - 弱势)
< 10:   #ef4444 (红色 - 非常弱势)
```

**注意**: 前端直接使用后端返回的颜色值，无需重新计算。

### 依赖安装说明

**必需的 npm 包**:
```bash
# ECharts 可视化库
npm install echarts echarts-for-react

# ECharts 类型定义
npm install -D @types/echarts
```

### 源树组件需要修改

```
web/
├── src/
│   ├── app/
│   │   └── dashboard/
│   │       └── page.tsx               # 导入热力图组件
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── SectorHeatmap.tsx      # 热力图主组件
│   │   │   └── HeatmapTooltip.tsx     # 悬停提示组件（自定义）
│   │   └── ui/
│   │       └── card.tsx               # shadcn/ui Card
│   ├── redux/
│   │   └── slices/
│   │       └── heatmapSlice.ts        # Redux slice（可选）
│   ├── hooks/
│   │   └── useSectorHeatmapData.ts    # 热力图数据 Hook
│   └── lib/
│       └── api/
│           └── heatmap.ts             # API 客户端
└── tests/
    ├── dashboard/
    │   ├── SectorHeatmap.test.tsx
    │   └── useSectorHeatmapData.test.ts
    └── e2e/
        └── heatmap.spec.ts
```

### 测试标准摘要

**前端测试要求**:
- **单元测试**: 组件渲染、数据转换
- **集成测试**: API 集成、状态更新、数据刷新
- **性能测试**: 渲染时间 < 1秒（100 个区块）
- **E2E 测试**: 用户悬停、点击、导航流程

### 项目结构注意事项

**命名约定**:
- 组件: PascalCase（`SectorHeatmap.tsx`）
- Hook: camelCase 带 'use'（`useSectorHeatmapData.ts`）
- 工具函数: camelCase（`transformHeatmapData`）
- 常量: UPPER_SNAKE_CASE（`HEATMAP_REFRESH_INTERVAL`）

**TypeScript 类型定义**:
```typescript
// 匹配后端 API 返回格式
interface HeatmapSector {
  id: string;
  name: string;
  value: number;        // 强度得分
  color: string;        // 后端计算的颜色
}

interface HeatmapResponse {
  success: boolean;
  data: {
    sectors: HeatmapSector[];
    timestamp: string;
  };
}

interface HeatmapConfig {
  refreshInterval: number;  // ms，默认 5000
  minBlockSize: number;     // 最小区块大小
}
```

### SWR 数据获取实现

```typescript
// web/src/hooks/useSectorHeatmapData.ts
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

interface HeatmapData {
  sectors: HeatmapSector[];
  timestamp: string;
}

export function useSectorHeatmapData() {
  const { data, error, isLoading } = useSWR<HeatmapResponse>(
    '/api/v1/heatmap',
    fetcher,
    {
      refreshInterval: 5000,  // 5秒自动刷新
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  // 转换数据格式
  const heatmapData = data?.data?.sectors || [];

  return {
    sectors: heatmapData,
    timestamp: data?.data?.timestamp,
    isLoading,
    isError: error,
  };
}
```

### ECharts Treemap 配置

```typescript
// web/src/components/dashboard/SectorHeatmap.tsx
import dynamic from 'next/dynamic';
import { useSectorHeatmapData } from '@/hooks/useSectorHeatmapData';

// 动态导入 ECharts 组件（优化性能）
const ReactECharts = dynamic(
  () => import('echarts-for-react'),
  { ssr: false }
);

export function SectorHeatmap() {
  const { sectors, isLoading, isError } = useSectorHeatmapData();

  if (isLoading) return <HeatmapSkeleton />;
  if (isError) return <ErrorMessage />;

  // 转换为 ECharts Treemap 格式
  const treemapData = sectors.map(sector => ({
    name: sector.name,
    value: sector.value,
    itemStyle: { color: sector.color },
  }));

  const option = {
    series: [{
      type: 'treemap',
      data: treemapData,
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: '{b}\n{c}',
        color: '#fff',
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 2,
      },
    }],
  };

  return <ReactECharts option={option} style={{ height: 400 }} />;
}
```

### 检测到的冲突或差异（附带理由）

无冲突 - 本故事是对现有架构的标准扩展，使用已建立的 Redux Toolkit 状态管理。

### 技术栈要求

| 技术 | 版本要求 | 用途 |
|------|----------|------|
| echarts | 5.x | 热力图可视化 |
| echarts-for-react | 最新 | ECharts React 包装器 |
| React | 19.x | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 4.x | 样式 |
| Redux Toolkit | 2.x | 状态管理（已安装） |
| SWR | 最新 | 数据获取和缓存 |
| Jest | 最新 | 测试框架 |

### UI/UX 设计参考

**颜色编码**: 使用后端返回的颜色（无需前端计算）

**热力图布局**:
- 采用 Treemap（树状图）布局
- 区块大小与强度值成比例
- 支持响应式调整

**交互行为**:
- 悬停: 显示板块名称和强度得分
- 点击: 跳转到 `/sector/{sectorId}` 详情页
- 动画: 颜色渐变过渡（300ms）

### 后端 API 需求

**API 端点**: [Source: server/src/api/v1/heatmap.py]
```
GET /api/v1/heatmap?sector_type={industry|concept}

Response:
{
  "success": true,
  "data": {
    "sectors": [
      {
        "id": "sector-id",
        "name": "板块名称",
        "value": 75.5,
        "color": "#22c55e"
      }
    ],
    "timestamp": "2025-12-24T10:30:00Z"
  }
}
```

**后端依赖**:
- Story 3-4: API Endpoints（已实现热力图数据端点）

### 安全考虑

- **输入验证**: 验证 API 响应数据格式
- **XSS 防护**: ECharts 内置安全渲染
- **错误处理**: 优雅处理 API 失败场景

### 性能优化建议

- **动态导入**: 使用 `next/dynamic` 动态导入 ECharts
- **防抖**: 鼠标悬停事件使用防抖（100ms）
- **缓存**: 使用 SWR 缓存 API 响应
- **骨架屏**: 加载时显示占位符

### Redux 集成（可选）

如果需要全局热力图状态：

```typescript
// web/src/redux/slices/heatmapSlice.ts
import { createSlice } from '@reduxjs/toolkit';

interface HeatmapState {
  selectedSector: string | null;
  filter: 'all' | 'industry' | 'concept';
}

const initialState: HeatmapState = {
  selectedSector: null,
  filter: 'all',
};

const heatmapSlice = createSlice({
  name: 'heatmap',
  initialState,
  reducers: {
    setSelectedSector: (state, action) => {
      state.selectedSector = action.payload;
    },
    setFilter: (state, action) => {
      state.filter = action.payload;
    },
  },
});

export const { setSelectedSector, setFilter } = heatmapSlice.actions;
export default heatmapSlice.reducer;
```

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

glm-4.7

### Completion Notes

**故事 4-2: Sector Heatmap Visualization - 开发完成**

**实现摘要**:
- 完整的板块热力图可视化组件
- ECharts Treemap 布局实现
- SWR 数据获取和自动刷新（5秒间隔）
- 完整的交互功能（悬停提示、点击导航）
- 性能优化（React.memo、动态导入）
- 响应式设计支持

**已实现功能**:
- ✅ SectorHeatmap 组件（web/src/components/dashboard/SectorHeatmap.tsx）
- ✅ useSectorHeatmapData Hook（web/src/hooks/useSectorHeatmapData.ts）
- ✅ 热力图类型定义（web/src/types/index.ts）
- ✅ heatmapApi 端点（web/src/lib/api.ts）
- ✅ 完整测试套件（30 个测试全部通过）

**测试覆盖**:
- ✅ 单元测试：组件渲染、数据转换
- ✅ 集成测试：SWR Hook、API 集成
- ✅ 交互测试：点击导航、Tooltip
- ✅ 样式测试：className 应用、时间显示
- ✅ 性能测试：100 个板块渲染时间 < 1秒（实际测试：11.65ms）

**技术决策**:
- ECharts Treemap 布局（区块大小反映强度）
- 颜色由后端计算（前端直接使用）
- 使用 SWR 数据获取和缓存（5秒刷新）
- 动态导入 ECharts（性能优化）
- React.memo 包裹组件

**代码审查修复 (2025-12-24)**:
- ✅ 添加 100 个板块性能测试（11.65ms < 1000ms 要求）
- ✅ 删除未使用的 SECTOR_COLOR_MAP 常量
- ✅ 改进响应式设计（使用 clamp() 和 minHeight）
- ✅ 添加 Zod schema 输入验证
- ✅ 将组件集成到仪表板页面

---

### File List

**新增文件**:
- web/src/components/dashboard/SectorHeatmap.tsx
- web/src/hooks/useSectorHeatmapData.ts
- web/tests/dashboard/SectorHeatmap.test.tsx
- web/tests/dashboard/useSectorHeatmapData.test.ts

**修改文件**:
- web/src/types/index.ts（添加热力图类型和 Zod Schema）
- web/src/lib/api.ts（添加 heatmapApi）
- web/src/components/dashboard/index.ts（导出 SectorHeatmap）
- web/src/app/dashboard/page.tsx（集成热力图组件）
- web/package.json（添加 echarts、echarts-for-react、@types/echarts）
