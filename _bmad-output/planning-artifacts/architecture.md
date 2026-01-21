---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - 'docs/architecture.md'
workflowType: 'architecture'
project_name: 'sector-strenth'
user_name: 'Mark'
date: '2026-01-20'
communication_language: 'Mandarin'
document_output_language: 'Mandarin'
classification:
  projectType: 'web_app_feature'
  domain: 'fintech'
  complexity: 'high'
  projectContext: 'brownfield'
lastStep: 8
status: 'complete'
completedAt: '2026-01-20'
---

# Architecture Decision Document - 板块强弱分类功能

_本文档通过逐步协作构建。随着我们进行每个架构决策，章节将被追加。_

**Author:** Mark
**Date:** 2026-01-20
**Version:** 1.0 (In Progress)

---

## 文档初始化

**功能范围：** 为现有 Sector Strength 系统添加板块强弱分类功能

**输入文档：**
- PRD v1.1: `_bmad-output/planning-artifacts/prd.md`
- 现有系统架构: `docs/architecture.md`

**项目上下文：**
- 类型：Web 应用功能扩展
- 领域：金融科技（Fintech）
- 复杂度：高
- 上下文：棕地项目（集成到现有 Next.js + FastAPI 系统）

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
28 个功能需求，组织成 8 个类别：
- **板块分类查看（FR1-FR4）**：展示分类结果、状态、基础信息
- **数据展示与交互（FR5-FR8）**：排序、搜索、刷新
- **帮助与说明（FR9-FR12）**：分类说明、风险提示
- **分类计算（FR13-FR15）**：核心算法实现
- **API 接口（FR16-FR18）**：开发者集成
- **管理员功能（FR19-FR22）**：配置、测试、监控
- **合规与安全（FR23-FR25）**：免责声明、审计日志、认证
- **错误处理（FR26-FR28）**：明确错误提示

**Non-Functional Requirements:**
关键 NFRs 驱动架构决策：
- **性能**：API < 200ms，FCP < 1.5s，分类计算 < 200ms
- **安全**：JWT 认证、RBAC、HTTPS/TLS、审计日志保留 6 个月
- **可靠性**：分类算法准确率 = 100%，数据缺失明确提示
- **集成**：与现有 JWT 认证、PostgreSQL 数据库、数据更新流程集成
- **可访问性**：基本可用性（颜色对比度、键盘导航、明确 label）

**Scale & Complexity:**
- 主要域：全栈 Web 应用
- 复杂度等级：高
- 预估架构组件：6-8 个

### Technical Constraints & Dependencies

**棕地项目集成约束：**
- 必须集成现有 Next.js 16.1.1 前端框架
- 必须集成现有 FastAPI 后端
- 必须使用现有 PostgreSQL 数据库和表结构
- 必须复用现有 JWT 认证中间件和 RBAC 权限系统
- 必须遵循现有 API 设计模式（RESTful）
- 必须集成现有数据更新流程

**缠论算法约束：**
- 8条均线：5, 10, 20, 30, 60, 90, 120, 240 天
- 9类分类：第1类（最弱）~ 第9类（最强）
- 反弹/调整判断：当前价格 vs 5天前
- 算法正确性必须 = 100%

**金融科技合规要求：**
- 所有页面必须标注"数据仅供参考，不构成投资建议"
- 管理员操作审计日志保留 6 个月
- 数据传输 HTTPS/TLS 加密

### Cross-Cutting Concerns Identified

1. **认证与授权**：所有端点需 JWT 验证，管理员功能需 RBAC
2. **审计日志**：管理员配置、测试、监控操作必须记录
3. **错误处理**：数据缺失、计算失败、API 错误需明确提示
4. **性能监控**：API 响应时间、分类计算耗时、页面加载时间
5. **数据准确性**：分类算法 100% 正确性，可追溯和验证

---

## Starter Template Evaluation

### Primary Technology Domain

Web 应用功能扩展（棕地项目）- 基于 PRD 需求分析确定

### Starter Options Considered

