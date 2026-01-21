# Story 1.5: 集成应用级缓存机制

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 后端开发者,
I want 实现 24 小时 TTL 的应用级缓存,
so that 减少数据库查询并提升性能。

## Acceptance Criteria

**Given** 分类 API 端点已实现 (Story 1.3)
**When** 首次请求分类数据
**Then** 系统从数据库查询并缓存结果
**And** 缓存键格式: "classification:all" 或 "classification:{sector_id}"
**And** 缓存 TTL = 24 小时
**When** 24 小时内再次请求相同数据
**Then** 系统从缓存返回结果（不查询数据库）
**And** 响应时间 < 50ms (缓存命中)
**When** 缓存过期后再次请求
**Then** 系统从数据库重新查询并更新缓存
**And** 提供手动清除缓存接口 (用于数据更新后)

## Tasks / Subtasks

- [x] Task 1: 创建缓存服务模块 (AC: 全部)
  - [x] Subtask 1.1: 创建 `server/src/services/classification_cache.py`
  - [x] Subtask 1.2: 实现 `ClassificationCache` 类
  - [x] Subtask 1.3: 实现 `get()` 方法（带 TTL 检查）
  - [x] Subtask 1.4: 实现 `set()` 方法（存储数据和时间戳）
  - [x] Subtask 1.5: 实现 `clear()` 方法（清除缓存）
  - [x] Subtask 1.6: 实现 `clear_pattern()` 方法（按模式清除）

- [x] Task 2: 集成缓存到 API 端点 (AC: 全部)
  - [x] Subtask 2.1: 修改 `sector_classifications.py` 端点
  - [x] Subtask 2.2: 在 `get_sector_classifications()` 中集成缓存
  - [x] Subtask 2.3: 在 `get_sector_classification()` 中集成缓存
  - [x] Subtask 2.4: 使用全局缓存实例
  - [x] Subtask 2.5: 添加缓存命中/未命中日志

- [x] Task 3: 实现缓存清除接口 (AC: 全部)
  - [x] Subtask 3.1: 创建 `POST /api/v1/sector-classifications/cache/clear` 端点
  - [x] Subtask 3.2: 实现清除所有缓存功能
  - [x] Subtask 3.3: 实现清除单个板块缓存功能
  - [x] Subtask 3.4: 添加管理员权限验证（RBAC）
  - [x] Subtask 3.5: 添加中文文档字符串

- [x] Task 4: 创建单元测试 (AC: 全部)
  - [x] Subtask 4.1: 创建 `server/tests/test_classification_cache.py`
  - [x] Subtask 4.2: 测试缓存设置和获取
  - [x] Subtask 4.3: 测试 TTL 过期机制
  - [x] Subtask 4.4: 测试缓存清除功能
  - [x] Subtask 4.5: 测试并发访问（线程安全）

- [x] Task 5: 性能验证 (AC: 全部)
  - [x] Subtask 5.1: 测试缓存命中响应时间 < 50ms
  - [x] Subtask 5.2: 测试缓存未命中响应时间
  - [x] Subtask 5.3: 创建性能基准测试
  - [x] Subtask 5.4: 验证缓存效果（减少数据库查询）

- [x] Task 6: 添加缓存监控 (AC: 全部)
  - [x] Subtask 6.1: 记录缓存命中率
  - [x] Subtask 6.2: 记录缓存大小
  - [x] Subtask 6.3: 添加日志输出
  - [x] Subtask 6.4: 可选：添加缓存统计端点

## Dev Notes

### 缓存服务实现

**应用级内存缓存:**

