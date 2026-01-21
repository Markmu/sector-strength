# Story 1.4: 创建最小前端验证页面

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 后端开发者/测试人员,
I want 创建一个简单的 API 验证页面,
so that 可以快速验证 API 端点可用性。

## Acceptance Criteria

**Given** API 端点已实现 (Story 1.3)
**When** 访问验证页面 /api-test/sector-classification
**Then** 页面显示"API 测试页面"标题
**And** 页面显示一个"测试获取所有分类"按钮
**And** 点击按钮后:
  - 发送请求到 GET /api/v1/sector-classifications
  - 显示原始 JSON 响应数据
  - 显示 HTTP 状态码
  - 显示响应时间
**And** 页面显示一个"测试获取单个分类"输入框和按钮
**And** 输入 sector_id 后:
  - 发送请求到 GET /api/v1/sector-classifications/{sector_id}
  - 显示响应数据或错误信息
**And** 错误时显示明确的错误提示
**And** 页面样式简洁，仅用于开发/测试验证

## Tasks / Subtasks

- [x] Task 1: 创建验证页面路由 (AC: 全部)
  - [x] Subtask 1.1: 创建 `web/src/app/api-test/sector-classification/page.tsx`
  - [x] Subtask 1.2: 添加 'use client' 指令（使用 React hooks）
  - [x] Subtask 1.3: 设置页面标题为"API 测试页面"
  - [x] Subtask 1.4: 添加页面布局（Header + Content）

- [x] Task 2: 实现获取所有分类按钮 (AC: 全部)
  - [x] Subtask 2.1: 创建测试按钮组件
  - [x] Subtask 2.2: 添加 onClick 事件处理器
  - [x] Subtask 2.3: 调用 GET /api/v1/sector-classifications
  - [x] Subtask 2.4: 显示 JSON 响应数据（格式化）
  - [x] Subtask 2.5: 显示 HTTP 状态码
  - [x] Subtask 2.6: 显示响应时间（毫秒）
  - [x] Subtask 2.7: 添加加载状态（按钮禁用 + 旋转图标）

- [x] Task 3: 实现获取单个分类功能 (AC: 全部)
  - [x] Subtask 3.1: 创建 sector_id 输入框
  - [x] Subtask 3.2: 创建测试按钮
  - [x] Subtask 3.3: 添加 onClick 事件处理器
  - [x] Subtask 3.4: 调用 GET /api/v1/sector-classifications/{sector_id}
  - [x] Subtask 3.5: 显示响应数据或错误信息

- [x] Task 4: 实现错误处理 (AC: 全部)
  - [x] Subtask 4.1: 捕获 401 未认证错误
  - [x] Subtask 4.2: 捕获 404 不存在错误
  - [x] Subtask 4.3: 捕获 500 服务器错误
  - [x] Subtask 4.4: 显示中文错误消息
  - [x] Subtask 4.5: 错误消息使用红色字体

- [x] Task 5: 样式和布局 (AC: 全部)
  - [x] Subtask 5.1: 使用简洁的 Tailwind CSS 样式
  - [x] Subtask 5.2: JSON 响应使用预格式化显示
  - [x] Subtask 5.3: 添加页面标题和说明
  - [x] Subtask 5.4: 响应式布局（移动端友好）

- [x] Task 6: 创建 API 客户端工具 (AC: 全部)
  - [x] Subtask 6.1: 创建 `web/src/lib/sectorClassificationApi.ts`
  - [x] Subtask 6.2: 实现 `getAllClassifications()` 方法
  - [x] Subtask 6.3: 实现 `getClassificationById()` 方法
  - [x] Subtask 6.4: 集成 JWT 认证（从 localStorage 读取 token）
  - [x] Subtask 6.5: 处理错误响应

## Dev Notes

### 页面结构设计

**Next.js App Router 页面:**

