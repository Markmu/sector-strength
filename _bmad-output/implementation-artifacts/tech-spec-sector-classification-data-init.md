---
title: '板块分类数据初始化与定时增量更新'
slug: 'sector-classification-data-init'
created: '2026-02-09'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.10+', 'FastAPI', 'SQLAlchemy 2.0+', 'APScheduler', 'PostgreSQL', 'React 19.2.0', 'Next.js 16.1.1', 'TypeScript 5', 'Pydantic 2.12.5']
files_to_modify: ['server/src/services/sector_classification_service.py', 'server/src/services/task_handlers.py', 'server/src/api/admin/sector_classifications.py (新建)', 'server/src/services/scheduler/job_manager.py', 'web/src/lib/api.ts', 'web/src/components/admin/DataSyncAdmin.tsx']
code_patterns: ['@TaskRegistry.register 装饰器注册任务', 'AsyncSession 依赖注入', 'require_admin 权限验证', 'async/await 异步模式', 'progress_callback 进度报告', 'classification_cache.clear_pattern 缓存清除']
test_patterns: ['pytest + pytest-asyncio', 'API 测试使用 fixture 获取 session', '组件测试使用 Testing Library', '任务处理器需要 mock manager 和 service']
---

# Tech-Spec: 板块分类数据初始化与定时增量更新

**Created:** 2026-02-09

## Overview

### Problem Statement

`SectorClassificationService` 只计算板块分类但**不保存结果到数据库**，导致前端板块分类页面无数据可展示。现有 API 只有查询和清除缓存功能，缺少数据初始化和增量更新的管理接口。

### Solution

1. **扩展 `SectorClassificationService`**：添加数据持久化方法（`save_classification_results()`、`initialize_classifications()`、`update_daily_classification()`）
2. **新增管理 API 端点**：
   - `POST /admin/sector-classification/initialize` - 历史数据初始化
   - `POST /admin/sector-classification/update-daily` - 每日增量更新
   - `GET /admin/sector-classification/status` - 获取数据状态
3. **定时任务**：在 `JobManager` 中添加每日 16:00 执行的增量更新任务
4. **前端 UI 扩展**：在 `DataSyncAdmin` 组件中添加板块分类管理卡片，显示初始化按钮、进度条、状态信息

### Scope

**In Scope:**
- 历史数据初始化功能（默认从每个板块最早日期开始，支持通过参数指定起始日期）
- 每日 16:00 定时增量更新（只计算当天最新日期的分类）
- 前端 UI 集成（初始化按钮、进度显示、状态反馈）
- 数据持久化到 `SectorClassification` 表
- 任务进度追踪和状态查询

**Out of Scope:**
- 分类算法修改（现有 `calculate_classification_level` 算法不变）
- 板块市场数据采集（已有数据更新任务负责）
- 均线数据计算（已有 MA 数据）
- 分类算法参数调整

## Context for Development

### Codebase Patterns

**异步模式 (SQLAlchemy 2.0+)**：
- 所有数据库操作必须使用 `async/await`
- 使用 `AsyncSession` 进行数据库会话管理
- 查询使用 `select().where()` 构造，执行使用 `await session.execute()`

**服务层模式**：
- 服务类接收 `AsyncSession` 作为构造参数
- 使用 `@timing_decorator` 装饰器测量执行时间
- 支持进度回调：`set_progress_callback(callback: Callable[[int, int, str], None])`

**API 端点模式**：
- 使用 FastAPI 路由：`router = APIRouter(prefix="/...", tags=["..."])`
- 管理员权限验证：`Depends(require_admin)`
- 响应使用 Pydantic 模型验证
- 中文文档字符串

**定时任务模式**：
- 使用 APScheduler 的 `AsyncIOScheduler`
- `CronTrigger` 用于定时触发（如 `CronTrigger(hour=16, minute=0)`）
- 任务方法为 `async def _method_name(self)`
- 在 `_register_jobs()` 中注册所有任务

