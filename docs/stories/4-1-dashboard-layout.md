# Story 4.1: Dashboard Layout and Routing

Status: Completed

## Story

作为一名 用户，
我需要 访问系统主页仪表板，
以便 直观地查看板块强度热力图和排名概览。

## Acceptance Criteria

1. 创建仪表板主页路由 (`/dashboard`)
2. 实现响应式布局，支持桌面和移动设备（NFR5）
3. 创建仪表板页面框架组件（Dashboard 页面）
4. 设置页面导航结构，集成到主应用路由
5. 页面加载时间 < 1秒（NFR2）
6. 集成 shadcn/ui 组件库的布局组件
7. 页面包含：头部导航栏、主内容区、侧边栏（可选）

## Tasks / Subtasks

- [x] 安装必需依赖 (AC: 6)
  - [x] 安装 shadcn/ui 组件库依赖
  - [x] 初始化 shadcn/ui 配置
  - [x] 安装需要的 shadcn/ui 组件
  - [x] 安装 SWR 数据获取库

- [x] 创建仪表板页面路由 (AC: 1, 4)
  - [x] 在 `web/src/app/dashboard/` 下创建 page.tsx
  - [x] 配置页面元数据（title, description）
  - [x] 更新根布局导航菜单，添加仪表板链接
  - [x] 设置默认首页跳转到仪表板

- [x] 实现响应式布局框架 (AC: 2, 6, 7)
  - [x] 创建 `DashboardLayout.tsx` 组件
  - [x] 使用 shadcn/ui 的 Card 组件作为容器
  - [x] 实现 Tailwind 响应式设计（mobile, tablet, desktop 断点）
  - [x] 创建头部导航栏组件（DashboardHeader.tsx）
  - [x] 创建主内容区域容器（DashboardContent.tsx）

- [x] 集成 Redux Toolkit 状态管理 (AC: 4)
  - [x] 创建 dashboard slice（如需要）
  - [x] 设置页面状态管理
  - [x] 确保路由导航平滑过渡

- [x] 性能优化 (AC: 5)
  - [x] 实现代码分割和懒加载
  - [x] 优化首屏渲染性能
  - [x] 添加加载状态指示器

- [x] 测试 (AC: 2, 5)
  - [x] 创建布局组件的单元测试
  - [x] 测试响应式布局在不同设备的表现
  - [x] 测试页面加载性能

## Dev Notes

### 故事依赖关系

**前置依赖**:
- Story 1-4: Frontend Project Init（提供 Next.js 基础框架）
- Story 2-2: User Login JWT（提供 Redux Toolkit 基础设置）

**被以下故事依赖**:
- Story 4-2: Sector Heatmap（在此布局中添加热力图组件）
- Story 4-3: Ranking Lists（在此布局中添加排名列表）
- Story 4-4: Market Index（在此布局中添加市场指数）

### 相关架构模式和约束