```python
# server/src/services/classification_cache.py
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading
import logging

logger = logging.getLogger(__name__)

class ClassificationCache:
    """
    板块分类应用级缓存服务

    使用内存字典存储缓存数据，支持 TTL 过期机制。
    线程安全，适用于 FastAPI 异步环境。
    """

    def __init__(self, ttl_hours: int = 24):
        """
        初始化缓存

        参数:
            ttl_hours: 缓存过期时间（小时），默认 24 小时
        """
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = threading.RLock()  # 可重入锁，支持线程安全

        # 缓存统计
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        参数:
            key: 缓存键

        返回:
            缓存值，如果不存在或已过期则返回 None
        """
        with self._lock:
            # 检查键是否存在
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"缓存未命中: {key}")
                return None

            # 检查是否过期
            cache_time = self._cache_time[key]
            if datetime.now() - cache_time > self._ttl:
                # 缓存已过期，删除并返回 None
                del self._cache[key]
                del self._cache_time[key]
                self._misses += 1
                logger.debug(f"缓存过期: {key}")
                return None

            # 缓存命中
            self._hits += 1
            logger.debug(f"缓存命中: {key}")
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值

        参数:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            self._cache[key] = value
            self._cache_time[key] = datetime.now()
            logger.debug(f"缓存设置: {key}")

    def clear(self, key: Optional[str] = None) -> None:
        """
        清除缓存

        参数:
            key: 缓存键，如果为 None 则清除所有缓存
        """
        with self._lock:
            if key is None:
                # 清除所有缓存
                count = len(self._cache)
                self._cache.clear()
                self._cache_time.clear()
                logger.info(f"清除所有缓存: {count} 条")
            else:
                # 清除指定缓存
                if key in self._cache:
                    del self._cache[key]
                    del self._cache_time[key]
                    logger.debug(f"清除缓存: {key}")

    def clear_pattern(self, pattern: str) -> None:
        """
        按模式清除缓存

        参数:
            pattern: 键模式（支持前缀匹配）
        """
        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                del self._cache_time[key]
            logger.info(f"按模式清除缓存: {pattern}, 删除 {len(keys_to_delete)} 条")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        返回:
            包含缓存统计的字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "ttl_hours": self._ttl.total_seconds() / 3600
            }

# 全局缓存实例
classification_cache = ClassificationCache(ttl_hours=24)
```

### API 端点集成

**集成缓存到现有端点:**

```python
# server/src/api/v1/sector_classifications.py
from src.services.classification_cache import classification_cache

@router.get("/sector-classifications")
async def get_sector_classifications(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取所有板块分类（带缓存）"""
    cache_key = f"classification:all:{skip}:{limit}"

    # 尝试从缓存获取
    cached_data = classification_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # 缓存未命中，查询数据库
    query = select(SectorClassification).offset(skip).limit(limit)
    result = await db.execute(query)
    classifications = result.scalars().all()

    # 转换为响应模型
    response_data = [
        SectorClassificationResponse.model_validate(c) for c in classifications
    ]
    response = SectorClassificationListResponse(data=response_data, total=len(classifications))

    # 存入缓存
    classification_cache.set(cache_key, response)

    return response


@router.get("/sector-classifications/{sector_id}")
async def get_sector_classification(
    sector_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个板块分类（带缓存）"""
    cache_key = f"classification:{sector_id}"

    # 尝试从缓存获取
    cached_data = classification_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # 缓存未命中，查询数据库
    query = select(SectorClassification).where(
        SectorClassification.sector_id == sector_id
    )
    result = await db.execute(query)
    classification = result.scalar_one_or_none()

    if classification is None:
        raise HTTPException(status_code=404, detail=f"板块 {sector_id} 不存在")

    # 转换为响应模型
    response = SectorClassificationResponse.model_validate(classification)

    # 存入缓存
    classification_cache.set(cache_key, response)

    return response
```

### 缓存清除端点

**管理员清除缓存接口:**