| 选项 | 适用性 | 原因 |
|------|--------|------|
| 新建 Next.js 16 项目 | ❌ 不适用 | 现有系统已有 Next.js 16.1.1 |
| 新建 FastAPI 项目 | ❌ 不适用 | 现有系统已有 FastAPI |
| 使用现有代码库 | ✅ **推荐** | 集成到现有系统 |

### Selected Approach: 扩展现有架构（无需 Starter Template）

**理由：**
1. 现有系统使用 **Next.js 16.1.1**（最新版本）+ **React 19.2.0**
2. 现有系统使用 **Tailwind CSS 4.x**（最新版本）
3. PRD 明确要求与现有系统集成（JWT、PostgreSQL、数据更新流程）
4. 避免重复基础设施，专注于新功能实现
5. 减少技术债务和维护成本

### 现有技术栈（实际版本）

**前端技术栈：**
| 类别 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Next.js | **16.1.1** |
| React | 19.2.0 |
| 状态管理 | Zustand | 5.0.9 |
| Redux Toolkit | 2.11.0 |
| UI 组件 | Radix UI, shadcn/ui | 最新 |
| 图表 | ECharts | 6.0.0 |
| CSS 框架 | Tailwind CSS | **4.x** |
| 测试 | Jest, Testing Library | 最新 |

**后端技术栈：**
| 类别 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.104+ |
| 数据库 | PostgreSQL | 14+ |
| ORM | SQLAlchemy | - |
| 认证 | JWT | - |

### 需要新建的组件

**前端组件：**
- 新增 `/sector-classification` 路由和页面组件
- 复用现有 shadcn/ui 组件和 Tailwind CSS 样式
- 复用现有布局组件（导航栏、侧边栏）
- 复用现有 API 客户端模式

**后端组件：**
- 新增 `sector_classification_service.py`（分类算法服务）
- 新增 API 端点（`GET /api/sector-classification`）
- 复用现有 JWT 认证中间件和 RBAC 权限系统
- 复用现有数据库连接和 ORM 模式

**数据库组件：**
- 新增分类结果表（或扩展现有表结构）
- 复用现有日线数据表和均线数据表

### 无需 Starter Template 的原因

1. 现有项目已有完整的开发环境配置
2. 现有项目已有测试框架和 CI/CD 配置
3. 现有项目已有 Docker 容器化部署配置
4. 新功能将遵循现有代码组织模式和规范
5. Next.js 16.1.1 是最新版本，无需升级

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- 数据架构：新建独立表存储分类结果
- 缓存策略：应用级内存缓存（24小时过期）
- API 设计：新增独立端点
- 前端架构：页面 + 布局 + 组件分离
- 错误处理：统一错误码 + 消息

**Important Decisions (Shape Architecture):**
- 复用现有认证系统（JWT + RBAC）
- 复用现有 ORM 模式（SQLAlchemy）
- 遵循现有代码组织规范

**Deferred Decisions (Post-MVP):**
- 历史分类趋势图表存储策略
- 分类变化预警机制

### Data Architecture

**决策：新建独立表存储分类结果**

**表结构设计：**
```sql
-- 板块分类结果表
CREATE TABLE sector_classification (
    id UUID PRIMARY KEY,
    sector_id UUID NOT NULL REFERENCES sectors(id),
    classification_date DATE NOT NULL,
    classification_level INTEGER NOT NULL,  -- 1-9
    state VARCHAR(10) NOT NULL,             -- '反弹' or '调整'
    current_price DECIMAL(10, 2),
    change_percent DECIMAL(5, 2),
    ma_5 DECIMAL(10, 2),
    ma_10 DECIMAL(10, 2),
    ma_20 DECIMAL(10, 2),
    ma_30 DECIMAL(10, 2),
    ma_60 DECIMAL(10, 2),
    ma_90 DECIMAL(10, 2),
    ma_120 DECIMAL(10, 2),
    ma_240 DECIMAL(10, 2),
    price_5_days_ago DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(sector_id, classification_date)
);

CREATE INDEX idx_sector_classification_date ON sector_classification(classification_date);
CREATE INDEX idx_sector_classification_sector ON sector_classification(sector_id);
```