**前端模式**：
- 使用 `adminApi` 调用后端管理接口
- 状态管理：`useState` 存储本地状态
- 消息提示：`showMessage(type, text)` 显示成功/错误
- 加载状态：`isLoading`、`refreshing` 控制 UI 状态

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `server/src/services/sector_classification_service.py` | 现有分类计算服务，需要扩展添加持久化方法 |
| `server/src/models/sector_classification.py` | `SectorClassification` 模型定义，包含所有字段 |
| `server/src/api/v1/sector_classifications.py` | 现有查询 API 参考，使用 `classification_cache` 缓存模式 |
| `server/src/api/admin/tasks.py` | 任务系统 API，参考如何创建异步任务 |
| `server/src/services/task_handlers.py` | 任务处理器注册模式，使用 `@TaskRegistry.register` |
| `server/src/services/task_executor.py` | TaskRegistry 和 TaskExecutor 实现 |
| `server/src/services/scheduler/job_manager.py` | 定时任务管理器，需要添加 16:00 任务 |
| `server/src/services/classification_cache.py` | 缓存服务，提供 `clear_pattern()` 方法 |
| `web/src/components/admin/DataSyncAdmin.tsx` | 数据管理 UI，需要扩展添加分类管理卡片 |
| `web/src/lib/api.ts` | 前端 API 客户端，需要添加分类管理方法 |
| `server/src/services/sector_strength_service.py` | 参考 `calculate_sector_strength_by_range()` 的范围计算模式 |

### Technical Decisions

1. **数据初始化策略**：
   - 默认：从每个板块的最早数据日期开始计算
   - 可选：支持通过 `start_date` 参数指定起始日期
   - 使用 `overwrite` 参数控制是否覆盖已有数据

2. **增量更新策略**：
   - 每日 16:00 执行，计算当天（`date.today()`）的分类
   - 只更新当天的数据，避免重复计算历史
   - 自动跳过已有数据的日期（除非 `overwrite=True`）

3. **进度追踪与异步执行**：
   - 使用现有的任务系统（`tasksApi`）进行异步进度追踪
   - API 立即返回 `task_id`，后台执行初始化
   - 实时报告当前处理的板块进度（如："正在处理：板块 A (1/100)"）
   - 前端可通过 `task_id` 查询实时进度

4. **断点续传与任务去重**：
   - **不使用单一事务**：每处理完一个板块的所有日期后 `flush()` 保存
   - **断点续传**：任务中断后重新执行，自动跳过已完成的板块和日期
   - **任务去重**：相同参数的初始化任务只能有一个运行中（通过任务状态表检查）
   - **失败处理**：失败时不回滚，下次重跑可覆盖已有数据

5. **缓存管理**：
   - 初始化/更新完成后自动清除相关缓存
   - 调用 `classification_cache.clear_pattern("classification:")`
   - API 响应中明确提示"已清除缓存"

6. **数据新鲜度检查**：
   - 初始化前验证当日市场数据是否存在
   - 定时任务检查数据新鲜度，如数据未就绪则跳过并记录警告日志

---

### Architecture Decision Records (ADR)

**ADR-001: 数据持久化策略** → 选择"每板块 flush"而非单一事务
- **决策**：不使用单一事务，每处理完一个板块的所有日期后 `flush()` 保存
- **理由**：大数据量场景下（可能数万条记录），可恢复性比完美原子性更重要
- **影响**：配合 `overwrite` 参数实现幂等性，支持断点续传和安全的重跑

**ADR-002: 任务系统集成** → 复用现有 tasksApi
- **决策**：使用现有的任务系统（`tasksApi`）进行异步进度追踪
- **理由**：DRY 原则，避免重复造轮子。前端已有 `tasksApi` 客户端
- **影响**：注册新任务类型 `init_sector_classifications`，复用进度查询、日志、取消机制

