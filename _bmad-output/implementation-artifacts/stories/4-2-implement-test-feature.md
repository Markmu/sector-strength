# Story 4.2: 实现分类算法测试功能

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 管理员（如王芳）,
I want 测试分类算法是否正常工作,
So that 我可以监控系统运行状态。

## Acceptance Criteria

**Given** 管理员在配置页面
**When** 点击"测试分类算法"按钮
**Then** 系统调用测试端点（POST /api/v1/admin/sector-classification/test）
**And** 显示"测试中..."加载状态
**When** 测试完成
**Then** 显示测试结果：
  - "测试完成！共计算 X 个板块分类。"
  - 成功数量：X 个
  - 失败数量：0 个
  - 计算耗时：X ms
**And** 如果测试失败，显示错误信息：
  - "测试失败：{具体错误}"
  - 提供"重试"按钮
**And** 所有操作记录到审计日志（NFR-SEC-006）

## Tasks / Subtasks

- [x] Task 1: 创建测试按钮组件 (AC: #)
  - [x] Subtask 1.1: 创建 `TestAlgorithmButton.tsx` 组件
  - [x] Subtask 1.2: 添加 'use client' 指令
  - [x] Subtask 1.3: 实现按钮点击处理逻辑
  - [x] Subtask 1.4: 显示加载状态（禁用按钮 + 旋转图标）
  - [x] Subtask 1.5: 使用项目自定义 Button 组件

- [x] Task 2: 创建测试结果展示组件 (AC: #)
  - [x] Subtask 2.1: 创建 `TestResultDisplay.tsx` 组件
  - [x] Subtask 2.2: 显示成功测试结果（总数、成功数、失败数、耗时）
  - [x] Subtask 2.3: 显示失败错误信息
  - [x] Subtask 2.4: 提供重试按钮（失败时）
  - [x] Subtask 2.5: 使用 Card 组件展示

- [x] Task 3: 实现前端 API 调用逻辑 (AC: #)
  - [x] Subtask 3.1: 创建 `useClassificationTest` hook
  - [x] Subtask 3.2: 实现测试端点调用（POST /api/v1/admin/sector-classification/test）
  - [x] Subtask 3.3: 处理加载状态（testing: boolean）
  - [x] Subtask 3.4: 处理成功响应（testResult）
  - [x] Subtask 3.5: 处理错误响应（error）

- [x] Task 4: 创建后端测试 API 端点 (AC: #)
  - [x] Subtask 4.1: 创建 `server/api/v1/endpoints/admin_sector_classifications.py`
  - [x] Subtask 4.2: 实现 POST /api/v1/admin/sector-classification/test 端点
  - [x] Subtask 4.3: 添加管理员权限验证（RBAC）
  - [x] Subtask 4.4: 调用分类算法服务进行测试
  - [x] Subtask 4.5: 返回测试结果（总数、成功数、失败数、耗时）

- [x] Task 5: 实现后端测试逻辑 (AC: #)
  - [x] Subtask 5.1: 复用 `sector_classification_service.py` 的分类算法
  - [x] Subtask 5.2: 获取所有板块列表
  - [x] Subtask 5.3: 对每个板块执行分类计算
  - [x] Subtask 5.4: 记录计算耗时（开始和结束时间）
  - [x] Subtask 5.5: 统计成功和失败数量

- [x] Task 6: 实现审计日志记录 (AC: #)
  - [x] Subtask 6.1: 记录测试操作（操作人、时间、操作类型）
  - [x] Subtask 6.2: 记录测试结果（成功数、失败数、耗时）
  - [x] Subtask 6.3: 记录错误信息（如果测试失败）
  - [x] Subtask 6.4: 存储到审计日志表或文件

- [x] Task 7: 集成测试按钮到配置页面 (AC: #)
  - [x] Subtask 7.1: 修改 `AdminConfigDisplay.tsx` 添加测试按钮
  - [x] Subtask 7.2: 修改配置页面添加测试结果展示区域
  - [x] Subtask 7.3: 集成 `useClassificationTest` hook
  - [x] Subtask 7.4: 处理测试结果显示
  - [x] Subtask 7.5: 处理重试逻辑

- [x] Task 8: 创建类型定义 (AC: #)
  - [x] Subtask 8.1: 创建 `ClassificationTestResult` 类型定义
  - [x] Subtask 8.2: 定义测试请求和响应接口
  - [x] Subtask 8.3: 定义错误类型

- [x] Task 9: 创建测试 (AC: #)
  - [x] Subtask 9.1: 测试测试按钮组件渲染和交互
  - [x] Subtask 9.2: 测试测试结果展示组件
  - [x] Subtask 9.3: 测试 hook 状态管理
  - [x] Subtask 9.4: 测试后端 API 端点（管理员权限、测试逻辑）
  - [x] Subtask 9.5: 测试审计日志记录

## Dev Notes

### Epic 4 完整上下文

**Epic 目标:** 为管理员提供分类参数查看、算法测试、运行状态监控和操作审计日志功能。

**FRs 覆盖:**
- FR20: 管理员可以测试分类算法
- FR24: 系统记录所有管理员操作到审计日志

**NFRs 相关:**
- NFR-SEC-002: 管理员功能必须有基于角色的访问控制（RBAC）
- NFR-SEC-003: 非管理员用户无法访问管理员功能
- NFR-SEC-006: 系统应记录所有管理员操作到审计日志
- NFR-SEC-007: 审计日志应包含操作人、时间、操作内容
- NFR-PERF-003: 分类计算时间 < 200ms（15个板块）

**依赖关系:**
- 依赖 Epic 1 完成（分类算法服务 `sector_classification_service.py` 已实现）
- 依赖 Story 4.1 完成（配置页面已创建，将在其上添加测试按钮）
- 依赖现有用户认证和 RBAC 系统

**后续影响:**
- Story 4.3 将创建监控面板
- Story 4.4 将实现审计日志查看

### 前置故事智能（Story 4.1）

**从 Story 4.1 学到的经验:**

1. **管理员页面模式:**
   - 使用 `DashboardLayout` 和 `DashboardHeader`
   - 权限验证使用 `useAuth` hook 的 `isAdmin` 属性
   - 非管理员用户显示友好的权限不足页面
   - 所有组件需要 'use client' 指令

2. **组件结构模式:**
   - 管理员组件放在 `components/admin/sector-classification/` 目录
   - 类型定义放在单独的 `.types.ts` 文件
   - 使用项目现有的 Card 组件（`@/components/ui/Card`）
   - 颜色主题：cyan-500 作为主色

3. **权限验证模式:**
   ```typescript
   const { user, isAuthenticated, isLoading, isAdmin } = useAuth()

   // 未登录用户重定向
   // 非管理员用户显示权限不足页面
   ```

4. **文件结构:**
   - 页面文件：`app/admin/sector-classification/config/page.tsx`
   - 组件文件：`components/admin/sector-classification/AdminConfigDisplay.tsx`
   - 类型文件：`components/admin/sector-classification/AdminConfigDisplay.types.ts`

**代码模式参考:**
- 查看 `web/src/app/admin/sector-classification/config/page.tsx` 了解管理员页面结构
- 查看 `web/src/components/admin/sector-classification/AdminConfigDisplay.tsx` 了解组件模式
- 查看 `web/src/components/admin/` 目录了解其他管理员组件模式

### 架构模式与约束

**前端技术栈:**
- Next.js 16.1.1 (App Router)
- React 19.2.0
- TypeScript 5 (strict mode)
- 项目自定义 UI 组件（Card, Button, Table）

**后端技术栈:**
- FastAPI 0.104+
- SQLAlchemy 2.0+
- PostgreSQL 14+

**关键设计决策:**

| 方面 | 设计决策 | 原因 |
|------|----------|------|
| API 端点 | POST /api/v1/admin/sector-classification/test | 符合 REST 规范，管理员端点 |
| 权限验证 | RBAC（仅管理员） | NFR-SEC-002, NFR-SEC-003 |
| 审计日志 | 记录测试操作和结果 | NFR-SEC-006, NFR-SEC-007 |
| 测试逻辑 | 复用现有分类算法服务 | 避免重复代码，确保一致性 |
| 前端状态 | useClassificationTest hook | 集中管理测试状态 |

**测试端点响应格式:**
```typescript
// 成功响应
{
  success: true,
  data: {
    total_count: 15,
    success_count: 15,
    failure_count: 0,
    duration_ms: 125,
    timestamp: "2026-01-26T10:30:00Z"
  }
}

// 失败响应
{
  success: false,
  error: {
    code: "TEST_FAILED",
    message: "分类计算失败：均线数据缺失",
    details: { ... }
  }
}
```

### 项目结构规范

**文件结构:**
```
web/src/
├── app/
│   └── admin/
│       └── sector-classification/
│           └── config/
│               └── page.tsx                      # 修改：添加测试按钮和结果展示
├── components/
│   └── admin/
│       └── sector-classification/
│           ├── TestAlgorithmButton.tsx           # 新增：测试按钮组件
│           ├── TestAlgorithmButton.types.ts      # 新增：按钮类型
│           ├── TestResultDisplay.tsx             # 新增：测试结果展示
│           ├── TestResultDisplay.types.ts        # 新增：结果类型
│           ├── useClassificationTest.ts          # 新增：测试 hook
│           ├── AdminConfigDisplay.tsx            # 修改：添加测试按钮
│           └── AdminConfigDisplay.types.ts       # 修改：添加测试相关类型
└── types/
    └── admin-test.ts                             # 新增：测试类型定义

server/
├── api/
│   └── v1/
│       └── endpoints/
│           └── admin_sector_classifications.py   # 新增：管理员 API 端点
├── services/
│   ├── sector_classification_service.py          # 已有：复用分类算法
│   └── audit_service.py                          # 可选：审计日志服务
└── tests/
    └── test_admin_sector_classifications.py      # 新增：端点测试
```

**命名约定:**
- 组件文件: `PascalCase.tsx`
- Hook 文件: `useClassificationTest.ts`
- 类型文件: `PascalCase.types.ts` 或 `kebab-case.ts`
- 测试文件: `test_*.py` (Python), `*.test.tsx` (TypeScript)

### TypeScript 类型定义

**测试结果类型:**
```typescript
// web/src/types/admin-test.ts
export interface ClassificationTestResult {
  /** 总板块数 */
  total_count: number
  /** 成功计算数 */
  success_count: number
  /** 失败计算数 */
  failure_count: number
  /** 计算耗时（毫秒） */
  duration_ms: number
  /** 测试时间戳 */
  timestamp: string
  /** 失败的板块列表（如果有） */
  failures?: TestFailure[]
}

export interface TestFailure {
  /** 板块 ID */
  sector_id: string
  /** 板块名称 */
  sector_name: string
  /** 错误信息 */
  error: string
}

export interface TestApiResponse {
  success: boolean
  data?: ClassificationTestResult
  error?: {
    code: string
    message: string
    details?: any
  }
}

export interface UseClassificationTestReturn {
  /** 测试状态 */
  testing: boolean
  /** 测试结果 */
  testResult: ClassificationTestResult | null
  /** 错误信息 */
  error: string | null
  /** 执行测试函数 */
  runTest: () => Promise<void>
  /** 重置测试状态 */
  reset: () => void
}
```

**组件 Props 类型:**
```typescript
// web/src/components/admin/sector-classification/TestAlgorithmButton.types.ts
export interface TestAlgorithmButtonProps {
  /** 是否正在测试 */
  testing: boolean
  /** 测试按钮点击回调 */
  onTest: () => void
  /** 是否禁用（可选） */
  disabled?: boolean
}

// web/src/components/admin/sector-classification/TestResultDisplay.types.ts
export interface TestResultDisplayProps {
  /** 测试结果 */
  result: ClassificationTestResult | null
  /** 错误信息 */
  error: string | null
  /** 重试回调 */
  onRetry: () => void
  /** 是否正在测试 */
  testing: boolean
}
```

### 组件实现

**useClassificationTest Hook:**
```typescript
// web/src/components/admin/sector-classification/useClassificationTest.ts
'use client'

import { useState, useCallback } from 'react'
import { apiClient } from '@/lib/apiClient'
import type {
  ClassificationTestResult,
  UseClassificationTestReturn
} from './useClassificationTest.types'

const TEST_ENDPOINT = '/api/v1/admin/sector-classification/test'

export function useClassificationTest(): UseClassificationTestReturn {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ClassificationTestResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runTest = useCallback(async () => {
    setTesting(true)
    setError(null)
    setTestResult(null)

    try {
      const response = await apiClient.post(TEST_ENDPOINT)

      if (response.success && response.data) {
        setTestResult(response.data)
      } else {
        setError(response.error?.message || '测试失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误，请重试')
    } finally {
      setTesting(false)
    }
  }, [])

  const reset = useCallback(() => {
    setTesting(false)
    setTestResult(null)
    setError(null)
  }, [])

  return {
    testing,
    testResult,
    error,
    runTest,
    reset,
  }
}
```

**TestAlgorithmButton 组件:**
```typescript
// web/src/components/admin/sector-classification/TestAlgorithmButton.tsx
'use client'

import { Button } from '@/components/ui/Button'
import { Play, Loader2 } from 'lucide-react'
import type { TestAlgorithmButtonProps } from './TestAlgorithmButton.types'

export function TestAlgorithmButton({
  testing,
  onTest,
  disabled = false,
}: TestAlgorithmButtonProps) {
  return (
    <Button
      onClick={onTest}
      disabled={disabled || testing}
      variant="primary"
      className="inline-flex items-center gap-2"
    >
      {testing ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>测试中...</span>
        </>
      ) : (
        <>
          <Play className="w-4 h-4" />
          <span>测试分类算法</span>
        </>
      )}
    </Button>
  )
}
```

**TestResultDisplay 组件:**
```typescript
// web/src/components/admin/sector-classification/TestResultDisplay.tsx
'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { CheckCircle2, XCircle, AlertCircle, RotateCcw } from 'lucide-react'
import type { TestResultDisplayProps } from './TestResultDisplay.types'

export function TestResultDisplay({
  result,
  error,
  onRetry,
  testing,
}: TestResultDisplayProps) {
  // 加载中状态
  if (testing) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
            <span className="ml-3 text-[#6c757d]">正在测试分类算法...</span>
          </div>
        </CardBody>
      </Card>
    )
  }

  // 错误状态
  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardBody>
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-red-900 mb-1">测试失败</h4>
              <p className="text-sm text-red-700 mb-4">{error}</p>
              <Button onClick={onRetry} variant="outline" size="sm">
                <RotateCcw className="w-4 h-4 mr-1" />
                重试
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    )
  }

  // 成功状态
  if (result) {
    const hasFailures = result.failure_count > 0

    return (
      <Card className={hasFailures ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'}>
        <CardHeader>
          <div className="flex items-center gap-2">
            {hasFailures ? (
              <AlertCircle className="w-5 h-5 text-amber-600" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            )}
            <h4 className="font-semibold text-[#1a1a2e]">
              {hasFailures ? '测试完成（部分失败）' : '测试完成'}
            </h4>
          </div>
        </CardHeader>
        <CardBody>
          <p className="text-lg mb-4">
            测试完成！共计算 <span className="font-bold">{result.total_count}</span> 个板块分类。
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-[#6c757d]">成功数量</p>
              <p className="text-2xl font-bold text-green-600">{result.success_count}</p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">失败数量</p>
              <p className={`text-2xl font-bold ${hasFailures ? 'text-red-600' : 'text-green-600'}`}>
                {result.failure_count}
              </p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">计算耗时</p>
              <p className="text-2xl font-bold text-cyan-600">{result.duration_ms} ms</p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">测试时间</p>
              <p className="text-sm font-semibold text-[#1a1a2e]">
                {new Date(result.timestamp).toLocaleString('zh-CN')}
              </p>
            </div>
          </div>

          {hasFailures && result.failures && result.failures.length > 0 && (
            <div className="border-t border-amber-200 pt-4">
              <p className="text-sm font-semibold text-red-900 mb-2">失败的板块：</p>
              <ul className="text-sm text-red-700 space-y-1">
                {result.failures.map((failure, index) => (
                  <li key={index}>
                    {failure.sector_name} - {failure.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardBody>
      </Card>
    )
  }

  // 初始状态（无结果）
  return null
}
```

### 后端 API 端点实现

**管理员 API 端点:**
```python
# server/api/v1/endpoints/admin_sector_classifications.py
"""
管理员板块分类 API 端点

提供管理员专用的分类功能：
- 测试分类算法
- 查看运行状态
- 数据修复
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import time

from src.db.database import get_db
from src.api.v1.endpoints.auth import get_current_user
from src.models.user import User
from src.models.sector import Sector
from src.services.sector_classification_service import SectorClassificationService
from src.services.audit_service import AuditService

router = APIRouter()

@router.post("/sector-classification/test")
async def test_classification_algorithm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试分类算法

    验证分类算法是否正常工作，对所有板块执行分类计算。

    权限：仅管理员

    返回：
        - total_count: 总板块数
        - success_count: 成功计算数
        - failure_count: 失败计算数
        - duration_ms: 计算耗时（毫秒）
        - timestamp: 测试时间戳
        - failures: 失败的板块列表（如果有）
    """
    # 验证管理员权限
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="权限不足：仅管理员可执行此操作"
        )

    # 记录审计日志
    audit_service = AuditService(db)
    await audit_service.log_action(
        user_id=current_user.id,
        action_type="test_classification",
        action_details="测试分类算法",
        ip_address="",  # 从 request 中获取
    )

    # 获取所有板块
    result = await db.execute(select(Sector))
    sectors = result.scalars().all()

    if not sectors:
        return {
            "success": True,
            "data": {
                "total_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "duration_ms": 0,
                "timestamp": datetime.now().isoformat(),
            }
        }

    # 执行分类测试
    start_time = time.time()
    service = SectorClassificationService(db)

    success_count = 0
    failure_count = 0
    failures = []

    for sector in sectors:
        try:
            # 调用分类算法
            await service.calculate_classification(sector.id)
            success_count += 1
        except Exception as e:
            failure_count += 1
            failures.append({
                "sector_id": str(sector.id),
                "sector_name": sector.name,
                "error": str(e),
            })

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    # 构建响应
    test_result = {
        "total_count": len(sectors),
        "success_count": success_count,
        "failure_count": failure_count,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
    }

    # 如果有失败，添加失败详情
    if failures:
        test_result["failures"] = failures

    # 记录测试结果到审计日志
    await audit_service.log_action(
        user_id=current_user.id,
        action_type="test_classification_result",
        action_details=f"测试完成：成功{success_count}个，失败{failure_count}个，耗时{duration_ms}ms",
        ip_address="",
    )

    return {
        "success": True,
        "data": test_result,
    }
```

### 集成到配置页面

**修改 AdminConfigDisplay 组件:**
```typescript
// web/src/components/admin/sector-classification/AdminConfigDisplay.tsx
'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { TestAlgorithmButton } from './TestAlgorithmButton'
import { TestResultDisplay } from './TestResultDisplay'
import { useClassificationTest } from './useClassificationTest'
import { ClassificationLevelDefinition } from './ClassificationLevelDefinition'
import type { AdminConfigDisplayProps } from './AdminConfigDisplay.types'

export function AdminConfigDisplay({ config }: AdminConfigDisplayProps) {
  const { testing, testResult, error, runTest, reset } = useClassificationTest()

  const handleTest = () => {
    reset() // 清除之前的测试结果
    runTest()
  }

  return (
    <div className="space-y-6">
      {/* 测试按钮区域 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">算法测试</h3>
          <p className="text-sm text-[#6c757d]">测试分类算法是否正常工作</p>
        </CardHeader>
        <CardBody>
          <TestAlgorithmButton testing={testing} onTest={handleTest} />
        </CardBody>
      </Card>

      {/* 测试结果展示 */}
      {(testing || testResult || error) && (
        <TestResultDisplay
          testing={testing}
          result={testResult}
          error={error}
          onRetry={handleTest}
        />
      )}

      {/* 配置参数展示 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">均线周期配置</h3>
          <p className="text-sm text-[#6c757d]">用于板块分类计算的均线周期（天）</p>
        </CardHeader>
        <CardBody>
          <div className="flex flex-wrap gap-2">
            {config.ma_periods.map((period) => (
              <span
                key={period}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-cyan-100 text-cyan-800 border border-cyan-200"
              >
                {period} 日线
              </span>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* 其他配置卡片... */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">判断基准天数</h3>
          <p className="text-sm text-[#6c757d]">用于判断反弹/调整状态的天数基准</p>
        </CardHeader>
        <CardBody>
          <p className="text-3xl font-bold text-cyan-600">{config.benchmark_days} 天</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">分类数量</h3>
          <p className="text-sm text-[#6c757d]">板块强弱分类的总类别数</p>
        </CardHeader>
        <CardBody>
          <p className="text-3xl font-bold text-cyan-600">{config.classification_count} 类</p>
        </CardBody>
      </Card>

      <ClassificationLevelDefinition definitions={config.level_definitions} />
    </div>
  )
}
```

### 审计日志服务

**审计日志服务（可选，如果不存在）:**
```python
# server/services/audit_service.py
"""
审计日志服务

记录所有管理员操作，包括：
- 操作人
- 操作时间
- 操作类型
- 操作内容
- IP 地址
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.audit_log import AuditLog

class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        user_id: str,
        action_type: str,
        action_details: str,
        ip_address: str,
    ):
        """
        记录管理员操作到审计日志

        Args:
            user_id: 用户 ID
            action_type: 操作类型（如 test_classification, view_config）
            action_details: 操作详情
            ip_address: IP 地址
        """
        audit_log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            action_details=action_details,
            ip_address=ip_address,
            created_at=datetime.now(),
        )

        self.db.add(audit_log)
        await self.db.commit()
```

**审计日志模型（如果不存在）:**
```python
# server/models/audit_log.py
"""
审计日志模型
"""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from src.db.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    action_details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)
```

### 测试要求

**前端测试:**
```typescript
// web/tests/components/admin/sector-classification/TestAlgorithmButton.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { TestAlgorithmButton } from '@/components/admin/sector-classification/TestAlgorithmButton'

describe('TestAlgorithmButton', () => {
  it('应该渲染测试按钮', () => {
    const mockOnTest = jest.fn()
    render(<TestAlgorithmButton testing={false} onTest={mockOnTest} />)

    expect(screen.getByText('测试分类算法')).toBeInTheDocument()
    expect(screen.getByRole('button')).not.toBeDisabled()
  })

  it('测试中时应该显示加载状态', () => {
    const mockOnTest = jest.fn()
    render(<TestAlgorithmButton testing={true} onTest={mockOnTest} />)

    expect(screen.getByText('测试中...')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('点击按钮应该调用 onTest', () => {
    const mockOnTest = jest.fn()
    render(<TestAlgorithmButton testing={false} onTest={mockOnTest} />)

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(mockOnTest).toHaveBeenCalledTimes(1)
  })
})

// web/tests/components/admin/sector-classification/TestResultDisplay.test.tsx
import { render, screen } from '@testing-library/react'
import { TestResultDisplay } from '@/components/admin/sector-classification/TestResultDisplay'

describe('TestResultDisplay', () => {
  it('应该显示成功测试结果', () => {
    const mockResult = {
      total_count: 15,
      success_count: 15,
      failure_count: 0,
      duration_ms: 125,
      timestamp: '2026-01-26T10:30:00Z',
    }

    render(
      <TestResultDisplay
        result={mockResult}
        error={null}
        onRetry={() => {}}
        testing={false}
      />
    )

    expect(screen.getByText(/测试完成/)).toBeInTheDocument()
    expect(screen.getByText(/15 个板块分类/)).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument() // 成功数量
    expect(screen.getByText('0')).toBeInTheDocument() // 失败数量
    expect(screen.getByText('125 ms')).toBeInTheDocument()
  })

  it('应该显示失败测试结果', () => {
    const mockError = '分类计算失败：均线数据缺失'

    render(
      <TestResultDisplay
        result={null}
        error={mockError}
        onRetry={() => {}}
        testing={false}
      />
    )

    expect(screen.getByText('测试失败')).toBeInTheDocument()
    expect(screen.getByText(mockError)).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
  })

  it('应该显示部分失败结果', () => {
    const mockResult = {
      total_count: 15,
      success_count: 13,
      failure_count: 2,
      duration_ms: 150,
      timestamp: '2026-01-26T10:30:00Z',
      failures: [
        { sector_id: '1', sector_name: '银行', error: '均线数据缺失' },
        { sector_id: '2', sector_name: '保险', error: '价格数据缺失' },
      ],
    }

    render(
      <TestResultDisplay
        result={mockResult}
        error={null}
        onRetry={() => {}}
        testing={false}
      />
    )

    expect(screen.getByText(/测试完成.*部分失败/)).toBeInTheDocument()
    expect(screen.getByText('13')).toBeInTheDocument() // 成功
    expect(screen.getByText('2')).toBeInTheDocument() // 失败
    expect(screen.getByText('银行 - 均线数据缺失')).toBeInTheDocument()
    expect(screen.getByText('保险 - 价格数据缺失')).toBeInTheDocument()
  })
})

// web/tests/components/admin/sector-classification/useClassificationTest.test.ts
import { renderHook, act, waitFor } from '@testing-library/react'
import { useClassificationTest } from '@/components/admin/sector-classification/useClassificationTest'
import { apiClient } from '@/lib/apiClient'

// Mock apiClient
jest.mock('@/lib/apiClient')

describe('useClassificationTest', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该执行测试并返回结果', async () => {
    const mockResult = {
      success: true,
      data: {
        total_count: 15,
        success_count: 15,
        failure_count: 0,
        duration_ms: 125,
        timestamp: '2026-01-26T10:30:00Z',
      },
    }

    apiClient.post = jest.fn().mockResolvedValue(mockResult)

    const { result } = renderHook(() => useClassificationTest())

    expect(result.current.testing).toBe(false)
    expect(result.current.testResult).toBe(null)

    await act(async () => {
      await result.current.runTest()
    })

    expect(result.current.testing).toBe(false)
    expect(result.current.testResult).toEqual(mockResult.data)
    expect(result.current.error).toBe(null)
  })

  it('应该处理测试失败', async () => {
    const mockError = {
      success: false,
      error: {
        code: 'TEST_FAILED',
        message: '分类计算失败：均线数据缺失',
      },
    }

    apiClient.post = jest.fn().mockResolvedValue(mockError)

    const { result } = renderHook(() => useClassificationTest())

    await act(async () => {
      await result.current.runTest()
    })

    expect(result.current.testResult).toBe(null)
    expect(result.current.error).toBe('分类计算失败：均线数据缺失')
  })

  it('应该重置测试状态', async () => {
    const mockResult = {
      success: true,
      data: {
        total_count: 15,
        success_count: 15,
        failure_count: 0,
        duration_ms: 125,
        timestamp: '2026-01-26T10:30:00Z',
      },
    }

    apiClient.post = jest.fn().mockResolvedValue(mockResult)

    const { result } = renderHook(() => useClassificationTest())

    await act(async () => {
      await result.current.runTest()
    })

    expect(result.current.testResult).not.toBe(null)

    act(() => {
      result.current.reset()
    })

    expect(result.current.testing).toBe(false)
    expect(result.current.testResult).toBe(null)
    expect(result.current.error).toBe(null)
  })
})
```

**后端测试:**
```python
# server/tests/test_admin_sector_classifications.py
"""
测试管理员板块分类 API 端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.db.database import get_db
from src.models.user import User
from src.api.v1.endpoints.auth import get_current_user

class MockAdminUser:
    id = "admin-id"
    username = "admin"
    email = "admin@example.com"
    is_admin = True

@pytest.mark.asyncio
async def test_classification_algorithm_success(db: AsyncSession, client: TestClient):
    """测试成功执行分类算法测试"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = client.post("/api/v1/admin/sector-classification/test")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "total_count" in data["data"]
    assert "success_count" in data["data"]
    assert "failure_count" in data["data"]
    assert "duration_ms" in data["data"]

    # 验证审计日志已记录
    # ...（根据实际审计日志实现验证）

@pytest.mark.asyncio
async def test_classification_algorithm_non_admin(db: AsyncSession, client: TestClient):
    """测试非管理员用户无法访问"""

    class MockNormalUser:
        id = "user-id"
        username = "user"
        email = "user@example.com"
        is_admin = False

    def mock_get_current_user():
        return MockNormalUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = client.post("/api/v1/admin/sector-classification/test")

    assert response.status_code == 403
    data = response.json()
    assert "权限不足" in data["detail"]
```

### Project Structure Notes

**对齐统一项目结构:**
- 管理员组件放在 `components/admin/sector-classification/` 目录
- 页面放在 `app/admin/sector-classification/config/` 目录
- 使用项目现有的 UI 组件（Card, Button）
- 遵循 TypeScript strict mode
- 复用 Story 4.1 的页面和组件模式

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式
- 使用项目现有的 Card 和 Button 组件（非 shadcn/ui）

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#API Design] - API 设计规范
- [Source: _bmad-output/planning-artifacts/architecture.md#Security Requirements] - 安全要求（RBAC）

**项目上下文:**
- [Source: _bmad-output/project-context.md#Framework-Specific Rules] - React/Next.js 规则
- [Source: _bmad-output/project-context.md#Security Rules] - 安全规则

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4] - Epic 4: 管理员功能与监控
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2] - Story 4.2 完整验收标准

**PRD 参考:**
- [Source: _bmad-output/planning-artifacts/prd.md#FR20] - FR20: 管理员可以测试分类算法
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 3] - Journey 3: 王芳 - 配置分类参数的管理员

**前置 Story:**
- [Source: _bmad-output/implementation-artifacts/stories/4-1-create-admin-config-page.md] - Story 4.1 实现详情

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 所有使用 hooks/state 的组件必须添加
2. **命名导出** - 使用 `export function`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **权限验证** - 前端和后端都必须验证管理员权限
5. **审计日志** - 所有测试操作必须记录到审计日志（NFR-SEC-006）
6. **错误处理** - 显示明确的错误信息和重试按钮
7. **性能要求** - 分类计算时间 < 200ms（NFR-PERF-003）
8. **TypeScript strict** - 不要使用 `any` 类型，正确定义接口
9. **复用服务** - 使用现有的 `sector_classification_service.py`
10. **中文文本** - 所有用户可见文本使用中文

**依赖:**
- Epic 1 完成（分类算法服务已实现）
- Story 4.1 完成（配置页面已创建）
- 现有认证系统（AuthContext）
- 现有 RBAC 系统（用户角色字段）

**后续影响:**
- Story 4.3 将创建监控面板
- Story 4.4 将实现审计日志查看
- Epic 4 完成后，所有管理员功能已就绪

### 性能与安全要求

**性能要求 (NFR-PERF-003):**
- 分类计算时间 < 200ms（15个板块）
- 测试端点响应时间 < 500ms
- 前端加载状态及时显示

**安全要求 (NFR-SEC-002, NFR-SEC-003, NFR-SEC-006, NFR-SEC-007):**
- 前端：检查用户角色字段
- 后端：API 端点必须验证管理员权限
- 审计日志：记录操作人、时间、操作内容
- 审计日志：保留至少 6 个月（NFR-SEC-008）

### 实现计划

**优先级 1: 创建类型定义**
1. 创建 `admin-test.ts` 类型文件
2. 定义 `ClassificationTestResult` 接口
3. 定义 `TestFailure` 接口
4. 定义 `TestApiResponse` 接口

**优先级 2: 创建前端组件**
1. 创建 `useClassificationTest.ts` hook
2. 创建 `TestAlgorithmButton.tsx` 组件
3. 创建 `TestResultDisplay.tsx` 组件

**优先级 3: 创建后端 API**
1. 创建 `admin_sector_classifications.py` 端点文件
2. 实现 POST /api/v1/admin/sector-classification/test
3. 添加管理员权限验证
4. 实现测试逻辑（复用分类算法服务）

**优先级 4: 实现审计日志**
1. 创建 `audit_service.py`（如果不存在）
2. 创建 `audit_log.py` 模型（如果不存在）
3. 记录测试操作
4. 记录测试结果

**优先级 5: 集成到配置页面**
1. 修改 `AdminConfigDisplay.tsx`
2. 添加测试按钮
3. 添加测试结果展示
4. 测试集成功能

**优先级 6: 创建测试**
1. 前端组件测试
2. Hook 测试
3. 后端 API 测试
4. 集成测试

**优先级 7: 验证和代码审查**
1. 验证所有验收标准
2. 运行测试套件
3. 代码质量检查
4. 安全审查（权限验证、审计日志）

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-26 - Story 创建完成

### File List

**需要创建的文件:**
- `web/src/types/admin-test.ts` - 测试类型定义
- `web/src/components/admin/sector-classification/TestAlgorithmButton.tsx` - 测试按钮组件
- `web/src/components/admin/sector-classification/TestAlgorithmButton.types.ts` - 按钮类型
- `web/src/components/admin/sector-classification/TestResultDisplay.tsx` - 结果展示组件
- `web/src/components/admin/sector-classification/TestResultDisplay.types.ts` - 结果类型
- `web/src/components/admin/sector-classification/useClassificationTest.ts` - 测试 hook
- `web/src/components/admin/sector-classification/useClassificationTest.types.ts` - hook 类型
- `server/api/v1/endpoints/admin_sector_classifications.py` - 后端 API 端点
- `server/services/audit_service.py` - 审计日志服务（如果不存在）
- `server/models/audit_log.py` - 审计日志模型（如果不存在）
- `server/tests/test_admin_sector_classifications.py` - 后端测试
- `web/tests/components/admin/sector-classification/TestAlgorithmButton.test.tsx` - 前端测试
- `web/tests/components/admin/sector-classification/TestResultDisplay.test.tsx` - 前端测试
- `web/tests/components/admin/sector-classification/useClassificationTest.test.ts` - hook 测试

**需要修改的文件:**
- `web/src/components/admin/sector-classification/AdminConfigDisplay.tsx` - 添加测试按钮和结果展示

**依赖文件（已存在）:**
- `web/src/app/admin/sector-classification/config/page.tsx` - 配置页面
- `web/src/components/admin/sector-classification/AdminConfigDisplay.tsx` - 配置展示组件
- `server/services/sector_classification_service.py` - 分类算法服务

## Change Log

### 2026-01-26

- 创建 Story 4.2 文档
- 定义测试功能规范
- 定义测试按钮和结果展示组件
- 定义后端 API 端点规范
- 定义审计日志要求（NFR-SEC-006）
- 定义权限验证要求（NFR-SEC-002, NFR-SEC-003）
- 定义性能要求（NFR-PERF-003）
- Story 状态: backlog → ready-for-dev
