# Story 4.1: 创建管理员分类参数配置页面

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 管理员（如王芳）,
I want 查看和确认分类参数配置,
So that 我可以确保系统使用正确的参数。

## Acceptance Criteria

**Given** 管理员已登录并具有管理员权限
**When** 访问 /admin/sector-classification/config
**Then** 页面显示"分类参数配置"标题
**And** 页面显示以下参数（只读）：
  - 均线周期：[5, 10, 20, 30, 60, 90, 120, 240] 天
  - 判断基准天数：5 天
  - 分类数量：9 类（第 1 类 ~ 第 9 类）
  - 分类级别定义：完整显示（第 9 类到第 1 类的说明）
**And** 参数显示在卡片组件中（shadcn/ui Card）
**And** 每个参数有清晰的标签说明
**And** 页面只能由管理员访问（NFR-SEC-002, NFR-SEC-003）

## Tasks / Subtasks

- [x] Task 1: 创建管理员配置页面路由 (AC: #)
  - [x] Subtask 1.1: 创建 `web/src/app/admin/sector-classification/config/page.tsx`
  - [x] Subtask 1.2: 添加 'use client' 指令
  - [x] Subtask 1.3: 导入 AdminLayout 或复用 DashboardLayout
  - [x] Subtask 1.4: 实现页面基础结构

- [x] Task 2: 实现管理员权限验证 (AC: #)
  - [x] Subtask 2.1: 检查用户角色（从 AuthContext 或 JWT token）
  - [x] Subtask 2.2: 非管理员用户重定向到 403 页面或首页
  - [x] Subtask 2.3: 显示"权限不足"错误提示（如果需要）

- [x] Task 3: 创建配置参数展示组件 (AC: #)
  - [x] Subtask 3.1: 创建 `AdminConfigDisplay.tsx` 组件
  - [x] Subtask 3.2: 使用 shadcn/ui Card 组件展示参数
  - [x] Subtask 3.3: 显示均线周期数组 [5, 10, 20, 30, 60, 90, 120, 240]
  - [x] Subtask 3.4: 显示判断基准天数（5 天）
  - [x] Subtask 3.5: 显示分类数量（9 类）

- [x] Task 4: 实现分类级别定义展示 (AC: #)
  - [x] Subtask 4.1: 创建 `ClassificationLevelDefinition.tsx` 组件
  - [x] Subtask 4.2: 展示第 9 类到第 1 类的完整定义
  - [x] Subtask 4.3: 使用表格或列表格式清晰展示
  - [x] Subtask 4.4: 添加颜色标识（绿色→红色渐变）

- [x] Task 5: 添加管理员菜单项 (AC: #)
  - [x] Subtask 5.1: 在侧边栏或导航中添加"分类配置"菜单项
  - [x] Subtask 5.2: 设置正确的路由 `/admin/sector-classification/config`
  - [x] Subtask 5.3: 添加适当的图标（Settings 图标）
  - [x] Subtask 5.4: 确保菜单项仅对管理员可见

- [x] Task 6: 创建类型定义 (AC: #)
  - [x] Subtask 6.1: 创建 `ClassificationConfig` 类型定义
  - [x] Subtask 6.2: 定义配置参数的 TypeScript 接口
  - [x] Subtask 6.3: 确保类型安全

- [x] Task 7: 创建测试 (AC: #)
  - [x] Subtask 7.1: 测试管理员用户可以访问页面
  - [x] Subtask 7.2: 测试非管理员用户被拒绝访问
  - [x] Subtask 7.3: 测试所有配置参数正确显示
  - [x] Subtask 7.4: 测试分类级别定义完整展示

## Dev Notes

### Epic 4 完整上下文

**Epic 目标:** 为管理员提供分类参数查看、算法测试、运行状态监控和操作审计日志功能。

**FRs 覆盖:**
- FR19: 管理员可以查看分类参数配置（均线周期、判断基准天数、分类数量）
- FR20: 管理员可以测试分类算法（后续 Story 4.2）
- FR21: 管理员可以查看分类计算的运行状态（后续 Story 4.3）
- FR22: 管理员可以查看操作审计日志（后续 Story 4.4）
- FR24: 系统记录所有管理员操作到审计日志

**NFRs 相关:**
- NFR-SEC-002: 管理员功能必须有基于角色的访问控制（RBAC）
- NFR-SEC-003: 非管理员用户无法访问管理员功能
- NFR-SEC-006: 系统应记录所有管理员操作到审计日志
- NFR-SEC-007: 审计日志应包含操作人、时间、操作内容
- NFR-SEC-008: 审计日志应保留至少 6 个月

**依赖关系:**
- 依赖 Epic 1 完成（API 端点、数据库已实现）
- 依赖现有用户认证和 RBAC 系统
- 后续 Story 4.2 将在此页面添加测试按钮

**后续影响:**
- Story 4.2 将添加"测试分类算法"按钮
- Story 4.3 将创建监控面板
- Story 4.4 将实现审计日志查看

### 架构模式与约束

**管理员页面结构:**
```
AdminLayout (或复用 DashboardLayout)
    ├── Header (管理员控制台)
    ├── Sidebar (管理员菜单)
    │   ├── 分类配置 (当前)
    │   ├── 算法测试 (Story 4.2)
    │   ├── 运行监控 (Story 4.3)
    │   └── 审计日志 (Story 4.4)
    └── Main (内容区域)
```

**关键设计决策:**

| 方面 | 设计决策 | 原因 |
|------|----------|------|
| 路由模式 | `/admin/sector-classification/config` | 清晰的管理员路由结构 |
| 布局组件 | AdminLayout 或复用 DashboardLayout | 需要验证现有系统是否有 AdminLayout |
| 权限验证 | 基于角色的访问控制（RBAC） | NFR-SEC-002 要求 |
| 参数来源 | 硬编码或从配置文件读取 | 分类参数是系统常量 |
| 组件库 | shadcn/ui Card | 与项目 UI 风格一致 |

**缠论算法参数（只读展示）:**

```
均线周期: [5, 10, 20, 30, 60, 90, 120, 240]
判断基准天数: 5
分类数量: 9

分类级别定义:
- 第 9 类: 价格在所有均线上方（最强）
- 第 8 类: 攻克 240 日线
- 第 7 类: 攻克 120 日线
- 第 6 类: 攻克 90 日线
- 第 5 类: 攻克 60 日线
- 第 4 类: 攻克 30 日线
- 第 3 类: 攻克 20 日线
- 第 2 类: 攻克 10 日线
- 第 1 类: 价格在所有均线下方（最弱）
```

### 项目结构规范

**文件结构:**
```
web/src/
├── app/
│   └── admin/
│       └── sector-classification/
│           └── config/
│               └── page.tsx                      # 新增：管理员配置页面
├── components/
│   ├── admin/
│   │   ├── AdminLayout.tsx                      # 可能需要创建
│   │   └── sector-classification/
│   │       ├── AdminConfigDisplay.tsx           # 新增：配置展示组件
│   │       └── ClassificationLevelDefinition.tsx # 新增：分类级别定义组件
│   └── ui/
│       └── card.tsx                             # 已有：shadcn/ui Card
└── types/
    └── admin-config.ts                          # 新增：管理员配置类型
```

**命名约定:**
- 页面文件: `page.tsx` (App Router 约定)
- 组件文件: `PascalCase.tsx`
- 类型文件: `kebab-case.ts` 或 `PascalCase.ts`

### 认证与授权

**RBAC 权限模型:**
```typescript
// 用户角色类型
type UserRole = 'admin' | 'user'

// JWT Token payload（假设）
interface JWTPayload {
  user_id: string
  username: string
  role: UserRole  // 关键：角色字段
  exp: number
}

// 权限检查函数
function hasAdminRole(user: User | null): boolean {
  return user?.role === 'admin'
}
```

**权限验证实现:**
```typescript
// 在页面组件中
import { useAuth } from '@/contexts/AuthContext'

export default function AdminConfigPage() {
  const { user, isAuthenticated, isLoading } = useAuth()

  // 检查管理员权限
  if (!isAuthenticated || !hasAdminRole(user)) {
    // 重定向到 403 或首页
    redirect('/403') // 或 return <AccessDenied />
  }

  // 渲染管理员内容
  return (
    <AdminLayout>
      {/* 配置内容 */}
    </AdminLayout>
  )
}
```

**管理员菜单可见性:**
```typescript
// 在 DashboardLayout 或 AdminLayout 中
const adminMenuItems: SidebarItem[] = [
  {
    title: '分类配置',
    href: '/admin/sector-classification/config',
    icon: <Settings className="w-5 h-5" />,
    visible: user?.role === 'admin',  // 仅管理员可见
  },
]
```

### TypeScript 类型定义

**分类配置类型:**
```typescript
// web/src/types/admin-config.ts
export interface ClassificationConfig {
  /** 均线周期（天） */
  ma_periods: number[]
  /** 判断基准天数（天） */
  benchmark_days: number
  /** 分类数量 */
  classification_count: number
  /** 分类级别定义 */
  level_definitions: ClassificationLevelDefinition[]
}

export interface ClassificationLevelDefinition {
  /** 分类级别 */
  level: number
  /** 级别名称 */
  name: string
  /** 说明 */
  description: string
  /** 颜色标识（可选） */
  color?: string
}

/** 硬编码的分类配置（系统常量） */
export const CLASSIFICATION_CONFIG: ClassificationConfig = {
  ma_periods: [5, 10, 20, 30, 60, 90, 120, 240],
  benchmark_days: 5,
  classification_count: 9,
  level_definitions: [
    { level: 9, name: '第 9 类', description: '价格在所有均线上方（最强）', color: 'text-green-600' },
    { level: 8, name: '第 8 类', description: '攻克 240 日线', color: 'text-green-500' },
    { level: 7, name: '第 7 类', description: '攻克 120 日线', color: 'text-green-400' },
    { level: 6, name: '第 6 类', description: '攻克 90 日线', color: 'text-yellow-400' },
    { level: 5, name: '第 5 类', description: '攻克 60 日线', color: 'text-yellow-500' },
    { level: 4, name: '第 4 类', description: '攻克 30 日线', color: 'text-orange-400' },
    { level: 3, name: '第 3 类', description: '攻克 20 日线', color: 'text-orange-500' },
    { level: 2, name: '第 2 类', description: '攻克 10 日线', color: 'text-red-400' },
    { level: 1, name: '第 1 类', description: '价格在所有均线下方（最弱）', color: 'text-red-600' },
  ],
}
```

**组件 Props 类型:**
```typescript
// web/src/components/admin/sector-classification/AdminConfigDisplay.types.ts
export interface AdminConfigDisplayProps {
  config: ClassificationConfig
}

export interface ClassificationLevelDefinitionProps {
  definitions: ClassificationLevelDefinition[]
}
```

### 组件实现

**AdminConfigDisplay 组件:**
```typescript
// web/src/components/admin/sector-classification/AdminConfigDisplay.tsx
'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'
import { ClassificationLevelDefinition } from './ClassificationLevelDefinition'
import type { AdminConfigDisplayProps } from './AdminConfigDisplay.types'

export function AdminConfigDisplay({ config }: AdminConfigDisplayProps) {
  return (
    <div className="space-y-6">
      {/* 均线周期卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>均线周期配置</CardTitle>
          <CardDescription>用于板块分类计算的均线周期（天）</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {config.ma_periods.map((period) => (
              <span
                key={period}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary/10 text-primary"
              >
                {period} 日线
              </span>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 判断基准天数卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>判断基准天数</CardTitle>
          <CardDescription>用于判断反弹/调整状态的天数基准</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-semibold">{config.benchmark_days} 天</p>
        </CardContent>
      </Card>

      {/* 分类数量卡片 */}
      <Card>
        <CardHeader>
          <CardTitle>分类数量</CardTitle>
          <CardDescription>板块强弱分类的总类别数</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-semibold">{config.classification_count} 类</p>
        </CardContent>
      </Card>

      {/* 分类级别定义 */}
      <ClassificationLevelDefinition definitions={config.level_definitions} />
    </div>
  )
}
```

**ClassificationLevelDefinition 组件:**
```typescript
// web/src/components/admin/sector-classification/ClassificationLevelDefinition.tsx
'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { ClassificationLevelDefinitionProps } from './ClassificationLevelDefinition.types'

export function ClassificationLevelDefinition({ definitions }: ClassificationLevelDefinitionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>分类级别定义</CardTitle>
        <CardDescription>缠论板块强弱分类的完整级别说明</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">级别</TableHead>
              <TableHead>名称</TableHead>
              <TableHead>说明</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {definitions.map((def) => (
              <TableRow key={def.level}>
                <TableCell className={`font-semibold ${def.color || ''}`}>
                  {def.name}
                </TableCell>
                <TableCell>
                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                    def.level >= 7 ? 'bg-green-100 text-green-800' :
                    def.level >= 5 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {def.level === 9 ? '最强' :
                     def.level === 1 ? '最弱' :
                     def.level >= 7 ? '强势' :
                     def.level >= 4 ? '中等' : '弱势'}
                  </span>
                </TableCell>
                <TableCell>{def.description}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

**页面实现:**
```typescript
// web/src/app/admin/sector-classification/config/page.tsx
'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { AdminConfigDisplay } from '@/components/admin/sector-classification/AdminConfigDisplay'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'
import { AccessDenied } from '@/components/admin/AccessDenied' // 如果存在

export default function AdminConfigPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading } = useAuth()

  // 检查管理员权限
  const isAdmin = isAuthenticated && user?.role === 'admin'

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // 未登录用户重定向到登录页面
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // 加载中
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    )
  }

  // 权限不足
  if (!isAdmin) {
    return (
      <DashboardLayout>
        <AccessDenied message="您没有权限访问此页面。此功能仅限管理员使用。" />
      </DashboardLayout>
    )
  }

  // 管理员页面
  return (
    <DashboardLayout>
      <DashboardHeader
        title="分类参数配置"
        subtitle="查看和确认板块强弱分类的系统参数"
      />

      <div className="space-y-6">
        <AdminConfigDisplay config={CLASSIFICATION_CONFIG} />
      </div>
    </DashboardLayout>
  )
}
```

### 测试要求

**权限测试:**
```typescript
// web/tests/app/admin/sector-classification/config/page.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import AdminConfigPage from '@/app/admin/sector-classification/config/page'

// Mock dependencies
jest.mock('next/navigation')
jest.mock('@/contexts/AuthContext')

describe('AdminConfigPage - 权限控制', () => {
  it('管理员用户应该能够访问页面', async () => {
    const mockUser = { id: '1', username: 'admin', role: 'admin' }
    useAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('分类参数配置')).toBeInTheDocument()
      expect(screen.getByText('均线周期配置')).toBeInTheDocument()
    })
  })

  it('普通用户不应该能够访问页面', async () => {
    const mockUser = { id: '2', username: 'user', role: 'user' }
    useAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText(/权限不足/)).toBeInTheDocument()
    })
  })

  it('未登录用户应该被重定向到登录页面', async () => {
    useAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(useRouter().push).toHaveBeenCalledWith('/login')
    })
  })
})
```

**组件测试:**
```typescript
// web/tests/components/admin/sector-classification/AdminConfigDisplay.test.tsx
import { render, screen } from '@testing-library/react'
import { AdminConfigDisplay } from '@/components/admin/sector-classification/AdminConfigDisplay'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'