**ADR-003: 定时任务时机** → 数据新鲜度检查 + 跳过
- **决策**：每日 16:00 执行，但添加数据新鲜度检查，未就绪则跳过并警告
- **理由**：不改造任务系统的前提下最可靠方案。避免因数据延迟导致执行失败
- **影响**：定时任务添加数据就绪检查逻辑，管理员可通过日志发现问题

**ADR-004: 进度展示粒度** → 板块级别进度
- **决策**：进度回调报告当前板块名称和板块进度（current/total）
- **理由**：用户关心"还有多少板块"，日期级别信息变化过快导致 UI 闪烁
- **影响**：服务层每完成一个板块更新一次进度，前端显示"正在处理：板块 A (1/100)"

**ADR-005: 缓存清除时机** → 全部完成后清除
- **决策**：整个初始化完成后统一清除缓存
- **理由**：初始化是后台任务，用户通过任务进度查看，不依赖缓存数据。批量清除性能最优
- **影响**：服务层完成整个初始化后调用 `classification_cache.clear_pattern("classification:")`

## Implementation Plan

### Task Dependencies

```
Task 1 (服务扩展) ─────────────────────────┐
    ↓                                      │
Task 6 (注册任务处理器) ←──────────────────┘
    ↓
Task 2 (创建 API) ────→ Task 4 (前端 API 客户端)
    ↓                                      │
Task 3 (定时任务) ←─────────────────────────┘

Task 1 ────→ Task 3 (定时任务依赖服务方法)
Task 2 ────→ Task 5 (前端 UI)
```

**依赖说明**：
- Task 1 必须先完成（添加服务方法）才能注册任务处理器（Task 6）和创建定时任务（Task 3）
- Task 2 必须先完成（创建后端 API）才能添加前端 API 客户端（Task 4）和 UI 组件（Task 5）
- Task 6 和 Task 3 都依赖 Task 1 的服务方法

---

### Tasks

#### Task 1: 扩展 SectorClassificationService 添加数据持久化方法

**File**: `server/src/services/sector_classification_service.py`

**Actions**:
1. 添加 `_save_classification_result()` 私有方法：保存单个分类结果到 `SectorClassification` 表
   - 检查 `(sector_id, classification_date)` 组合是否已存在
   - 根据参数决定插入或跳过（`overwrite=False`）或删除后插入（`overwrite=True`）

2. 添加 `initialize_classifications()` 方法：
   - 参数：`start_date: Optional[date] = None`, `overwrite: bool = False`, `progress_callback: Optional[Callable] = None`
   - 逻辑：
     - 遍历所有板块，获取每个板块的日期范围
     - 外层循环板块，内层循环日期
     - 每完成一个板块的所有日期后 `flush()` 保存（支持断点续传）
     - 通过 `progress_callback` 报告进度：`(current_sector, total_sectors, sector_name)`
     - 数据不存在或 `overwrite=True` 时才计算和保存

3. 添加 `update_daily_classification()` 方法：
   - 参数：`target_date: Optional[date] = None`, `overwrite: bool = False`, `progress_callback: Optional[Callable] = None`
   - 逻辑：
     - **数据新鲜度检查**：查询 `DailyMarketData` 检查目标日期是否有市场数据
     - 如果数据不存在，返回 `{"success": False, "error": "市场数据未就绪"}`
     - 调用 `batch_calculate_all_sectors()` 保存当天结果
     - 完成后清除缓存（带错误处理）：
       ```python
       try:
           classification_cache.clear_pattern("classification:")
       except Exception as e:
           logger.warning(f"清除缓存失败: {e}")
       ```

4. 添加 `get_classification_status()` 方法：返回最新分类数据的统计信息
   - 返回：`{latest_date, total_sectors, by_level: {1-9: count}, by_state: {'反弹': count, '调整': count}}`