```python
# server/src/api/v1/sector_classifications.py
from src.services.classification_cache import classification_cache

@router.post(
    "/sector-classifications/cache/clear",
    status_code=status.HTTP_200_OK,
    summary="清除分类缓存",
    description="清除板块分类缓存，需要管理员权限"
)
async def clear_classification_cache(
    sector_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    清除分类缓存

    参数:
        sector_id: 板块 ID（可选），如果不提供则清除所有缓存

    权限:
        需要管理员权限

    返回:
        清除结果
    """
    # 验证管理员权限（假设 user 对象包含 role 信息）
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    if sector_id is None:
        # 清除所有缓存
        classification_cache.clear()
        return {"message": "已清除所有分类缓存"}
    else:
        # 清除单个板块缓存
        cache_key = f"classification:{sector_id}"
        classification_cache.clear(cache_key)
        return {"message": f"已清除板块 {sector_id} 的缓存"}


@router.get(
    "/sector-classifications/cache/stats",
    response_model=Dict[str, Any],
    summary="获取缓存统计",
    description="获取分类缓存统计信息，需要管理员权限"
)
async def get_cache_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    获取缓存统计信息

    权限:
        需要管理员权限

    返回:
        缓存统计信息
    """
    # 验证管理员权限
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    return classification_cache.get_stats()
```

### 架构模式与约束

**缓存架构:**
- 使用应用级内存缓存（无 Redis 依赖）
- 线程安全（使用 RLock）
- 支持 TTL 过期机制
- 提供缓存统计功能

**关键设计决策:**

| 方面 | 设计决策 | 原因 |
|------|----------|------|
| 缓存类型 | 应用级内存缓存 | 数据每日更新，缓存压力小 |
| TTL | 24 小时 | 匹配数据更新频率 |
| 线程安全 | threading.RLock | FastAPI 异步环境需要 |
| 缓存键 | "classification:all" 或 "classification:{id}" | 清晰的命名空间 |
| 清除接口 | 管理员权限 | 防止滥用 |

### Project Structure Notes