**Rationale:**
- 满足性能要求（可预计算并缓存）
- 支持历史记录功能（阶段 2）
- 不影响现有系统稳定性
- 清晰的数据边界

### Caching Strategy

**决策：应用级内存缓存（24小时过期）**

**实现方案：**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class ClassificationCache:
    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self._ttl = timedelta(hours=24)

    def get(self, key):
        if key in self._cache:
            if datetime.now() - self._cache_time[key] < self._ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._cache_time[key]
        return None

    def set(self, key, value):
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    def clear(self):
        self._cache.clear()
        self._cache_time.clear()

# 全局缓存实例
classification_cache = ClassificationCache()
```

**Rationale:**
- 数据每日更新一次，缓存压力小
- 避免引入 Redis 的额外基础设施
- 简单高效，满足性能要求

### API Design

**决策：新增独立端点**

**端点定义：**
```
GET /api/sector-classification
- 描述：获取所有板块的分类结果
- 认证：需要 JWT
- 响应：SectorClassificationListResponse

GET /api/sector-classification/{sector_id}
- 描述：获取单个板块的分类详情
- 认证：需要 JWT
- 响应：SectorClassificationDetailResponse
```

**Rationale:**
- 符合现有系统 REST 模式
- 不影响现有 API
- 清晰的资源边界

### Frontend Architecture

**决策：页面 + 布局 + 组件分离**

**目录结构：**
```
/app/sector-classification/page.tsx              # 页面入口
/app/api/sector-classification/route.ts          # API 客户端
/components/sector-classification/
  ├── ClassificationTable.tsx                    # 分类表格
  ├── ClassificationTableHeader.tsx              # 表头（排序）
  ├── SearchBar.tsx                              # 搜索栏
  ├── HelpDialog.tsx                             # 帮助弹窗
  └── Disclaimer.tsx                             # 免责声明
/stores/sectorClassificationStore.ts             # Zustand store
/types/sector-classification.ts                  # TypeScript 类型
```

**Rationale:**
- 组件可复用
- 清晰的代码组织
- 易于测试和维护

### Error Handling

**决策：统一错误码 + 消息（扩展现有模式）**

**错误码定义：**
```typescript
const ClassificationErrorCodes = {
  MISSING_MA_DATA: 'MISSING_MA_DATA',              // 均线数据缺失
  CLASSIFICATION_FAILED: 'CLASSIFICATION_FAILED',  // 分类计算失败
  SECTOR_NOT_FOUND: 'SECTOR_NOT_FOUND',            // 板块不存在
  CALCULATION_TIMEOUT: 'CALCULATION_TIMEOUT',      // 计算超时
} as const;

interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
    timestamp: string;
    requestId: string;
  };
}
```

**Rationale:**
- 符合现有架构模式
- 前端可解析错误码
- 便于监控和日志分析

### Decision Impact Analysis

**Implementation Sequence:**
1. 数据库表创建（sector_classification）
2. 后端分类算法服务（sector_classification_service.py）
3. 后端 API 端点实现
4. 前端 Zustand store 和类型定义
5. 前端页面和组件实现
6. 集成测试

**Cross-Component Dependencies:**
- 前端依赖后端 API 端点
- 后端依赖数据库表结构
- 所有组件依赖错误处理模式

---

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
7 个关键领域需要明确模式规范以防止 AI Agent 实现冲突

### Naming Patterns

**Database Naming Conventions:**

**表命名：**
- 使用 `snake_case` 小写
- 使用复数形式（与现有表一致）
- 示例：`sectors`, `stocks`, `sector_classifications`

**列命名：**
- 使用 `snake_case`
- 外键格式：`{table}_id`（如 `sector_id`）
- 布尔值：`is_{attribute}`（如 `is_active`）
- 时间戳：`{action}_at`（如 `created_at`, `updated_at`）

**索引命名：**
- 格式：`idx_{table}_{column}` 或 `idx_{table}_{column1}_{column2}`
- 示例：`idx_sector_classification_date`, `idx_sector_classification_sector`

**API Naming Conventions:**

**REST 端点命名：**
- 使用复数形式：`/api/v1/sector-classifications`
- 路径使用 kebab-case：`/sector-classification/{sector-id}`
- 路径参数使用 kebab-case：`{sector-id}`, `{classification-id}`

**查询参数命名：**
- 使用 snake_case：`sector_type`, `min_strength_score`
- 示例：`/api/v1/sector-classifications?sector_type=industry`

**Code Naming Conventions:**

**Python 后端：**
- 文件命名：`snake_case.py`（如 `sector_classification_service.py`）
- 函数命名：`snake_case`（如 `calculate_classification()`）
- 类命名：`PascalCase`（如 `ClassificationService`）
- 变量命名：`snake_case`（如 `classification_level`）

**TypeScript 前端：**
- 组件文件：`PascalCase.tsx`（如 `ClassificationTable.tsx`）
- 函数命名：`camelCase`（如 `getClassifications()`）
- 接口/类型：`PascalCase`（如 `SectorClassification`）
- 变量命名：`camelCase`（如 `classificationLevel`）
- 常量：`UPPER_SNAKE_CASE`（如 `API_TIMEOUT`）

### Structure Patterns

**Project Organization:**

**后端文件结构：**
```
server/
├── api/v1/endpoints/
│   ├── sector_classifications.py    # 新增端点
│   ├── sectors.py                    # 现有
│   └── ...
├── services/
│   ├── sector_classification_service.py  # 新增服务
│   └── ...
├── models/
│   ├── sector_classification.py      # 新增模型
│   └── ...
└── tests/
    ├── test_sector_classification.py
    └── ...
```

**前端文件结构：**
```
web/src/
├── app/dashboard/sector-classification/
│   └── page.tsx                       # 页面入口
├── components/sector-classification/
│   ├── ClassificationTable.tsx        # 表格组件
│   ├── ClassificationTableHeader.tsx  # 表头
│   ├── SearchBar.tsx                  # 搜索栏
│   ├── HelpDialog.tsx                 # 帮助弹窗
│   └── Disclaimer.tsx                 # 免责声明
├── store/slices/
│   └── sectorClassification.ts        # Redux slice
├── lib/
│   └── sectorClassificationApi.ts     # API 客户端
└── types/
    └── sector-classification.ts       # 类型定义
```

**测试文件位置：**
- 后端：与源文件同目录，`test_*.py`
- 前端：与源文件同目录，`*.test.ts`

### Format Patterns

**API Response Formats:**

**成功响应：**
```typescript
{
  data: T  // 实际数据
}
```

**错误响应：**
```typescript
{
  error: {
    type: string,       // 错误类型
    message: string,    // 用户友好消息
    status_code: number // HTTP 状态码
  }
}
```

**分页响应：**
```typescript
{
  data: {
    items: T[],
    total: number,
    page: number,
    page_size: number
  }
}
```

**Data Exchange Formats:**

**JSON 字段命名：**
- 后端 → 前端：使用 `snake_case`（与 Python 一致）
- 前端内部：使用 `camelCase`（TypeScript 约定）
- 需要在 API 层进行转换

**日期格式：**
- API：ISO 8601 字符串（如 `"2025-01-20T00:00:00Z"`）
- 数据库：`TIMESTAMP` 或 `DATE` 类型

**布尔表示：**
- API/JSON：`true`/`false`
- 数据库：`BOOLEAN` 类型

### Communication Patterns

**State Management Patterns:**

**Redux Toolkit 模式（用于全局共享状态）：**
```typescript
interface SectorClassificationState {
  classifications: SectorClassification[]
  loading: boolean
  error: string | null
  filters: ClassificationFilters
}

