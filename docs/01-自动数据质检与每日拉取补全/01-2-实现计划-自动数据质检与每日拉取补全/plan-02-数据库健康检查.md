---
feat_id: "plan-02"
title: "数据库健康检查"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-02: 数据库健康检查

## 1. 功能概要

- **目标**: 修复 `/health/db` 端点的 TODO 空实现，使其执行真实的数据库连接验证；同时确认 DataUpdateLog 模型支持 `skipped` 状态值。
- **完成后可观察结果**: 调用 `GET /health/db` 时，数据库正常运行返回 `{"status": "healthy", "database": "connected"}`；停止数据库服务后调用同一接口返回 HTTP 503 和 `{"status": "unhealthy", "database": "disconnected", "error": "..."}`。运维监控系统能据此准确报警。
- **依赖**: 无
- **关联验收标准**: [AC-05]
- **涉及架构模块**: HealthCheck, DataUpdateLog
- **前置条件**: PostgreSQL 运行中
- **不在范围**: 其他健康检查端点（如 `/health`）；数据库连接池监控指标

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/main.py` | 修复 database_health_check() 函数，执行真实 SELECT 1 |
| modify | `server/src/models/update_log.py` | 更新类注释，确认 status 支持 skipped |

## 3. 实现规格

### 后端部分

#### 1. 修复 database_health_check()

修改 `server/main.py` 的 `database_health_check()` 函数（L136-154）：

当前问题：try 块内无实际查询，直接返回 healthy，即使数据库宕机也返回"健康"。

修改内容：
1. 在文件顶部添加 import：
   ```python
   from sqlalchemy import text
   from src.db.database import AsyncSessionLocal
   ```
2. 在 `database_health_check()` 的 try 块内添加：
   ```python
   async with AsyncSessionLocal() as session:
       await session.execute(text("SELECT 1"))
   ```
3. 确保 except 块能捕获连接异常并返回 503 JSONResponse

修改后的函数结构：
```python
@app.get("/health/db")
async def database_health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
```

#### 2. 确认 DataUpdateLog 支持 skipped 状态

修改 `server/src/models/update_log.py` 的类注释：
- `status` 字段为 `String(20)` 类型，无枚举约束
- 更新注释：`# 'running', 'completed', 'failed', 'skipped'`
- 实际运行确认数据库无枚举约束（collector.py 已写入 `skipped`，无需数据库迁移）

**可观测性（架构 §8.4）**: 健康检查失败时记录 error 级别日志，输出结构化信息 `{ "status": "unhealthy", "error": "..." }`。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 修复 database_health_check() 执行 SELECT 1 | backend | done | 在 try 块内添加实际查询，导入 text 和 AsyncSessionLocal |
| 2 | 确认 DataUpdateLog status 支持 skipped | backend | done | 更新模型注释，确认无枚举约束 |

## 5. 验收标准

### 功能验收

- [x] AC-05 数据库正常运行时，`GET /health/db` 返回 `{"status": "healthy", "database": "connected"}` 和 HTTP 200
- [x] AC-05 数据库不可用时，`GET /health/db` 返回 HTTP 503 和 `{"status": "unhealthy", "database": "disconnected", "error": "..."}`
- [x] DataUpdateLog 的 status 字段可写入 `skipped` 值

## 6. 验证命令

```bash
cd server
# 单元测试
pytest tests/ -v -k "health or health_check"
# 手动验证（需启动服务 + 数据库）
uvicorn server.main:app --port 8000 &
curl http://localhost:8000/health/db
# 期望: {"status":"healthy","database":"connected"}
# 停止数据库后再次验证
curl http://localhost:8000/health/db
# 期望: HTTP 503 + {"status":"unhealthy","database":"disconnected","error":"..."}
```

## 7. 交接上下文

- **架构章节**: §5 ADR-4、§6.3 健康检查链路
- **相关代码**: `server/main.py` (L136-154)、`server/src/db/database.py`（AsyncSessionLocal）
- **契约 / 数据对象**: HealthCheck 响应 `{"status": "healthy/unhealthy", "database": "connected/disconnected", "error?": "..."}` 
- **下游消费方**: 无直接下游，运维监控系统消费此端点

## 8. 风险与边界

- **执行顺序**: 按任务列表顺序执行
- **验证失败排查方向**: 检查 AsyncSessionLocal 是否正确初始化、PostgreSQL 连接字符串是否正确、数据库是否运行
- **允许修改的额外文件**: 无
- **暂停条件**: 无
- **E2E 不适用说明**: 纯运维端点，无用户可观察 UI；通过 curl/pytest 验证
- **风险备注**: SELECT 1 只验证连接可用性，不验证数据完整性

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 数据库连接池耗尽 | session.execute 超时抛异常，返回 503 | done |
| 数据库重启中 | 连接失败返回 503 | done |
| AsyncSessionLocal 未初始化 | ImportError 或 AttributeError，返回 503 | done |