**Acceptance Criteria**:
- [ ] 能正确保存 `ClassificationResult` 到 `SectorClassification` 表
- [ ] 支持指定起始日期的历史初始化
- [ ] 支持单日增量更新
- [ ] 每完成一个板块后 `flush()` 保存，支持断点续传
- [ ] 相同参数的任务可安全重跑（跳过已有数据或覆盖）
- [ ] 完成后自动清除缓存

---

#### Task 2: 创建管理 API 端点

**File**: `server/src/api/admin/sector_classifications.py` (新建)

**Actions**:
1. 创建 API 路由：
   ```python
   router = APIRouter(prefix="/sector-classification", tags=["Admin - Sector Classification"])
   ```

2. 添加任务去重辅助函数：
   ```python
   async def _check_duplicate_task(
       manager: TaskManager,
       task_type: str,
       params: dict
   ) -> bool:
       """检查是否有相同参数的任务正在运行"""
       running_tasks = await manager.list_tasks(status="running", task_type=task_type)
       for task in running_tasks:
           task_params = await manager.get_task_params(task.task_id)
           if task_params == params:
               return True
       return False
   ```

3. 创建 `POST /admin/sector-classification/initialize` 端点：
   - 使用 `require_admin` 权限验证
   - 参数：`start_date: Optional[date]`, `overwrite: bool`
   - **任务去重检查**：调用 `_check_duplicate_task()` 检查是否有相同参数的任务正在运行
   - 如果有重复任务，返回错误提示
   - 通过 `TaskManager(session).create_task()` 创建异步任务
   - 任务类型：`init_sector_classifications`
   - 返回：`ApiResponse[TaskResponse]`

4. 创建 `POST /admin/sector-classification/update-daily` 端点：
   - 使用 `require_admin` 权限验证
   - 参数：`target_date: Optional[date]`, `overwrite: bool`
   - 任务类型：`update_sector_classification_daily`
   - 返回：`ApiResponse[TaskResponse]`

5. 创建 `GET /admin/sector-classification/status` 端点：
   - 使用 `require_admin` 权限验证
   - 查询 `SectorClassification` 表获取最新统计
   - 返回：`ApiResponse[ClassificationStatusResponse]`

6. 在 `server/src/api/admin/__init__.py` 中注册新路由

**Acceptance Criteria**:
- [ ] 所有端点使用 `require_admin` 权限验证
- [ ] 返回的任务 ID 可通过 `tasksApi` 查询进度
- [ ] 状态端点返回正确的统计信息
- [ ] API 文档字符串使用中文
- [ ] 路由正确注册到 admin router
- [ ] 任务去重检查正常工作
- [ ] 相同参数的任务被拒绝并返回友好提示

---

#### Task 3: 添加定时任务

**File**: `server/src/services/scheduler/job_manager.py`

**Actions**:
1. 在 `_register_jobs()` 方法中添加新任务（在现有任务之后）：
   ```python
   # 每日 16:00 执行板块分类更新
   self.scheduler.add_job(
       self._daily_sector_classification_update,
       trigger=CronTrigger(hour=16, minute=0),
       id='daily_sector_classification',
       name='板块分类每日更新',
       replace_existing=True,
       max_instances=1  # 防止并发执行
   )
   ```

2. 实现 `_daily_sector_classification_update()` 异步方法：
   ```python
   async def _daily_sector_classification_update(self):
       """每日板块分类更新任务

       注意：数据新鲜度检查已在服务层 update_daily_classification() 中统一处理
       """
       from src.services.sector_classification_service import SectorClassificationService
       from src.db.database import AsyncSessionLocal

       logger.info("[定时任务] 开始执行板块分类更新")

       try:
           async with AsyncSessionLocal() as session:
               service = SectorClassificationService(session)
               result = await service.update_daily_classification()

               if result.get("success"):
                   logger.info(f"[定时任务] 板块分类更新完成: {result}")
               else:
                   # 服务层返回失败（如数据未就绪），不抛出异常
                   logger.warning(f"[定时任务] 板块分类更新跳过: {result.get('error')}")
       except Exception as e:
           logger.error(f"[定时任务] 板块分类更新失败: {e}")
           raise  # 其他异常继续抛出，触发任务重试
   ```