```typescript
// web/src/app/api-test/sector-classification/page.tsx
'use client'

import { useState } from 'react'
import { sectorClassificationApi } from '@/lib/sectorClassificationApi'

interface TestResult {
  status: number
  data: unknown
  responseTime: number
  error?: string
}

export default function SectorClassificationAPITestPage() {
  const [allResult, setAllResult] = useState<TestResult | null>(null)
  const [singleResult, setSingleResult] = useState<TestResult | null>(null)
  const [sectorId, setSectorId] = useState<string>('1')
  const [loading, setLoading] = useState(false)

  // 测试获取所有分类
  const handleTestGetAll = async () => {
    setLoading(true)
    const startTime = performance.now()

    try {
      const response = await sectorClassificationApi.getAllClassifications()
      const endTime = performance.now()

      setAllResult({
        status: response.status,
        data: response.data,
        responseTime: endTime - startTime
      })
    } catch (error: unknown) {
      const endTime = performance.now()
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      setAllResult({
        status: 500,
        data: null,
        responseTime: endTime - startTime,
        error: errorMessage
      })
    } finally {
      setLoading(false)
    }
  }

  // 测试获取单个分类
  const handleTestGetSingle = async () => {
    if (!sectorId) return

    setLoading(true)
    const startTime = performance.now()

    try {
      const response = await sectorClassificationApi.getClassificationById(parseInt(sectorId))
      const endTime = performance.now()

      setSingleResult({
        status: response.status,
        data: response.data,
        responseTime: endTime - startTime
      })
    } catch (error: unknown) {
      const endTime = performance.now()
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      setSingleResult({
        status: 500,
        data: null,
        responseTime: endTime - startTime,
        error: errorMessage
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">API 测试页面</h1>
        <p className="text-gray-600 mb-8">板块强弱分类 API 端点验证工具</p>

        {/* 测试获取所有分类 */}
        <section className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">测试获取所有分类</h2>
          <button
            onClick={handleTestGetAll}
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? '测试中...' : '测试获取所有分类'}
          </button>

          {allResult && (
            <div className="mt-4">
              <div className="flex items-center gap-4 mb-2">
                <span className={`font-semibold ${allResult.error ? 'text-red-500' : 'text-green-500'}`}>
                  状态码: {allResult.status}
                </span>
                <span className="text-gray-600">
                  响应时间: {allResult.responseTime.toFixed(2)}ms
                </span>
              </div>

              {allResult.error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-2">
                  错误: {allResult.error}
                </div>
              )}

              <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-x-auto text-sm">
                {JSON.stringify(allResult.data, null, 2)}
              </pre>
            </div>
          )}
        </section>

        {/* 测试获取单个分类 */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">测试获取单个分类</h2>
          <div className="flex items-center gap-4 mb-4">
            <input
              type="number"
              value={sectorId}
              onChange={(e) => setSectorId(e.target.value)}
              placeholder="输入板块 ID"
              className="border border-gray-300 rounded px-3 py-2 w-40"
            />
            <button
              onClick={handleTestGetSingle}
              disabled={loading || !sectorId}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
            >
              {loading ? '测试中...' : '测试获取单个分类'}
            </button>
          </div>

          {singleResult && (
            <div className="mt-4">
              <div className="flex items-center gap-4 mb-2">
                <span className={`font-semibold ${singleResult.error ? 'text-red-500' : 'text-green-500'}`}>
                  状态码: {singleResult.status}
                </span>
                <span className="text-gray-600">
                  响应时间: {singleResult.responseTime.toFixed(2)}ms
                </span>
              </div>

              {singleResult.error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-2">
                  错误: {singleResult.error}
                </div>
              )}

              <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-x-auto text-sm">
                {JSON.stringify(singleResult.data, null, 2)}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
```

### API 客户端工具

**TypeScript API 客户端:**

```typescript
// web/src/lib/sectorClassificationApi.ts

interface ApiResponse<T> {
  data: T
  total?: number
}

interface ApiError {
  detail: string
}

class SectorClassificationAPI {
  private baseURL = '/api/v1'
  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` })
    }
  }

  async getAllClassifications(): Promise<ApiResponse<SectorClassification[]>> {
    const response = await fetch(`${this.baseURL}/sector-classifications`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || '获取分类数据失败')
    }

    return response.json()
  }

  async getClassificationById(sectorId: number): Promise<ApiResponse<SectorClassification>> {
    const response = await fetch(`${this.baseURL}/sector-classifications/${sectorId}`, {
      headers: this.getHeaders()
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || '获取板块分类失败')
    }

    return response.json()
  }
}