**前端架构模式** [Source: docs/architecture.md#组件]:
- **技术栈**: Next.js 16.x + React 19.x + TypeScript + Tailwind CSS + shadcn/ui
- **App Router**: 使用 Next.js App Router（非 Pages Router）
- **组件化 UI**: 基于 React 的可复用组件
- **状态管理**: 使用 Redux Toolkit（已在 Story 2-2 中设置）

**响应式设计要求** [Source: docs/prd.md#非功能需求]:
- **NFR5**: UI 应具有响应式设计，支持桌面和移动设备
- **NFR1**: 用户交互响应时间 < 200ms
- **NFR2**: 数据可视化渲染 < 1秒

### 依赖安装说明

**必需的 npm 包**:
```bash
# shadcn/ui CLI（用于添加组件）
npm install -D @tailwindcss/postcss tailwindcss-animate class-variance-authority clsx tailwind-merge

# SWR 数据获取和缓存
npm install swr

# Lucide React 图标库（shadcn/ui 依赖）
npm install lucide-react
```

**shadcn/ui 初始化**:
```bash
# 初始化 shadcn/ui 配置
npx shadcn@latest init

# 添加本故事需要的组件
npx shadcn@latest add card button navigation-menu
```

**注意**: shadcn/ui 不是传统 npm 包，而是通过 CLI 添加组件到项目中。组件文件会被复制到 `web/src/components/ui/` 目录。

### 源树组件需要修改

```
web/
├── src/
│   ├── app/
│   │   ├── dashboard/
│   │   │   └── page.tsx               # 仪表板主页
│   │   ├── layout.tsx                 # 根布局（需更新导航）
│   │   └── page.tsx                   # 首页（可重定向到 dashboard）
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── DashboardLayout.tsx    # 仪表板布局组件
│   │   │   ├── DashboardHeader.tsx    # 头部导航
│   │   │   └── DashboardContent.tsx   # 主内容区
│   │   └── ui/                        # shadcn/ui 组件
│   │       ├── card.tsx               # Card 组件
│   │       ├── button.tsx             # Button 组件
│   │       └── navigation-menu.tsx    # Navigation Menu 组件
│   ├── redux/
│   │   └── slices/                    # Redux slices（已存在）
│   │       └── dashboardSlice.ts      # Dashboard 状态（如需要）
│   └── lib/
│       └── utils.ts                   # Tailwind 工具函数（已存在）
└── tests/
    ├── dashboard/
    │   ├── DashboardLayout.test.tsx
    │   └── dashboard.test.tsx
    └── __mocks__/
```

### 测试标准摘要

**前端测试要求** [Source: docs/architecture.md#测试策略]:
- **测试框架**: Jest + React Testing Library
- **测试覆盖率目标**: > 80%
- **测试类型**:
  - 单元测试：组件渲染、用户交互
  - 集成测试：路由导航、布局响应
  - 性能测试：页面加载时间

### 项目结构注意事项

**命名约定** [Source: docs/architecture.md#命名约定]:
- **组件**: PascalCase（如 `DashboardLayout.tsx`）
- **Hook**: camelCase 带 'use'（如 `useDashboardData.ts`）
- **函数/方法**: camelCase（如 `fetchSectorData`）
- **常量**: UPPER_SNAKE_CASE（如 `MAX_RETRY_COUNT`）

**TypeScript 严格模式**:
- 所有组件必须有明确的 Props 类型定义
- 禁止使用 `any` 类型
- 使用严格的 null 检查

### Redux Toolkit 集成

**Dashboard Slice 示例**（如需要）:
```typescript
// web/src/redux/slices/dashboardSlice.ts
import { createSlice } from '@reduxjs/toolkit';

interface DashboardState {
  isLoading: boolean;
  error: string | null;
}

const initialState: DashboardState = {
  isLoading: false,
  error: null,
};

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
  },
});

export const { setLoading, setError } = dashboardSlice.actions;
export default dashboardSlice.reducer;
```

### 检测到的冲突或差异（附带理由）

无冲突 - 本故事是对现有前端架构的扩展，使用已建立的 Redux Toolkit 状态管理。

### 技术栈要求

| 技术 | 版本要求 | 用途 |
|------|----------|------|
| Next.js | 16.x | React 全栈框架（App Router） |
| React | 19.x | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 4.x | 实用优先的 CSS |
| shadcn/ui | 最新 | UI 组件库 |
| Redux Toolkit | 2.x | 状态管理（已安装） |
| SWR | 最新 | 数据获取和缓存 |
| Jest | 最新 | 测试框架 |

### UI/UX 设计参考

**品牌风格** [Source: docs/prd.md#品牌风格]:
- 简洁专业的金融界面风格
- 中性色调为主（灰、白、黑）
- 数据可视化颜色编码：红-橙-黄-绿（强度等级）

**关键交互模式**:
- 点击探索：用户可以点击进入详情页
- 悬停预览：鼠标悬停显示详细数据

### 后端 API 需求

虽然此故事主要关注前端布局，但需要预留以下 API 集成点：
- `GET /api/health` - 健康检查（验证后端连接）
- 后续故事将添加具体数据 API

### 安全考虑

- **CSP 头**: 确保内容安全策略配置正确
- **XSS 防护**: React 内置防护，避免使用 `dangerouslySetInnerHTML`
- **环境变量**: 通过 `process.env` 访问 API 端点，不要硬编码

### 性能优化建议

- **代码分割**: 使用 Next.js 动态导入 `next/dynamic`
- **图片优化**: 使用 `next/image` 组件
- **字体优化**: 使用 `next/font` 优化字体加载
- **数据缓存**: 使用 SWR 进行数据缓存和自动重新验证

### SWR 配置示例

```typescript
// web/src/lib/api.ts
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export function useDashboardData() {
  const { data, error, isLoading } = useSWR('/api/health', fetcher, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  return {
    data,
    isLoading,
    isError: error,
  };
}
```

### 路由配置示例

```typescript
// web/src/app/dashboard/page.tsx
import { Metadata } from 'next';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';

export const metadata: Metadata = {
  title: '仪表板 | Sector Strength',
  description: '板块强度分析仪表板',
};

export default function DashboardPage() {
  return (
    <div className="container mx-auto py-6 px-4">
      <DashboardLayout />
    </div>
  );
}
```

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

glm-4.7

### Completion Notes

**故事 4-1: Dashboard Layout and Routing - 已完成**

**实现摘要**:
- 安装并配置 shadcn/ui 组件库（class-variance-authority, tailwindcss-animate, lucide-react）
- 安装 SWR 数据获取库
- 创建仪表板路由 `/dashboard` 和页面组件
- 实现响应式布局框架，集成侧边栏导航（DashboardLayout, DashboardHeader, DashboardContent）
- 添加加载状态和错误状态组件
- 配置 SWR 数据获取 Hook

**侧边栏功能**:
- 包含4个导航菜单项（仪表板、板块热力图、排名列表、市场指数）
- 支持折叠/展开功能
- 活动状态高亮显示
- 徽章显示即将推出的功能

**测试结果**:
- 26 个测试通过（4个跳过 - DashboardLayout 集成测试）
- 依赖验证测试：7/7 通过
- 页面组件测试：2/2 通过
- 布局组件测试：17/17 通过
- 生产构建成功

**技术决策**:
- 复用现有 Layout 和 Sidebar 组件
- 复用现有 UI slice 进行状态管理（无需单独 dashboard slice）
- 使用现有 Card 和 Button 组件（shadcn/ui NavigationMenu 新增）
- Tailwind 响应式设计（mobile, tablet, desktop 断点）
- SWR 配置包含默认缓存和重试策略

**下一步**:
- Story 4-2: 在此布局基础上添加板块热力图组件
- Story 4-3: 添加排名列表组件
- Story 4-4: 添加市场强度指数组件

---

### File List

**新增文件:**
- web/components.json (shadcn/ui 配置)
- web/src/app/dashboard/page.tsx (仪表板页面)
- web/src/components/dashboard/DashboardLayout.tsx (布局组件)
- web/src/components/dashboard/DashboardHeader.tsx (头部导航组件)
- web/src/components/dashboard/DashboardContent.tsx (内容区域组件)
- web/src/components/dashboard/LoadingState.tsx (加载状态组件)
- web/src/components/dashboard/ErrorState.tsx (错误状态组件)
- web/src/components/dashboard/index.ts (组件导出)
- web/src/lib/swr.ts (SWR 数据获取配置)
- web/tests/dashboard/dashboard-dependencies.test.tsx (依赖测试)
- web/tests/dashboard/dashboard-page.test.tsx (页面测试)
- web/tests/dashboard/dashboard-components.test.tsx (组件测试)

**修改文件:**
- web/package.json (添加依赖和 test 脚本)
- web/tailwind.config.ts (更新 shadcn/ui 配置)
- web/src/app/globals.css (更新主题变量)
- web/src/app/page.tsx (添加自动重定向到 dashboard)