**对齐统一项目结构:**
- 服务放在 `src/services/` 目录
- 测试放在 `tests/` 目录
- 使用 Python 线程锁保证线程安全
- 遵循项目日志规范

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Caching Strategy] - 缓存策略设计
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns] - 命名约定和模式
- [Source: _bmad-output/planning-artifacts/architecture.md#Performance Requirements] - 性能要求

**项目上下文:**
- [Source: _bmad-output/project-context.md#Technology Stack] - Python 3.10+
- [Source: _bmad-output/project-context.md#Testing Rules] - pytest 测试框架

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1] - Epic 1: 数据库、算法与最小验证
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5] - Story 1.5 完整验收标准

### Previous Story Intelligence (Story 1.4)

**从 Story 1.4 学到的经验:**

1. **API 客户端已创建:**
   - `sectorClassificationApi.ts` 已实现
   - 集成了 JWT 认证
   - 可以用于测试缓存效果

2. **前端测试页面:**
   - `/api-test/sector-classification` 可用于验证缓存
   - 显示响应时间（可用于验证缓存命中）

3. **API 端点已实现:**
   - `GET /api/v1/sector-classifications` - 需要集成缓存
   - `GET /api/v1/sector-classifications/{sector_id}` - 需要集成缓存
   - 使用 SQLAlchemy 2.0+ 异步模式

4. **性能基准:**
   - Story 1.3 API 响应时间 < 10ms（无缓存）
   - 缓存命中后应 < 50ms（实际上应该 < 1ms）

5. **测试模式:**
   - 使用 pytest 进行单元测试
   - 性能测试使用 `@pytest.mark.performance`
   - 线程安全测试使用 threading 模块

**Git 智能摘要（最近10条提交）:**
- `16e6063` feat: 完成 Story 1.4 API 测试前端页面并修复代码审查问题 ← Story 1.4
- `8ba6e86` feat: 完成 Story 1.3 分类 API 端点并修复代码审查问题 ← Story 1.3
- `02f143d` docs: 完成 Story 1.2 缠论分类算法服务的代码审查

**代码模式参考:**
- 查看现有缓存实现（如果有的话）
- 参考现有服务层实现模式
- 使用项目日志规范

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **TTL 设置** - 缓存 TTL 必须是 24 小时
2. **线程安全** - 必须使用线程锁（RLock）保证线程安全
3. **缓存键格式** - "classification:all" 或 "classification:{sector_id}"
4. **缓存命中响应** - 必须小于 50ms（实际上应该 < 1ms）
5. **手动清除接口** - 必须提供管理员清除缓存接口
6. **RBAC 权限** - 清除缓存需要管理员权限
7. **缓存统计** - 必须记录命中率、大小等统计信息
8. **日志记录** - 必须记录缓存操作（命中、未命中、清除）
9. **过期检查** - 必须在 get() 时检查 TTL
10. **并发测试** - 必须测试线程安全性

**依赖:**
- Story 1.3 (API 端点必须已实现)
- Story 1.2 (分类服务必须已实现)
- Story 1.1 (数据库表必须已创建)

**后续影响:**
- 缓存将提升 API 性能
- 需要在数据更新后清除缓存
- Epic 2A/2B 可能需要手动刷新缓存

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### Implementation Plan

**实现步骤：**

1. **创建缓存服务模块**
   - 使用 `OrderedDict` 实现 LRU 淘汰机制
   - 使用 `threading.RLock` 保证线程安全
   - 实现 TTL 过期检查
   - 添加缓存统计功能（命中率、大小）

2. **集成缓存到 API 端点**
   - 修改 `get_sector_classifications()` 添加缓存逻辑
   - 修改 `get_sector_classification()` 添加缓存逻辑
   - 缓存键格式：`classification:all:{skip}:{limit}` 或 `classification:{sector_id}`

3. **实现缓存清除接口**
   - `POST /api/v1/sector-classifications/cache/clear` - 清除缓存
   - `GET /api/v1/sector-classifications/cache/stats` - 获取统计
   - 使用 `require_admin` 依赖进行权限验证

4. **创建单元测试**
   - 22 个测试用例覆盖所有功能
   - 包括性能测试（10000 次查询 < 50ms）
   - 包括线程安全测试

**测试结果：**
- ✅ 22/22 测试通过
- ✅ 性能测试通过（10000 次查询 < 50ms）
- ✅ 线程安全测试通过
- ✅ 现有 API 测试通过（13/13）

### File List

**新增文件:**
- `server/src/services/classification_cache.py` - 缓存服务模块
- `server/tests/test_classification_cache.py` - 缓存测试

**修改文件:**
- `server/src/api/v1/sector_classifications.py` - 集成缓存到 API 端点

### Change Log

- 2026-01-21: 实现 Story 1.5 应用级缓存机制
  - 创建 ClassificationCache 服务（LRU + TTL + 线程安全）
  - 集成缓存到分类 API 端点
  - 添加管理员缓存清除和统计接口
  - 22 个单元测试全部通过
  - 性能验证通过（缓存响应 < 50ms）

### Code Review Follow-ups (AI-Review)

**日期:** 2026-01-22
**审查者:** Claude Opus 4.5 (Code Review Agent)

**修复的问题:**
- [x] [AI-Review][HIGH] 修复 None 值无法与缓存未命中区分的问题
  - 使用 Tuple[bool, Any] 返回格式 (hit, value)
  - API 端点更新为使用新的返回格式
  - 测试全部更新为验证 hit 标志
- [x] [AI-Review][MEDIUM] 添加缓存使用限制和最佳实践文档
  - 说明缓存键包含分页参数的原因
  - 说明单进程内存缓存的限制
  - 说明 Pydantic 响应模型缓存的注意事项

**设计决策说明:**
- 缓存键包含分页参数 (classification:all:{skip}:{limit}) 是有意设计
  - 原因: 避免缓存整个数据集造成内存浪费
  - 影响: 不同分页参数会创建独立缓存条目
  - 缓解: 提供 clear_pattern() 方法按前缀清除相关缓存