describe('AdminConfigDisplay', () => {
  it('应该显示所有配置参数', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('均线周期配置')).toBeInTheDocument()
    expect(screen.getByText('判断基准天数')).toBeInTheDocument()
    expect(screen.getByText('分类数量')).toBeInTheDocument()
    expect(screen.getByText('分类级别定义')).toBeInTheDocument()
  })

  it('应该显示所有均线周期', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    CLASSIFICATION_CONFIG.ma_periods.forEach((period) => {
      expect(screen.getByText(`${period} 日线`)).toBeInTheDocument()
    })
  })

  it('应该显示判断基准天数', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('5 天')).toBeInTheDocument()
  })

  it('应该显示分类数量', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('9 类')).toBeInTheDocument()
  })

  it('应该显示所有分类级别定义', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    CLASSIFICATION_CONFIG.level_definitions.forEach((def) => {
      expect(screen.getByText(def.name)).toBeInTheDocument()
      expect(screen.getByText(def.description)).toBeInTheDocument()
    })
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- 管理员页面放在 `app/admin/` 目录下
- 管理员组件放在 `components/admin/` 目录下
- 使用 App Router 约定
- 遵循 TypeScript strict mode
- 使用 shadcn/ui 组件库

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式
- 需要验证：系统是否已有 AdminLayout，如果没有则复用 DashboardLayout

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture] - 前端架构设计
- [Source: _bmad-output/planning-artifacts/architecture.md#Security Requirements] - 安全要求（RBAC）

**项目上下文:**
- [Source: _bmad-output/project-context.md#Framework-Specific Rules] - React/Next.js 规则
- [Source: _bmad-output/project-context.md#Security Rules] - 安全规则
- [Source: _bmad-output/project-context.md#Critical Don't-Miss Rules] - 关键规则

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] - Epic 4: 管理员功能与监控
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1] - Story 4.1 完整验收标准

**PRD 参考:**
- [Source: _bmad-output/planning-artifacts/prd.md#FR19] - FR19: 管理员可以查看分类参数配置
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 3] - Journey 3: 王芳 - 配置分类参数的管理员

### Previous Story Intelligence (Epic 3 Stories)

**从 Epic 3 学到的经验:**

1. **弹窗和对话框组件:**
   - Story 3.1 创建了 HelpDialog，参考弹窗组件模式
   - Story 3.4 创建了 RiskAlertDialog，了解 AlertDialog 模式
   - 使用 shadcn/ui Dialog 和 AlertDialog 组件

2. **页面布局模式:**
   - Story 2A.1 创建了板块分类页面，了解页面结构
   - 使用 DashboardLayout 和 DashboardHeader 组件
   - 使用 'use client' 指令

3. **认证集成:**
   - 所有页面都使用 AuthContext 进行认证
   - 未登录用户重定向到登录页面
   - 检查用户角色进行权限验证

4. **测试模式:**
   - 使用 Jest 和 Testing Library
   - Mock 外部依赖（next/navigation, AuthContext）
   - 测试权限验证和页面渲染

**Git 智能摘要（最近提交）:**
- `a87f8ef` chore: 更新 Story 3.4 状态为 done
- `495183b` feat: 完成 Story 3.4 创建风险提示弹窗并通过代码审查
- `840937a` feat: 完成 Story 3.3 集成免责声明到所有页面并通过代码审查

**代码模式参考:**
- 查看 `web/src/app/dashboard/sector-classification/page.tsx` 了解页面结构
- 查看 `web/src/components/sector-classification/HelpDialog.tsx` 了解弹窗组件
- 查看 `web/src/contexts/AuthContext.tsx` 了解认证系统

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 所有使用 hooks/state 的组件必须添加
2. **命名导出** - 使用 `export default function`，不要使用命名导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **权限验证** - 必须检查用户角色，非管理员拒绝访问
5. **RBAC 实现** - 使用用户角色字段进行权限控制
6. **中文文本** - 所有用户可见文本使用中文
7. **shadcn/ui 组件** - 使用 Card、Table 等组件
8. **TypeScript strict** - 不要使用 `any` 类型，正确定义接口
9. **硬编码配置** - 分类参数作为系统常量展示
10. **只读展示** - 参数不可编辑（后续 Story 可能添加编辑功能）

**依赖:**
- Epic 1 完成（API 端点、数据库已实现）
- 现有认证系统（AuthContext）
- 现有 RBAC 系统（用户角色字段）
- shadcn/ui Card、Table 组件已安装

**后续影响:**
- Story 4.2 将在此页面添加"测试分类算法"按钮
- Story 4.3 将创建监控面板
- Story 4.4 将实现审计日志查看
- Epic 4 完成后，所有管理员功能已就绪

### 性能与可访问性要求

**性能要求 (NFR-PERF-001):**
- 页面首次加载（FCP）< 1.5 秒
- 配置数据是硬编码常量，无需 API 请求
- 使用 Next.js App Router 的自动代码分割

**可访问性要求 (NFR-SEC-002, NFR-SEC-003, NFR-ACC-001):**
- 颜色对比度符合 WCAG AA 标准
- 语义化 HTML 结构
- 表格有正确的表头（th 元素）
- 清晰的错误提示（权限不足）

### 安全要求

**管理员权限验证 (NFR-SEC-002, NFR-SEC-003):**
- 前端：检查用户角色字段
- 后端：API 端点必须验证管理员权限（后续 Story）
- 非管理员用户无法访问管理员页面
- 非管理员用户无法看到管理员菜单项

**审计日志 (NFR-SEC-006, NFR-SEC-007, NFR-SEC-008):**
- Story 4.1 主要是只读展示，暂不需要记录审计日志
- 后续 Story 4.2（测试算法）需要记录审计日志
- 审计日志应包含：操作人、时间、操作内容、IP 地址

### 实现计划

**优先级 1: 创建类型定义**
1. 创建 `admin-config.ts` 类型文件
2. 定义 `ClassificationConfig` 接口
3. 定义 `ClassificationLevelDefinition` 接口
4. 导出硬编码的配置常量 `CLASSIFICATION_CONFIG`

**优先级 2: 创建配置展示组件**
1. 创建 `AdminConfigDisplay.tsx` 组件
2. 创建 `ClassificationLevelDefinition.tsx` 组件
3. 使用 shadcn/ui Card 和 Table 组件
4. 实现配置参数展示

**优先级 3: 创建管理员页面**
1. 创建 `app/admin/sector-classification/config/page.tsx`
2. 添加 'use client' 指令
3. 实现权限验证逻辑
4. 集成 AdminConfigDisplay 组件

**优先级 4: 添加管理员菜单**
1. 在 DashboardLayout 或 AdminLayout 中添加菜单项
2. 设置路由为 `/admin/sector-classification/config`
3. 添加 Settings 图标
4. 确保菜单项仅对管理员可见

**优先级 5: 创建测试**
1. 测试管理员用户访问
2. 测试非管理员用户被拒绝
3. 测试配置参数显示
4. 测试权限验证逻辑

**优先级 6: 验证和代码审查**
1. 验证所有验收标准
2. 运行测试套件
3. 代码质量检查
4. 安全审查（权限验证）

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-26 - Story 创建完成

#### 2026-01-26 - Story 实现完成

**实现内容:**
1. 创建了管理员配置页面 (`/admin/sector-classification/config`)
2. 实现了基于 RBAC 的权限验证（使用 `isAdmin` 从 AuthContext）
3. 创建了配置展示组件 `AdminConfigDisplay` 和 `ClassificationLevelDefinition`
4. 添加了管理员菜单项"分类配置"，使用 Sliders 图标
5. 所有组件使用 TypeScript strict mode，遵循项目规范
6. 使用现有的 Card 和 Table 组件（非 shadcn/ui，而是项目自定义组件）

**技术决策:**
- 复用 `DashboardLayout` 而非创建新的 `AdminLayout`，保持一致性
- 配置参数作为硬编码常量（`CLASSIFICATION_CONFIG`），无需 API 调用
- 使用 `useAuth` hook 的 `isAdmin` 属性进行权限验证
- 权限不足时显示友好的错误页面，而非简单重定向
- 所有组件遵循 'use client' 模式，支持客户端导航

**文件创建:**
- `web/src/types/admin-config.ts` - 类型定义和配置常量
- `web/src/components/admin/sector-classification/AdminConfigDisplay.tsx` - 主配置展示组件
- `web/src/components/admin/sector-classification/AdminConfigDisplay.types.ts` - 组件类型
- `web/src/components/admin/sector-classification/ClassificationLevelDefinition.tsx` - 级别定义展示
- `web/src/components/admin/sector-classification/ClassificationLevelDefinition.types.ts` - 组件类型
- `web/src/app/admin/sector-classification/config/page.tsx` - 管理员配置页面
- `web/tests/app/admin/sector-classification/config/page.test.tsx` - 页面测试
- `web/tests/components/admin/sector-classification/AdminConfigDisplay.test.tsx` - 组件测试
- `web/tests/components/admin/sector-classification/ClassificationLevelDefinition.test.tsx` - 组件测试

**文件修改:**
- `web/src/components/dashboard/DashboardLayout.tsx` - 添加"分类配置"菜单项

### File List

**已创建的文件:**
- `web/src/types/admin-config.ts` - 管理员配置类型定义和硬编码配置常量
- `web/src/components/admin/sector-classification/AdminConfigDisplay.tsx` - 配置展示组件
- `web/src/components/admin/sector-classification/AdminConfigDisplay.types.ts` - 组件类型
- `web/src/components/admin/sector-classification/ClassificationLevelDefinition.tsx` - 分类级别定义组件
- `web/src/components/admin/sector-classification/ClassificationLevelDefinition.types.ts` - 组件类型
- `web/src/app/admin/sector-classification/config/page.tsx` - 管理员配置页面
- `web/tests/app/admin/sector-classification/config/page.test.tsx` - 页面测试
- `web/tests/components/admin/sector-classification/AdminConfigDisplay.test.tsx` - 组件测试
- `web/tests/components/admin/sector-classification/ClassificationLevelDefinition.test.tsx` - 组件测试

**已修改的文件:**
- `web/src/components/dashboard/DashboardLayout.tsx` - 添加"分类配置"管理员菜单项

## Change Log

### 2026-01-26

**Story 创建:**
- 创建 Story 4.1 文档
- 定义管理员配置页面规范
- 定义权限验证要求（RBAC）
- 定义配置参数展示
- 定义分类级别定义展示
- 定义测试策略
- 定义安全要求（NFR-SEC-002, NFR-SEC-003）
- Story 状态: backlog → ready-for-dev

**Story 实现:**
- 实现所有 7 个任务和 27 个子任务
- 创建 9 个新文件（类型、组件、页面、测试）
- 修改 1 个现有文件（DashboardLayout）
- TypeScript 类型检查通过
- 所有验收标准已满足
- Story 状态: ready-for-dev → review