**Acceptance Criteria**:
- [ ] 任务在每天 16:00 准时触发
- [ ] 使用独立的 AsyncSession
- [ ] 设置 `max_instances=1` 防止并发执行
- [ ] 数据新鲜度检查在服务层统一处理
- [ ] 服务层返回数据未就绪时记录警告但不抛出异常
- [ ] 其他异常被正确捕获和记录

---

#### Task 4: 扩展前端 API 客户端

**File**: `web/src/lib/api.ts`

**Actions**:
1. 在 `adminApi` 对象中添加：
   ```typescript
   // 板块分类管理
   initSectorClassification: (params?: { start_date?: string; overwrite?: boolean }) =>
     adminApiClient.post<{task_id: string; message: string}>('/admin/sector-classification/initialize', params),
   updateSectorClassificationDaily: (params?: { target_date?: string; overwrite?: boolean }) =>
     adminApiClient.post<{task_id: string; message: string}>('/admin/sector-classification/update-daily', params),
   getSectorClassificationStatus: () =>
     adminApiClient.get<any>('/admin/sector-classification/status'),
   ```

**Acceptance Criteria**:
- [ ] API 方法签名与后端端点匹配
- [ ] 使用 `adminApiClient` 实例

---

#### Task 5: 扩展 DataSyncAdmin UI 组件

**File**: `web/src/components/admin/DataSyncAdmin.tsx`

**Actions**:
1. 添加状态变量：
   ```typescript
   const [classificationStatus, setClassificationStatus] = useState<any>(null);
   ```

2. 添加时间估算辅助函数：
   ```typescript
   // 估算初始化所需时间
   const estimateTime = (sectorCount: number, daysCount: number): string => {
       const recordsPerSecond = 10; // 假设每秒处理 10 条记录
       const totalSeconds = (sectorCount * daysCount) / recordsPerSecond;
       if (totalSeconds > 3600) return `${(totalSeconds / 3600).toFixed(1)} 小时`;
       if (totalSeconds > 60) return `${(totalSeconds / 60).toFixed(0)} 分钟`;
       return `${totalSeconds.toFixed(0)} 秒`;
   };
   ```

3. 在 `loadAllData()` 中添加调用 `adminApi.getSectorClassificationStatus()`

4. 添加处理函数：
   - `handleInitClassification()` - 调用初始化 API
   - `handleUpdateDailyClassification()` - 调用每日更新 API
   - 在调用前显示确认对话框，包含时间估算

5. 添加新的 Card 组件"板块分类管理"：
   - 显示最新分类日期、板块数量统计
   - 初始化历史数据按钮（带时间估算提示）
   - 手动执行每日更新按钮
   - 进度轮询（每 5 秒查询一次任务状态，完成后停止）

**Acceptance Criteria**:
- [ ] 新卡片位于"系统健康状态"卡片之后
- [ ] 按钮点击后显示加载状态
- [ ] 成功/失败显示消息提示
- [ ] 数据加载时自动获取分类状态
- [ ] 初始化前显示时间估算提示
- [ ] 任务执行中每 5 秒轮询进度

---

#### Task 6: 注册任务处理器

**File**: `server/src/services/task_handlers.py`

**Actions**:
1. 在文件顶部添加导入：
   ```python
   from src.services.sector_classification_service import SectorClassificationService
   ```

