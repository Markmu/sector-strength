# 开发计划检查报告（复审）

## 一、检查对象

- 架构文档：`docs/05-股票十大流通股东同步/05-1-架构文档-股票十大流通股东同步.md`
- 实现计划：`docs/05-股票十大流通股东同步/05-2-实现计划-股票十大流通股东同步/`
- 功能数：3（plan-01, plan-02, plan-03）

## 二、总评

- 结论：**通过**（上轮 4 项建议全部处理，本轮新发现 2 项非阻塞建议）
- 阻塞问题数：0
- 建议项数：2

上轮检查的 4 项建议中，3 项已明确修复（前端集成路径改为独立页面 + Sidebar 导航、ADR-3 偏差说明已补充、验证命令 token 获取已完善），1 项非阻塞建议（E2E 自动化）已在 plan-03 风险与边界中注明后续补充方向。

本轮重新逐维度检查后，整体仍为通过状态。发现 2 项新的非阻塞建议：plan-02 中任务处理器注册的回调模式描述与实际代码库存在偏差，可能导致实现者写出不正确的代码；plan-03 中 `listTasks` 参数名与实际 API 接口不一致。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README workflow_type | ✅ 通过 | `create-dev-plan` |
| README org_mode | ✅ 通过 | `feature` |
| README status 合法性 | ✅ 通过 | `review_ready` ∈ {draft, review_ready, in_execution, in_review, accepted, released} |
| execution_order 引用真实 plan 文件 | ✅ 通过 | `[["plan-01"], ["plan-02"], ["plan-03"]]` 对应三个 plan-*.md |
| total_tasks 与 plan 文件数一致 | ✅ 通过 | `total_tasks: 3`，实际 3 个 plan 文件 |
| README 必备章节完整性 | ✅ 通过 | 10 个必备章节全部存在：概览、输入摘要、验收标准追踪矩阵、模块地图、依赖图、阶段摘要、任务总览、未决策项、执行前置、变更记录 |
| 追踪矩阵表头格式 | ✅ 通过 | `AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态` |
| FEAT feat_id 与文件名一致 | ✅ 通过 | plan-01/02/03 文件名与 feat_id 一致 |
| FEAT status 合法性 | ✅ 通过 | 均为 `draft` ∈ {draft, ready-to-dev, in-progress, review, done, deprecated} |
| FEAT 必备章节完整性 | ✅ 通过 | 三个 FEAT 均包含：功能概要、文件清单、实现规格、Task 列表、验收标准、验证命令、交接上下文、风险与边界 |
| Task 步骤状态合法性 | ✅ 通过 | 均为 `todo` |
| depends_on 引用真实功能 | ✅ 通过 | plan-02 → plan-01, plan-03 → plan-02，均存在 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 管理员选择报告期并触发同步 | plan-03 | plan-03 验收标准（API 返回 task_id + 前端按钮状态变更） | ✅ 完整 |
| AC-02 | 数据完整入库 | plan-01, plan-02 | plan-01（Model+迁移）+ plan-02（执行验证） | ✅ 完整 |
| AC-03 | 同步过程中前端实时显示进度 | plan-03 | plan-03 验收标准（进度条 X/Y 实时更新） | ✅ 完整 |
| AC-04 | 部分失败不中断 | plan-02 | plan-02 验收标准（任务完成 + 统计含失败数） | ✅ 完整 |
| AC-05 | 同步完成展示统计 | plan-03 | plan-03 验收标准（统计数字正确展示） | ✅ 完整 |
| AC-06 | 幂等性 | plan-02 | plan-02 验收标准（两次同步记录数一致） | ✅ 完整 |
| AC-07 | 同步失败提示具体原因 | plan-02, plan-03 | plan-02（任务级失败标记）+ plan-03（前端错误展示） | ✅ 完整 |