export const sectorClassificationApi = new SectorClassificationAPI()
```

### 架构模式与约束

**前端架构:**
- 使用 Next.js 16.1.1 App Router
- 使用 React 19.2.0 和 TypeScript 5
- 使用 Tailwind CSS 4.x 进行样式
- 页面必须是客户端组件（'use client'）
- 使用 React hooks（useState, useEffect）

**关键设计决策:**

| 方面 | 设计决策 | 原因 |
|------|----------|------|
| 路由位置 | `/api-test/sector-classification` | 明确标识这是测试页面 |
| 客户端组件 | 'use client' | 需要使用 hooks 和事件处理 |
| 样式方案 | Tailwind CSS | 复用项目现有配置 |
| API 通信 | fetch API | 简单直接，无需额外依赖 |
| 错误处理 | try-catch + 用户友好消息 | 明确的错误提示 |

### 项目结构规范

**前端文件结构:**
```
web/src/
├── app/
│   └── api-test/
│       └── sector-classification/
│           └── page.tsx                # 新增：API 测试页面
├── lib/
│   └── sectorClassificationApi.ts     # 新增：API 客户端
└── types/
    └── sector-classification.ts       # 新增：类型定义（可选）
```

**命名约定:**
- 页面文件: `page.tsx` (Next.js App Router 约定)
- API 客户端文件: `camelCase.ts` (如 `sectorClassificationApi.ts`)
- 组件函数: `PascalCase` (如 `SectorClassificationAPITestPage`)
- Hooks 变量: `camelCase` (如 `useState`, `useEffect`)

### 错误处理规范

**用户友好的错误消息:**

```typescript
const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    // 处理常见错误类型
    if (error.message.includes('401')) {
      return '未认证：请先登录'
    }
    if (error.message.includes('404')) {
      return '板块不存在'
    }
    if (error.message.includes('500')) {
      return '服务器错误，请稍后重试'
    }
    return error.message
  }
  return '未知错误'
}
```

**错误显示样式:**
```tsx
<div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded">
  {getErrorMessage(error)}