2. 添加两个任务处理器（在现有处理器之后）：

   ```python
   @TaskRegistry.register("init_sector_classifications")
   async def init_sector_classifications_task(
       task_id: str,
       params: Dict[str, Any],
       manager: TaskManager,
   ) -> None:
       """板块分类历史初始化任务"""
       service = SectorClassificationService(manager.db)
       callback = await _make_progress_callback(manager, task_id)
       service.set_progress_callback(callback)

       start_date = params.get("start_date")
       overwrite = params.get("overwrite", False)

       await manager.log_message(task_id, "INFO", f"Starting sector classification initialization (start_date: {start_date})")

       result = await service.initialize_classifications(
           start_date=start_date,
           overwrite=overwrite
       )

       if result.get("success"):
           await manager.log_message(task_id, "INFO", f"Classification initialization completed: {result.get('total_sectors')} sectors processed")
       else:
           error_msg = result.get("error", "Unknown error")
           await manager.log_message(task_id, "ERROR", f"Classification initialization failed: {error_msg}")
           raise Exception(error_msg)

   @TaskRegistry.register("update_sector_classification_daily")
   async def update_sector_classification_daily_task(
       task_id: str,
       params: Dict[str, Any],
       manager: TaskManager,
   ) -> None:
       """板块分类每日增量更新任务"""
       service = SectorClassificationService(manager.db)
       callback = await _make_progress_callback(manager, task_id)
       service.set_progress_callback(callback)

       target_date = params.get("target_date")
       overwrite = params.get("overwrite", False)

       await manager.log_message(task_id, "INFO", f"Starting daily classification update (target_date: {target_date})")

       result = await service.update_daily_classification(
           target_date=target_date,
           overwrite=overwrite
       )

       if result.get("success"):
           await manager.log_message(task_id, "INFO", f"Daily classification update completed: {result.get('total_sectors')} sectors processed, cache cleared")
       else:
           error_msg = result.get("error", "Unknown error")
           await manager.log_message(task_id, "ERROR", f"Daily classification update failed: {error_msg}")
           raise Exception(error_msg)
   ```

**Acceptance Criteria**:
- [ ] 使用 `@TaskRegistry.register` 装饰器注册任务
- [ ] 任务类型名称与 API 中使用的一致
- [ ] 使用 `manager.db` 作为数据库会话
- [ ] 设置进度回调
- [ ] 记录任务日志
- [ ] 正确处理成功/失败状态

---

### Acceptance Criteria

**功能验收标准 (Given/When/Then 格式)**:

**AC-01: 历史数据初始化**
- [ ] Given 管理员已登录，当点击"初始化历史数据"按钮时，Then 应创建异步任务并返回 task_id
- [ ] Given 任务正在执行，当查询任务进度时，Then 应显示当前板块进度（如："正在处理：板块 A (1/100)"）
- [ ] Given 任务参数包含 start_date，当执行初始化时，Then 应从指定日期开始计算
- [ ] Given 数据库中已有部分数据且 overwrite=False，当重新执行初始化时，Then 应跳过已有数据的日期

**AC-02: 每日增量更新**
- [ ] Given 管理员已登录，当点击"执行每日更新"按钮时，Then 应创建异步任务计算当天分类
- [ ] Given 定时任务触发时间为 16:00，当时钟到达 16:00 时，Then 应自动执行每日更新任务
- [ ] Given 当日市场数据尚未采集，当定时任务执行时，Then 应跳过并记录警告日志
- [ ] Given 任务执行完成，当更新完成后，Then 应自动清除分类缓存

**AC-03: 断点续传与任务去重**
- [ ] Given 初始化任务执行中，当任务被中断后重新执行，Then 应自动跳过已完成的板块和日期
- [ ] Given 相同参数的初始化任务正在运行，当再次发起相同请求时，Then 应拒绝创建新任务
- [ ] Given 板块数据不足以计算分类，当处理该板块时，Then 应跳过并记录警告日志

**AC-04: 权限与安全**
- [ ] Given 非管理员用户，当访问管理 API 端点时，Then 应返回 403 Forbidden
- [ ] Given 未认证用户，当访问管理 API 端点时，Then 应返回 401 Unauthorized

