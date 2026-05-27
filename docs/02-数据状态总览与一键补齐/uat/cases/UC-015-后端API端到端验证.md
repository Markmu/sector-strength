# 用例详情：UC-015 - 后端 API 端到端验证

**Case ID:** UC-015
**模块:** 后端 API
**用例类型:** 正向
**优先级:** P0
**创建日期:** 2026-05-27
**关联验收标准:** AC-01 ~ AC-05

## 用例描述

通过 curl 验证后端 API 端点，包括状态查询、补齐触发、冲突处理和参数校验。

## 前置条件

1. PostgreSQL 运行中
2. 后端服务运行在 localhost:8000
3. 有有效的管理员 JWT token

## 测试数据

| 数据项 | 数据值 | 说明 |
|--------|--------|------|
| API base | http://localhost:8000/api/v1/admin | 后端 API 地址 |
| Auth header | Authorization: Bearer $TOKEN | 管理员 JWT |

## 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | `curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/admin/data/status` | 返回 200，body 包含 `{ success: true, data: { items: [...] } }`，3 个 item |
| 2 | 检查返回的 items 结构 | 每个 item 包含 type, label, latest_date, status, missing_range, active_task |
| 3 | `curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/admin/data/backfill/history` | 若有缺失返回 200 + task_id；若无缺失返回 400 |
| 4 | 重复步骤 3 | 返回 409 `{ detail: "该类数据已有补齐任务正在执行" }` |
| 5 | `curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/admin/data/backfill/invalid` | 返回 422（参数校验失败） |
| 6 | 无 token 直接请求 | 返回 401（未授权） |
| 7 | 查询 status API 响应时间 | < 2s |

## 预期结果

- GET /status 返回三类数据完整状态
- POST /backfill/{type} 正确创建任务或返回 400/409
- type 参数校验：只接受 history/ma/strength
- 未授权访问被拒绝
- 响应时间 < 2s

## 实际结果

**执行日期:** 2026-05-27
**执行状态:** Passed

- Step 1: GET /status → 200 (0.42s)，返回三类数据完整状态，history=normal, ma/strength=missing
- Step 2: POST /backfill/ma → 200，创建任务 task_aa5d481b360f
- Step 3: POST /backfill/ma 重复 → 409 冲突正确返回
- Step 4: POST /backfill/invalid → 422 参数校验正确
- Step 5: 无 token → 401 未授权正确
- Step 7: 响应时间 0.42s < 2s ✓

修复项：data_status 路由未注册到 admin __init__.py（已修复）；TaskType 枚举缺少 BACKFILL_HISTORY/MA/STRENGTH（已添加）

## 证据链接

（待执行后填写）

## 备注

本用例对应架构文档 §7.3 API 边界和 plan-02 的后端验收标准。