</div>
```

### Testing Standards Summary

**测试要求:**
- 页面可以手动测试（主要测试方式）
- 验证按钮点击正常工作
- 验证 API 调用成功
- 验证错误处理正常
- 验证响应时间显示正确

**手动测试清单:**
1. 访问 `/api-test/sector-classification`
2. 点击"测试获取所有分类"按钮
3. 验证显示 JSON 数据
4. 验证显示状态码和响应时间
5. 输入板块 ID 并点击"测试获取单个分类"
6. 验证显示单个板块数据
7. 测试错误情况（无效 ID、未认证）

### Project Structure Notes

**对齐统一项目结构:**
- 页面放在 `app/api-test/` 目录（与项目结构一致）
- API 客户端放在 `lib/` 目录
- 使用 Tailwind CSS（项目已配置）
- 使用 TypeScript（项目已配置）

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture] - 前端架构规范
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] - 命名约定和模式
- [Source: _bmad-output/planning-artifacts/architecture.md#API Design] - API 端点设计

**项目上下文:**
- [Source: _bmad-output/project-context.md#Technology Stack] - Next.js 16.1.1, React 19.2.0, Tailwind CSS 4.x
- [Source: _bmad-output/project-context.md#Framework-Specific Rules] - React/Next.js 规范
- [Source: _bmad-output/project-context.md#Code Organization] - 前端文件组织

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1] - Epic 1: 数据库、算法与最小验证
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4] - Story 1.4 完整验收标准

### Previous Story Intelligence (Story 1.3)

**从 Story 1.3 学到的经验:**

1. **API 端点已创建:**
   - `GET /api/v1/sector-classifications` - 获取所有分类
   - `GET /api/v1/sector-classifications/{sector_id}` - 获取单个分类
   - 需要 JWT 认证（Authorization: Bearer <token>）

2. **API 响应格式:**
   - 成功响应: `{ data: [...], total: number }`
   - 单个响应: `{ data: {...} }`
   - 错误响应: `{ detail: "错误消息" }`

3. **认证集成:**
   - JWT token 存储在 localStorage
   - 请求头需要携带 Authorization
   - 401 错误表示未认证

4. **测试模式:**
   - Story 1.3 使用 FastAPI TestClient
   - 前端可以使用 fetch API 或 axios
   - 需要处理 CORS（如果前后端分离）

5. **性能验证:**
   - Story 1.3 API 响应时间 < 10ms
   - 前端应显示响应时间用于验证

**Git 智能摘要（最近10条提交）:**
- `8ba6e86` feat: 完成 Story 1.3 分类 API 端点并修复代码审查问题 ← Story 1.3
- `02f143d` docs: 完成 Story 1.2 缠论分类算法服务的代码审查
- `7e8ee3f` feat: 实现缠论板块分类算法服务 ← Story 1.2
- `fa31928` docs: 添加 BMAD 框架生成的项目文档和制品

**代码模式参考:**
- 查看现有页面组件（如 dashboard）了解页面模式
- 参考现有 API 客户端实现模式
- 使用 Tailwind CSS 进行样式设计

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 页面必须使用 'use client'（使用 hooks）
2. **页面路由** - 使用 `/api-test/sector-classification` 路径
3. **JWT 认证** - API 调用必须携带 Authorization 头
4. **错误处理** - 必须捕获并显示错误消息
5. **响应时间** - 必须显示 API 响应时间
6. **JSON 格式化** - 响应数据必须格式化显示
7. **状态码显示** - 必须显示 HTTP 状态码
8. **加载状态** - 请求期间按钮必须禁用
9. **Tailwind CSS** - 使用项目已配置的 Tailwind CSS
10. **类型安全** - 使用 TypeScript 定义接口

**依赖:**
- Story 1.3 (API 端点必须已实现)
- Next.js 16.1.1 (项目已配置)
- React 19.2.0 (项目已配置)
- Tailwind CSS 4.x (项目已配置)

**后续影响:**
- 此页面仅用于开发和测试
- Epic 2A 将创建正式的用户界面
- 可以保留用于后续 API 调试

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

**实现完成于: 2026-01-21**

创建了 API 测试页面用于验证板块分类 API 端点：

1. **API 客户端 (`sectorClassificationApi.ts`)**:
   - 实现了 `getAllClassifications()` 和 `getClassificationById()` 方法
   - 集成了 JWT 认证（从 localStorage 读取 accessToken）
   - 添加了带响应时间测量的辅助方法
   - 处理了 401/404/500 等错误情况

2. **测试页面 (`page.tsx`)**:
   - 位于 `/api-test/sector-classification` 路由
   - 提供两个测试功能：获取所有分类、获取单个分类
   - 显示状态码、响应时间和 JSON 数据
   - 实现了加载状态和错误处理
   - 使用 Tailwind CSS 实现响应式布局

3. **验收标准满足情况**:
   - ✅ 页面显示"API 测试页面"标题
   - ✅ 提供"测试获取所有分类"按钮
   - ✅ 点击后调用 GET /api/v1/sector-classifications
   - ✅ 显示原始 JSON 响应数据
   - ✅ 显示 HTTP 状态码
   - ✅ 显示响应时间（毫秒）
   - ✅ 提供单个分类查询功能（输入 sector_id）
   - ✅ 错误时显示明确的中文错误提示
   - ✅ 样式简洁，仅用于开发/测试验证

### File List

- `web/src/lib/sectorClassificationApi.ts` - 新增：板块分类 API 客户端
- `web/src/app/api-test/sector-classification/page.tsx` - 新增：API 测试页面

### Code Review Follow-ups (AI-Review)

**日期:** 2026-01-21
**审查者:** Claude Opus 4.5 (Code Review Agent)

**修复的问题:**
- [x] [AI-Review][HIGH] 修复 `getErrorMessage` 函数使用状态码判断而非字符串匹配 (page.tsx:64-77)
- [x] [AI-Review][MEDIUM] 添加 `sectorId` 输入验证，防止 NaN、负数和无效输入 (page.tsx:41-48)

**撤回的问题:**
- [x] [AI-Review][MEDIUM] 撤回类型安全问题 - 确认后端 `id` 字段确实是 `int` 类型