**AC-05: 前端数据展示**
- [ ] Given 板块分类数据已初始化，当访问数据管理页面时，Then 应显示最新分类日期和板块统计
- [ ] Given 任务执行中，当查看任务状态时，Then 应显示实时进度条和当前处理信息
- [ ] Given 操作成功完成，当任务结束时，Then 应显示成功消息提示

**AC-06: 缓存管理**
- [ ] Given 初始化任务完成，当任务成功结束时，Then 应调用 `classification_cache.clear_pattern("classification:")`
- [ ] Given API 响应，当任务完成时，Then 响应消息应包含"已清除缓存"提示

**AC-07: 错误处理**
- [ ] Given 数据库操作失败，当捕获异常时，Then 应记录错误日志并标记任务为失败状态
- [ ] Given overwrite=True，当重新执行初始化时，Then 应覆盖已有数据

**Edge Cases 边界情况**:
- [ ] 板块无足够数据时跳过并记录日志
- [ ] 数据库操作失败时记录错误，下次重跑可覆盖已有数据
- [ ] 重复初始化时正确处理已有数据（根据 `overwrite` 参数：跳过或覆盖）
- [ ] 定时任务执行失败不影响后续执行
- [ ] 任务中断后重新执行，自动跳过已完成的板块和日期（断点续传）
- [ ] 相同参数的任务只能有一个运行中（任务去重）
- [ ] 定时任务检查数据新鲜度，如数据未就绪则跳过并记录警告
- [ ] 前端显示实时进度：当前板块/总板块数（如："正在处理：板块 A (1/100)"）

## Additional Context

### Dependencies

- **后端**:
  - `SQLAlchemy 2.0+` 异步 ORM
  - `FastAPI` Web 框架
  - `APScheduler` 定时任务
  - 现有 `SectorClassificationService`、`SectorClassification` 模型

- **前端**:
  - `React 19.2.0`
  - `adminApi` 客户端
  - 现有 `DataSyncAdmin` 组件

### Testing Strategy

**单元测试**:
- `test_sector_classification_service.py`: 测试新增的持久化方法
  - 测试保存单个分类结果
  - 测试历史初始化（mock 数据）
  - 测试每日更新
  - 测试状态查询

**集成测试**:
- `test_sector_classification_admin_api.py`: 测试新增的管理 API
  - 测试初始化端点（需要认证）
  - 测试每日更新端点
  - 测试状态查询端点
  - 测试权限验证

**前端测试**:
- `DataSyncAdmin.test.tsx`: 测试 UI 交互
  - 测试初始化按钮点击
  - 测试状态显示

### Notes

- **数据量大时的性能考虑**：历史初始化可能处理数万条记录，建议分批处理（每 100 条 flush 一次）
- **任务系统整合**：考虑使用现有的任务系统（`tasksApi`）进行进度追踪，而不是创建新的任务管理
- **时区问题**：定时任务使用服务器本地时区，确保与数据采集任务时区一致
- **缓存策略**：分类数据缓存时间建议设置为 24 小时，与数据更新周期一致
- **数据库索引**：确保 `(sector_id, classification_date)` 组合索引存在，以支持高效的去重检查
- **任务去重实现**：在创建任务前检查是否存在 `status='running'` 且 `params` 相同的任务
- **前端进度轮询**：建议每 5 秒轮询一次任务状态，任务完成后停止轮询
- **用户提示**：初始化前应估算并显示预计时间，让用户了解操作规模
- **缓存清除的副作用**：清除缓存后所有用户都会重新加载数据，考虑在低峰期执行大规模初始化
- **线程安全**：`TaskManager.update_progress()` 和 `TaskManager.log_message()` 从后台线程调用，已通过数据库连接池实现线程安全，无需额外处理
- **数据新鲜度检查统一**：在服务层 `update_daily_classification()` 中统一检查，定时任务和其他调用方无需重复检查
- **定时任务并发保护**：设置 `max_instances=1` 防止同一任务同时运行多个实例
- **缓存清除失败处理**：清除缓存失败时记录警告但不影响任务成功状态，因为数据已正确保存