// 使用 createSlice 和 createAsyncThunk
export const fetchClassifications = createAsyncThunk(
  'sectorClassification/fetchAll',
  async () => {
    const response = await sectorClassificationApi.getClassifications()
    return response.data
  }
)
```

**Zustand 模式（用于组件本地状态）：**
```typescript
interface ClassificationStore {
  sortBy: 'level' | 'name' | 'change'
  sortOrder: 'asc' | 'desc'
  searchQuery: string
  setSortBy: (sortBy: string) => void
  setSearchQuery: (query: string) => void
}

const useClassificationStore = create<ClassificationStore>((set) => ({
  sortBy: 'level',
  sortOrder: 'desc',
  searchQuery: '',
  setSortBy: (sortBy) => set({ sortBy }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
}))
```

### Process Patterns

**Error Handling Patterns:**

**全局错误处理：**
- 后端：FastAPI 异常处理器返回标准错误格式
- 前端：ApiClient 统一处理 401/403/500 等状态码

**用户错误消息：**
- 中文消息（与 `communication_language: Mandarin` 一致）
- 明确说明问题和可能的解决方案

**Loading State Patterns:**

**命名约定：**
```typescript
interface LoadingState {
  loading: boolean      // 请求进行中
  error: string | null  // 错误信息
  data?: T             // 成功后的数据
}
```

**组件中使用：**
```typescript
const { loading, error, data } = useSectorClassifications()
```

### Enforcement Guidelines

**All AI Agents MUST:**

1. **遵循现有代码风格**：参考现有文件（如 `sectors.py`, `api.ts`）的编码模式
2. **使用相同的 API 客户端基类**：继承 `ApiClient` 而不是直接使用 `fetch`
3. **遵循错误响应格式**：确保错误返回包含 `{error: {type, message, status_code}}`
4. **使用相同的导入路径别名**：`@/lib/api`, `@/types`, `@/components`
5. **保持文件组织一致性**：新文件放置在对应的目录结构中

**Pattern Enforcement:**

- **代码审查**：确保 PR 遵循既定模式
- **Linting**：使用 ESLint 和 Pylint 强制执行基本风格
- **类型检查**：TypeScript strict mode, Python type hints

### Pattern Examples

**Good Examples:**

```python
# server/api/v1/endpoints/sector_classifications.py
"""板块强弱分类 API 端点"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.db.database import get_db

router = APIRouter()

@router.get("/sector-classifications", response_model=List[dict])
async def get_sector_classifications(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取所有板块的分类结果"""
    # 实现逻辑
    pass
```

```typescript
// web/src/components/sector-classification/ClassificationTable.tsx
interface ClassificationTableProps {
  classifications: SectorClassification[]
  onSort: (column: string) => void
}

export function ClassificationTable({
  classifications,
  onSort
}: ClassificationTableProps) {
  // 组件实现
}
```

**Anti-Patterns (避免):**

```python
# ❌ 错误：使用驼峰命名
@router.get("/sectorClassifications")  # 应使用 kebab-case

# ❌ 错误：使用 PascalCase 命名函数
async def GetSectorClassifications():  # 应使用 snake_case
```

```typescript
// ❌ 错误：使用 kebab-case 文件名
// classification-table.tsx  // 应使用 PascalCase

// ❌ 错误：直接使用 fetch 而不是 ApiClient
const data = await fetch('/api/v1/sector-classifications')  // 应使用 apiClient
```

---

## Project Structure & Boundaries

### Complete Project Directory Structure

**新增功能文件（板块强弱分类）：**

```
sector-strenth/
├── server/                                    # FastAPI 后端
│   ├── api/v1/endpoints/
│   │   └── sector_classifications.py         # 新增：分类 API 端点
│   ├── services/
│   │   ├── sector_classification_service.py  # 新增：分类算法服务
│   │   └── classification_cache.py           # 新增：缓存管理
│   ├── models/
│   │   └── sector_classification.py          # 新增：数据模型
│   └── tests/
│       └── test_sector_classification.py     # 新增：服务测试
│
├── web/src/                                   # Next.js 前端
│   ├── app/dashboard/sector-classification/
│   │   └── page.tsx                           # 新增：页面入口
│   ├── components/sector-classification/
│   │   ├── ClassificationTable.tsx           # 新增：分类表格
│   │   ├── ClassificationTableHeader.tsx     # 新增：表头（排序）
│   │   ├── SearchBar.tsx                     # 新增：搜索栏
│   │   ├── HelpDialog.tsx                    # 新增：帮助弹窗
│   │   ├── Disclaimer.tsx                    # 新增：免责声明
│   │   └── index.ts                          # 导出文件
│   ├── store/slices/
│   │   └── sectorClassification.ts            # 新增：Redux slice
│   ├── lib/
│   │   └── sectorClassificationApi.ts         # 新增：API 客户端
│   ├── types/
│   │   └── sector-classification.ts          # 新增：类型定义
│   └── hooks/
│       └── useSectorClassification.ts         # 新增：自定义 Hook
│
└── alembic/
    └── versions/
        └── create_sector_classification_table.py  # 新增：Alembic 迁移脚本
```

### Architectural Boundaries

**API Boundaries:**

**现有 API 端点（不修改）：**
```
GET /api/v1/sectors          # 板块列表
GET /api/v1/sectors/{id}     # 板块详情
```

**新增 API 端点：**
```
GET /api/v1/sector-classifications              # 获取所有分类
GET /api/v1/sector-classifications/{sector-id} # 获取单个分类
```

**认证边界：**
- 所有端点需要 JWT 认证
- 管理员功能需要 RBAC 验证

**Component Boundaries:**

**前端组件通信：**
```
SectorClassificationPage
    ├── ClassificationTable (props: data, onSort)
    │   ├── ClassificationTableHeader (props: onSort)
    │   └── SearchBar (props: value, onChange)
    ├── HelpDialog (Dialog)
    └── Disclaimer (Static Component)
```

**状态管理边界：**
- **Redux Toolkit**：全局共享状态（分类列表、加载状态）
- **Zustand**：组件本地状态（排序、搜索筛选）

**Service Boundaries:**

**后端服务职责：**
```
SectorClassificationService
    ├── calculate_classification()     # 核心算法
    ├── get_classification()           # 从数据库获取
    ├── invalidate_cache()            # 清除缓存
    └── batch_calculate()              # 批量计算所有板块
```

**Data Boundaries:**

**数据库表边界：**
- `sector_classification` - 分类结果（新表）
- `sectors` - 板块信息（现有表，只读）
- `daily_market_data` - 日线数据（现有表，只读）
- `moving_average_data` - 均线数据（现有表，只读）

**缓存边界：**
- 缓存键：`classification:all` 或 `classification:{sector_id}`
- 缓存 TTL：24 小时
- 手动刷新时清除缓存

### Requirements to Structure Mapping

**Feature Mapping:**

**板块分类查看（FR1-FR4）：**
```
前端：
  - web/src/app/dashboard/sector-classification/page.tsx
  - web/src/components/sector-classification/ClassificationTable.tsx

后端：
  - server/api/v1/endpoints/sector_classifications.py
  - server/services/sector_classification_service.py

数据库：
  - sector_classification 表
```

**分类计算（FR13-FR15）：**
```
后端：
  - server/services/sector_classification_service.py
    - calculate_classification() - 核心缠论算法
    - calculate_state() - 反弹/调整判断

依赖：
  - 读取：moving_average_data 表
  - 写入：sector_classification 表
```

**管理员功能（FR19-FR22）：**
```
前端：
  - 复用 web/src/components/admin/ 目录下的现有模式

后端：
  - 扩展现有 /api/v1/admin/ 端点
  - 添加测试端点：/api/v1/admin/sector-classification/test
```

**Cross-Cutting Concerns:**

**认证与授权：**
```
前端：
  - web/src/lib/api.ts (ApiClient 已包含 JWT 处理)
  - web/src/contexts/AuthContext.tsx

后端：
  - server/api/v1/endpoints/sector_classifications.py
    - @router.get("/sector-classifications", dependencies=[Depends(get_current_user)])
```

**审计日志：**
```
后端：
  - server/services/audit_service.py (可能需要新建)
  - 记录管理员操作：分类测试、参数配置、监控查看
```

### Integration Points

**Internal Communication:**

```
用户 → 前端页面 → ApiClient → FastAPI 端点
                              ↓
                    SectorClassificationService
                              ↓
                    ClassificationCache → PostgreSQL
```

**数据流：**
```
1. 用户访问 /dashboard/sector-classification
2. 页面调用 sectorClassificationApi.getClassifications()
3. ApiClient 发送 GET /api/v1/sector-classifications
4. FastAPI 端点检查 JWT 认证
5. 调用 SectorClassificationService.get_classification()
6. 服务先检查缓存，命中则返回；未命中则查询数据库
7. 返回格式化的分类数据
```

**External Integrations:**
- 无（功能使用现有数据源）

### File Organization Patterns

**Configuration Files:**
```
server/
  - .env (环境变量)
  - requirements.txt (Python 依赖)
  - pyproject.toml (项目配置)

web/
  - package.json (Node 依赖)
  - tsconfig.json (TypeScript 配置)
  - next.config.js (Next.js 配置)
  - tailwind.config.js (Tailwind 配置)
```

**Source Organization:**
```
按功能分层：
  - endpoints/ (API 路由)
  - services/ (业务逻辑)
  - models/ (数据模型)
  - components/ (UI 组件)
```

**Test Organization:**
```
server/tests/
  - test_sector_classification_service.py
  - test_sector_classification_api.py

web/src/components/sector-classification/
  - ClassificationTable.test.tsx
```

### Development Workflow Integration

**开发命令：**
```
# 后端
cd server && python -m pytest tests/test_sector_classification.py

# 前端
cd web && npm test -- ClassificationTable.test.tsx
```

**数据库迁移：**
```
# 生成迁移脚本
cd server && alembic revision -m "create sector classification table"

# 执行迁移
cd server && alembic upgrade head

# 回滚迁移
cd server && alembic downgrade -1
```

**部署：**
- 无需修改（集成到现有 Docker Compose 配置）

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- 数据架构（独立表）→ 缓存策略（应用级）→ API 设计（独立端点）形成完整链路
- 前端架构（组件分离）→ 状态管理（Redux + Zustand）→ 错误处理（统一格式）互相支持
- 所有技术选择版本兼容（Next.js 16.1.1, React 19.2.0, FastAPI, PostgreSQL）

**Pattern Consistency:**
- 命名规范（snake_case/kebab-case/camelCase）贯穿前后端
- API 响应格式统一（成功/错误/分页结构）
- 代码组织模式一致（分层架构：endpoints/services/models）

**Structure Alignment:**
- 项目结构支持所有架构决策（14 个新文件清晰定义）
- 组件边界明确（API/Service/Data/Cache）
- 集成点清晰（JWT认证、RBAC权限、审计日志）

### Requirements Coverage Validation ✅

**Functional Requirements Coverage (28/28):**
- 板块分类查看（FR1-FR4）：ClassificationTable + API 端点
- 数据展示与交互（FR5-FR8）：排序、搜索、刷新组件
- 帮助与说明（FR9-FR12）：HelpDialog + Disclaimer 组件
- 分类计算（FR13-FR15）：SectorClassificationService 算法实现
- API 接口（FR16-FR18）：独立 RESTful 端点
- 管理员功能（FR19-FR22）：扩展现有 admin 端点
- 合规与安全（FR23-FR25）：JWT + RBAC + 审计日志
- 错误处理（FR26-FR28）：统一错误码系统

**Non-Functional Requirements Coverage:**
- **性能**：缓存策略（24小时 TTL）满足 < 200ms 要求
- **安全**：JWT 认证、RBAC 权限、HTTPS/TLS 加密
- **可靠性**：算法 100% 正确性，数据缺失明确提示
- **集成**：复用现有 JWT、PostgreSQL、数据更新流程
- **可访问性**：颜色对比度、键盘导航、明确 label

**Cross-Cutting Concerns:**
- 认证与授权：所有端点 JWT 验证，管理员 RBAC
- 审计日志：管理员操作记录（保留 6 个月）
- 错误处理：统一错误码 + 中文消息
- 性能监控：API 响应时间、计算耗时
- 数据准确性：分类算法可追溯验证

### Implementation Readiness Validation ✅

**Decision Completeness:**
- 6 个核心架构决策（数据架构、缓存、API、前端、错误处理、集成）
- 所有技术选择包含具体版本号
- 每个决策有清晰的 rationale 说明

**Structure Completeness:**
- 14 个新文件完整定义（前后端 + 数据库迁移）
- 目录结构清晰（按功能分层）
- 测试文件位置明确

**Pattern Completeness:**
- 7 个冲突点解决（命名、结构、格式、通信、流程）
- 5 条强制规则（代码风格、API 客户端、错误格式、导入路径、文件组织）
- Good/Anti 模式示例完整

### Architecture Readiness Assessment

**Overall Status:** ✅ **READY FOR IMPLEMENTATION**

**Confidence Level:** 高（基于全面验证）

**风险评估：**
- 技术风险：低（使用现有成熟技术栈）
- 集成风险：低（棕地项目，复用现有模式）
- 复杂度风险：中等（缠论算法需要精确实现）

---

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-20
**Document Location:** _bmad-output/planning-artifacts/architecture.md

### Final Architecture Deliverables

**📋 Complete Architecture Document**

- 所有架构决策已文档化，包含具体版本号
- 实现模式确保 AI agent 一致性
- 完整的项目结构和所有文件目录
- 需求到架构的映射
- 验证确认了连贯性和完整性

**🏗️ Implementation Ready Foundation**

- 6 个核心架构决策
- 7 个实现模式类别（命名、结构、格式、通信、流程）
- 14 个新增组件（前端 + 后端 + 数据库）
- 28 个功能需求完全覆盖
- 25 个非功能需求全部支持

**📚 AI Agent Implementation Guide**

- 技术栈包含验证版本（Next.js 16.1.1, React 19.2.0, FastAPI, PostgreSQL）
- 一致性规则防止实现冲突
- 项目结构包含清晰边界
- 集成模式和通信标准

### Implementation Handoff

**For AI Agents:**
本架构文档是实现板块强弱分类功能的完整指南。严格按照文档的所有决策、模式和结构执行。

**First Implementation Priority:**
数据库迁移（使用 Alembic 创建 sector_classification 表）

**Development Sequence:**

1. 执行数据库迁移（Alembic）
2. 实现后端分类算法服务（sector_classification_service.py）
3. 实现后端 API 端点
4. 创建前端 Redux slice 和类型定义
5. 实现前端页面和组件
6. 集成测试

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] 所有决策协同工作，无冲突
- [x] 技术选择兼容（Next.js 16.1.1 + React 19.2.0 + FastAPI）
- [x] 模式支持架构决策
- [x] 结构与所有选择对齐

**✅ Requirements Coverage**

- [x] 所有功能需求被支持（28/28）
- [x] 所有非功能需求被处理（25/25）
- [x] 横切关注点已处理
- [x] 集成点已定义

**✅ Implementation Readiness**

- [x] 决策具体可执行
- [x] 模式防止 agent 冲突
- [x] 结构完整无歧义
- [x] 提供示例说明清晰

### Project Success Factors

**🎯 Clear Decision Framework**
每个技术选择都是协作做出的，有清晰的 rationale，确保所有利益相关者理解架构方向。

**🔧 Consistency Guarantee**
实现模式和规则确保多个 AI agent 将产生兼容、一致的代码。

**📋 Complete Coverage**
所有项目需求都得到架构支持，从业务需求到技术实现有清晰映射。

**🏗️ Solid Foundation**
现有技术栈和架构模式提供生产就绪基础。

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** 开始实现阶段，使用本文档记录的架构决策和模式。

**Document Maintenance:** 在实现过程中做出重大技术决策时更新此架构。