AC 全映射，无孤立项。README `计划承接` 列指向真实 FEAT，`验证方式` 可追溯到 FEAT 验收标准。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✅ 继承良好 | 0 | 核心闭环（选择报告期→逐股票同步→数据入库）、首版聚焦数据基础设施，完整承接 |
| 2. 范围与非目标 | ✅ 继承良好 | 0 | P0 六项全部有 FEAT 承接；非目标七项均未引入 |
| 3. 成功标准 | ✅ 继承良好 | 0 | 定量指标（≤35min、≤3s、≤500ms）出现在对应 FEAT 验收标准 |
| 4. 验收标准防漂移 | ✅ 继承良好 | 0 | AC-01~AC-07 全部映射；plan-03 E2E 不适用说明已注明后续补充方向 |
| 5. ADR 约束 | ✅ 继承良好 | 0 | 五条 ADR 均在 README 护栏和 FEAT 实现规格中体现；ADR-3 偏差已注明；禁止事项均未引入 |
| 6. 用户流程与状态机 | ✅ 继承良好 | 0 | 主流程 6 步、4 条分支、状态枚举全部覆盖 |
| 7. 模块职责与系统上下文 | ✅ 继承良好 | 0 | 六个架构模块在 README 模块地图中有对应承接；过度设计避免项均遵守 |
| 8. 运行链路 | ✅ 继承良好 | 0 | 三条运行链路（触发/执行/进度）步骤在 FEAT 实现规格中一一落地 |
| 9. 数据模型与契约 | ✅ 继承良好 | 0 | Schema 13 个字段、API 边界 3 个接口、命名规则 7 条全部对齐 |
| 10. 非功能需求 | ✅ 继承良好 | 0 | 性能/安全/可观测性/成本均已落地到 FEAT；降级策略在边界场景覆盖 |
| 11. 实施建议与技术选型 | ✅ 继承良好 | 0 | 三阶段划分与架构一致；技术栈未偏离 |
| 12. 风险与未决策项 | ✅ 继承良好 | 0 | 架构无 open_questions，README 继承；四条风险在 FEAT 风险与边界有缓解 |
| 13. 功能拆分质量 | ✅ 继承良好 | 0 | 每个 FEAT 连贯；Task 数 3-5 不超标；DAG 无循环 |
| 14. 可执行性 | ⚠️ 有建议 | 2 | plan-02 回调模式描述偏差（问题 #1）；plan-03 `listTasks` 参数名偏差（问题 #2） |
| 15. 状态与报告契约 | ✅ 继承良好 | 0 | README/FEAT 状态均合法 |
| 16. 复用声明链路验证 | ✅ 继承良好 | 0 | 三条复用声明在 FEAT 中有正确调用描述，无新增未验证复用 |

## 六、问题清单

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 1 | ⚠️ 建议 | plan-02 实现规格 §2b 任务处理器 | **回调模式描述与实际代码库不一致**：计划写 `service.set_progress_callback(_make_progress_callback(manager, task_id))` 和 `service.set_cancel_check(lambda: _is_task_cancelled(manager, task_id))`，但实际代码库（`task_handlers.py:1117-1125`）的模式是：① `_make_progress_callback` 是 async 函数，需 `callback = await _make_progress_callback(...)` 再 `service.set_progress_callback(callback)`；② 取消检查使用 async 闭包 `async def _check_cancelled(): task = await manager.get_task(task_id); ...` 而非 `lambda` 和不存在的 `_is_task_cancelled`。按计划描述实现会导致传入 coroutine 对象而非实际回调。 | 修正实现规格为实际代码库模式：`callback = await _make_progress_callback(manager, task_id)` + `service.set_progress_callback(callback)` + `async def _check_cancelled(): ...` + `service.set_cancel_check(_check_cancelled)`。 |
| 2 | ⚠️ 建议 | plan-03 实现规格 §3 "上次同步信息" | **`listTasks` 参数名偏差**：计划写 `tasksApi.listTasks({ task_types: 'sync_top10_holders', limit: 1 })`，但实际 API 接口（`api.ts:656-661`）的参数为 `task_types?: string` + `page_size?: number`，无 `limit` 参数。 | 改为 `tasksApi.listTasks({ task_types: 'sync_top10_holders', page_size: 1 })`。 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-03 §4 创建 StockTop10SyncPanel.tsx + 独立页面 | 架构 ADR-3 原文说"不创建独立组件文件""不创建独立页面路由"，但实际 brownfield 验证发现 FundSyncPanel 本身即为独立组件文件且渲染在独立页面 `fund-init/page.tsx` | 符合现有代码库组织模式（FundSyncPanel → fund-init/page.tsx），便于维护和后续迭代。plan-03 已在风险与边界中注明 ADR-3 偏差。 |
| plan-01 可观测性要求 | 架构 §8.5 提到 Python logging，plan-01 在 Tushare 方法中增加了具体 logging 描述 | 将架构层面的可观测性要求细化为可执行指导，合理。 |
| plan-02 性能验收章节 | 架构 §8.1 的性能目标在 plan-02 中增加为独立验收项 | 将非功能指标转化为可验证的 checklist，合理。 |
| plan-03 全流程验收（US 覆盖矩阵） | 新增 US-01~US-05 用户故事覆盖矩阵 | 架构成功标准的用户视角落地，增强验收完整性，合理。 |

## 八、建议补丁计划

### 补丁 1（中优先）：修正 plan-02 任务处理器回调模式

**影响文件**：`plan-02-同步服务与任务注册.md`

将实现规格 §2b 第 4-5 步修正为：

```python
# 4. 设置进度回调（await 异步工厂函数）
callback = await _make_progress_callback(manager, task_id)
service.set_progress_callback(callback)

# 5. 设置取消检查（async 闭包查询 DB 状态）
async def _check_cancelled():
    task = await manager.get_task(task_id)
    return task is not None and task.status == "cancelled"
service.set_cancel_check(_check_cancelled)
```

### 补丁 2（低优先）：修正 plan-03 listTasks 参数名

**影响文件**：`plan-03-管理端同步入口.md`

在实现规格 §3 "上次同步信息"中，将 `limit: 1` 改为 `page_size: 1`：

```typescript
tasksApi.listTasks({ task_types: 'sync_top10_holders', page_size: 1 })
```
