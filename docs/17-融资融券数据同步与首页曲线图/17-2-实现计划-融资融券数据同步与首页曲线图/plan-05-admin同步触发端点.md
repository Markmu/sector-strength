---
feat_id: "plan-05"
title: "admin同步触发端点"
dimension: backend
phase: 2
status: done
depends_on: ["plan-04"]
---

# plan-05: admin同步触发端点

## 功能概要

- **目标**: 新建 `server/src/api/admin/init_margin.py`（逐行对照仿 `init_market_metrics.py`），提供 `POST /api/v1/admin/init/margin` 作为 `sync_market_margin` 任务的唯一合法创建入口：`require_admin` + 五项校验链（起止倒置 / end>today / 跨度>3650 天 / `TradingCalendarRepository.refresh_range` 日历刷新 / 零交易日，任一失败 `ApiResponse(success=False)` 且**不建任务**），通过后延迟导入 `TaskManager.create_exclusive_task(task_type="sync_market_margin", ...)` 互斥建任务；挂载到 `api/admin/__init__.py`。
- **完成后可观察结果**: 管理员 POST 合法起止日（如近 2-3 个真实交易日）获得 `task_id` 并触发 plan-04 交付的范围同步任务；起止倒置 / 未来日 / 超 10 年 / 日历刷新失败 / 零交易日五类请求均返回明确 message 且 `async_tasks` 表无新行；非管理员调用 403；已有同类 pending/running 时再创建返回互斥提示（HTTP 200，与 16 期锚点一致）；通用 `POST /api/v1/admin/tasks` 的封堵消息（plan-04 交付）指向本端点。
- **依赖**: plan-04（`create_exclusive_task` 的 margin 锁 key 映射 + `SYNC_MARKET_MARGIN` 任务类型 + RESERVED 封堵提示）
- **关联验收标准**: [AC-4]（同步端点校验：end>today 拒绝不建任务）
- **涉及架构模块**: admin 管理路由（spec REQ-5，对应 16 期 plan-05 的 init_market_metrics.py 路由部分）
- **前置条件**: plan-01~04 已合并；本地 PostgreSQL；`TUSHARE_TOKEN`（路由级执行验证的日历刷新与真实小范围任务需要）。
- **不在范围**: 范围同步 handler 与 fencing（**已在 plan-04 交付**，与 16 期 plan-05 的拆分不同——17 期无 collector/自动日更，spec 边界禁止范围外功能）；查询 API（plan-06）；前端同步面板（plan-08）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/admin/init_margin.py` | 专用创建路由（唯一合法入口），逐行对照 init_market_metrics.py |
| modify | `server/src/api/admin/__init__.py` | L24 旁 import + L46 旁 include_router 挂载 |
| create | `server/tests/api/admin/test_init_margin.py` | 五项校验 / 互斥 / 鉴权 / 执行验证用例 |

## 实现规格

### 后端部分

#### 1. 专用创建路由（spec REQ-5）

`server/src/api/admin/init_margin.py`，逐段仿 `init_market_metrics.py`（16 期 plan-05 成品，L1-154）：

- `router = APIRouter(prefix="/init", tags=["Admin - Margin"])`；挂载链：admin 主路由（无统一前缀）→ `router.py` `/v1/admin` → main.py `/api` = **最终路径 `/api/v1/admin/init/margin`**
- Pydantic payload：`MarginRangePayload`，`start_date: date`、`end_date: date`（body snake_case，user_input）
- 端点签名：

```python
@router.post("/margin", response_model=ApiResponse[dict])
async def init_margin(
    payload: MarginRangePayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
```

- **五项校验链**（任一失败 `ApiResponse(success=False, data=None, message=...)`，**不建任务**；行号为 init_market_metrics.py 对照锚点）：
  1. `payload.start_date > payload.end_date` → "开始日期不能晚于结束日期"（对照 :80）
  2. `payload.end_date > date.today()` → "结束日期不能晚于今天"（对照 :86；AC-4 主断言）
  3. `(end_date - start_date).days > _MAX_BACKSPAN_DAYS` → "日期范围不能超过 10 年（3650 天）"（对照 :94；`_MAX_BACKSPAN_DAYS = 3650` 模块常量照搬）
  4. `TradingCalendarRepository(session).refresh_range(start, end)`（对照 :104）：Provider 失败/响应不完整 → `session.rollback()` + WARNING 日志 + "交易日历刷新失败，未创建任务：{e}"（不降级旧批次，16 期同款）
  5. `cal_repo.get_trading_days(start, end)` 为空 → "所选范围内没有交易日，未创建任务"（对照 :115-123）
- 校验全过后：延迟导入 `from src.services.task_manager import TaskManager`（避免循环依赖，对照 :126）→ `manager.create_exclusive_task(task_type="sync_market_margin", params={"start_date": payload.start_date.isoformat(), "end_date": payload.end_date.isoformat()}, created_by=_admin.id)`：
  - 返回 None（互斥命中，plan-04 的 margin advisory lock）→ `ApiResponse(success=False, message="已有融资融券同步任务正在运行，请等待当前任务完成")`（HTTP 200，与 16 期锚点一致）
  - 成功 → `ApiResponse(success=True, data={"task_id": task.task_id}, message=f"融资融券同步任务已创建（{start} ~ {end}，交易日 {len(trading_days)} 个）")`
- **安全（16 期 §8.3 惯例继承）**: `require_admin` 依赖（非管理员 403）；日期用 Pydantic `date` 类型天然防注入；不透传 `max_retries`（`create_exclusive_task` 固定 `max_retries=0`）。
- **可观测性**: 校验拒绝与创建成功均记 INFO/WARNING 日志（含范围与交易日数）；任务进度与 result 的可观测性由 plan-04 handler 承担。

#### 2. 路由挂载

`server/src/api/admin/__init__.py` 两处对称扩展（不动 16 期行）：

- import 区 L24 旁：`from .init_margin import router as init_margin_router  # 第 17 期 plan-05`
- 注册区 L46 旁：`router.include_router(init_margin_router)  # /api/v1/admin/init/margin（第 17 期 plan-05）`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | init_margin.py 路由骨架 + MarginRangePayload + require_admin | backend | done | /api/v1/admin/init/margin |
| 2 | 五项校验链（倒置/未来/跨度/日历刷新/零交易日） | backend | done | 任一失败不建任务（AC-4） |
| 3 | create_exclusive_task 接线 + 互斥/成功响应 | backend | done | task_type="sync_market_margin" |
| 4 | admin/__init__.py 挂载 | backend | done | import + include_router |
| 5 | 编写 test_init_margin.py | backend | done | 五项校验/互斥/403/执行验证 |

## 验收标准

### 后端验收

- [x] AC-4 起止倒置 / end>today / 跨度>10 年 / 日历刷新失败 / 零交易日五类请求均 `success=False` 且返回明确 message，并断言 **async_tasks 表无新行**（五项逐一用例）
- [x] 非管理员调用 → 403（`require_admin`）；合法请求返回 `data.task_id` 且任务 `task_type=sync_market_margin`、params 含 ISO 起止日、`created_by` 为管理员 id
- [x] AC-3（端点侧）已有同类型 pending/running 时再创建 → `success=False` + 互斥提示 message，不产生重复任务
- [x] **执行验证（路由级，不豁免）**：真实 PG + `TUSHARE_TOKEN` 下经 httpx `ASGITransport` 直连 app（admin 依赖 override，见 §6 脚本）POST 近 2-3 个真实交易日 → 返回 task_id → 启动执行器等待终态 → 任务 completed 且 `market_margin_daily` 数据断言复用 plan-04 执行验证第 3 条
- [x] 端点行为与 plan-04 RESERVED 封堵联动：通用 `POST /api/v1/admin/tasks` 创建 `sync_market_margin` 的拒绝消息含 `POST /api/v1/admin/init/margin`（复跑 plan-04 AC-8 用例确认指向正确）
- [x] **16 期回归（共享文件挂载扩展）**：`pytest tests/api/admin/test_init_market_metrics.py tests/api -q --no-cov` 全绿——init/market-metrics 及其余 admin 路由行为不变
- [x] E2E 不适用：后端路由功能无浏览器界面；以路由级执行验证（上第 4 条）为质量门，浏览器侧触发交互由 plan-08 E2E 覆盖

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 本功能单测（tests/api/admin/conftest.py 的 autouse admin override 自动生效）
pytest tests/api/admin/test_init_margin.py -v --no-cov

# 2. 16 期 admin 路由回归（挂载扩展硬门槛）
pytest tests/api/admin/ tests/api -q --no-cov

# 3. 路由级执行验证（需 TUSHARE_TOKEN + 本地 PG；先 alembic upgrade head）
python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from src.api.deps import get_current_user
from src.models.user import User

async def main():
    app.dependency_overrides[get_current_user] = lambda: User(
        email='exec@example.com', password_hash='x', username='exec_admin', role='admin')
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as c:
        r = await c.post('/api/v1/admin/init/margin',
                         json={'start_date': '2026-08-11', 'end_date': '2026-08-13'})
        print(r.status_code, r.json())
asyncio.run(main())
"
# 拿到 task_id 后启动执行器（现有服务入口）等待终态，查库断言复用 plan-04 §6 第 3 步脚本。

# 4. 全量回归
pytest tests/ -q --no-cov
```

## 交接上下文

- **spec 章节**: REQ-5（同步端点）、边界（必须：require_admin + 五项校验；禁止：无）、任务清单 T5
- **相关代码**: `server/src/api/admin/init_market_metrics.py`（L1-154 全量对照母本：payload L48-58、校验链 L77-123、建任务 L125-136、互斥 L138-144）、`server/src/api/admin/__init__.py`（import L24、挂载 L46）、`server/src/services/trading_calendar_repository.py`（refresh_range / get_trading_days，16 期交付直接复用）、`server/src/services/task_manager.py`（`create_exclusive_task` margin 分支，plan-04 交付）
- **契约 / 数据对象**: 请求 `{start_date, end_date}`（YYYY-MM-DD，snake_case body）；成功响应 `ApiResponse[dict]` `data={"task_id": ...}`（snake_case，与 `initMarketMetrics` 同款，plan-08 前端 `adminApi.initMargin` 消费）
- **下游消费方**: plan-08（`adminApi.initMargin` POST 本端点；互斥 message 直接展示）
- **路径说明**: `server/tests/api/admin/` 已存在（16 期建立），其 conftest.py 的 autouse admin override 与中间件解包逻辑对本功能测试自动生效，无需新建 conftest
- **实现级补充项**: 无（16 期 init_market_metrics.py 范式逐行对照即可，两融无生命周期 preflight 等额外环节）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 3 依赖 plan-04 的 `create_exclusive_task` margin 锁映射
- **验证失败排查方向**: 403 意外出现 → 查 conftest autouse override 是否生效；互斥永不触发 → 查 plan-04 `_EXCLUSIVE_TASK_LOCK_KEYS` 是否含 sync_market_margin；日历刷新失败 → 确认 TUSHARE_TOKEN 与 trade_cal 权限
- **允许修改的额外文件**: 无
- **暂停条件**: 若路由级执行验证因 Tushare margin 接口积分不足（2000 分）持续失败，暂停并请用户提供可用账号（与 plan-04 执行验证同款暂停条件）
- **风险备注**: 本功能纯新增文件 + 两行挂载，风险面小；主要风险是与 plan-04 的契约错位（task_type 字符串、锁 key），Task 3 完成后立即复跑 plan-04 的互斥用例确认

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 起止倒置 | success=False "开始日期不能晚于结束日期"，不建任务 | done |
| end_date 晚于今天 | success=False "结束日期不能晚于今天"，不建任务（AC-4） | done |
| 跨度 > 3650 天 | success=False "日期范围不能超过 10 年"，不建任务 | done |
| 日历刷新 Provider 失败 | rollback + 失败 message，不降级旧批次，不建任务 | done |
| 范围全为非交易日 | success=False "所选范围内没有交易日"，不建任务 | done |
| 同类任务 pending/running 中再创建 | 互斥命中，success=False 提示已有任务（HTTP 200） | done |
| 非管理员调用 | 403（require_admin） | done |
