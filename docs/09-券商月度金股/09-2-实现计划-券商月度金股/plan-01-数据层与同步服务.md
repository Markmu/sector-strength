---
feat_id: "plan-01"
title: "数据层与同步服务（模型 + Tushare 扩展 + 同步 service + task handler + admin API）"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 数据层与同步服务

## 功能概要

- **目标**: 交付券商金股的"按月同步"数据底座：新建 `broker_recommend` 表与 SQLAlchemy 模型、扩展 Tushare 客户端（接口原生支持 month 入参，直接拉取该月数据）、新建同步服务（month 入参 + 按 ts_code,broker 去重 + 先删后写逐批 commit，复用 Top10 同步范式）、注册 `SYNC_BROKER_RECOMMEND` task handler、新增 admin 同步触发 API。完成后系统具备把任意月份券商金股数据写入数据库的能力。
- **完成后可观察结果**: 管理员在数据管理页（或 curl admin 端点）选择月份（YYYYMM）触发"券商月度金股同步"后，任务被创建并执行，TaskExecutor 拾取 `sync_broker_recommend_task`，直接用 `pro.broker_recommend(month=YYYYMM)` 从 Tushare 拉取该月全部券商推荐记录写入 `broker_recommend` 表，任务列表显示进度与日志，可取消；同步成功后该月数据可被 plan-02 的查询服务读取；重复触发同一月份为覆盖式刷新（先删后写，不堆积）；已有同类型任务运行中时拒绝并发。
- **依赖**: 无
- **关联验收标准**: [AC-08]
- **涉及架构模块**: BrokerRecommend 模型、Tushare 客户端扩展、BrokerRecommendDataInitService、SYNC_BROKER_RECOMMEND task handler、admin 同步 API（架构 §4.2 / §6.3 / §9 Phase A）
- **前置条件**: PostgreSQL 与 Alembic 环境就绪；Tushare token 配置就绪（代理服务相当于 15000 积分，broker_recommend 需 6000 积分，满足）；`server/src/services/task_handlers.py` / `data_init_top10_holder.py` / `api/admin/init_top10_holders.py` 现有范式可参照
- **不在范围**: 用户侧查询 API（plan-02）、前端页面（plan-03）、前端同步面板（plan-03）、缓存层（ADR-6 明确不做）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/broker_recommend.py` | 新建 `BrokerRecommend(Base)` 模型，字段 id/month/trade_date/ts_code/symbol/broker/name/reason/created_at/updated_at，索引 (symbol,month)+(broker,month)+(month) |
| modify | `server/src/models/__init__.py` | 导出 `BrokerRecommend`（追加 import + `__all__`），范式参照 line 18（Top10FloatHolder） |
| create | `server/alembic/versions/{timestamp}_create_broker_recommend.py` | 新建 broker_recommend 表迁移（alembic revision 自动生成） |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 新增 `get_broker_recommend(month)`（范式参照 `get_top10_float_holders` line 698） |
| create | `server/src/services/data_init_broker_recommend.py` | 新建 `BrokerRecommendDataInitService(session)`，sync_broker_recommend(month) + _parse_record |
| modify | `server/src/services/task_handlers.py` | `TaskType` 枚举新增 `SYNC_BROKER_RECOMMEND`（line 65 后）；新增 `sync_broker_recommend_task` handler（范式照搬 line 1172 的 `sync_top10_holders_task`） |
| create | `server/src/api/admin/init_broker_recommend.py` | 新建 admin 同步路由（范式照搬 `init_top10_holders.py`） |
| modify | `server/src/api/admin/__init__.py` | 注册 `init_broker_recommend_router`（line 37 范式） |

## 实现规格

### 后端部分

#### 1. 数据模型 `BrokerRecommend`（`server/src/models/broker_recommend.py`）

范式参照 `server/src/models/top10_float_holder.py`（`class Top10FloatHolder(Base)`，`__table_args__` 用 `Index(...)`）。

- `from .base import Base`（与 Top10 同导出位置）
- 字段：
  - `id = Column(Integer, primary_key=True, autoincrement=True)`
  - `month = Column(Date, nullable=False, comment="月份标识（该月第一天，MAX 比较键）")` — **关键**：存该月第一天（如 202606 → 2026-06-01），与 trade_date 区分（ADR-1）
  - `trade_date = Column(Date, nullable=False, comment="推荐日期（接口返回，同月可能有多个）")`
  - `ts_code = Column(String(20), nullable=False, comment="Tushare代码")`
  - `symbol = Column(String(10), nullable=False, comment="股票代码(纯数字)")`
  - `broker = Column(String(100), nullable=False, comment="券商名称")`
  - `name = Column(String(100), comment="股票名称(取自接口，仅快照用；查询时以 stocks JOIN 为准)")`
  - `reason = Column(Text, comment="推荐理由")`
  - `created_at = Column(DateTime(timezone=True), server_default=func.now())`
  - `updated_at = Column(DateTime(timezone=True), onupdate=func.now())`
- `__table_args__`：
  - `Index('ix_broker_symbol_month', 'symbol', 'month')`
  - `Index('ix_broker_broker_month', 'broker', 'month')`
  - `Index('ix_broker_month', 'month')`
- 导出：`server/src/models/__init__.py` 追加 `from .broker_recommend import BrokerRecommend` + `__all__` 加 `"BrokerRecommend"`（范式参照 line 18/42）。

#### 2. Alembic 迁移

在 `server/` 下用 `alembic revision --autogenerate -m "create broker_recommend table"` 生成，确认升级含 `op.create_table('broker_recommend', ...)` + 3 个 `op.create_index(...)`，降级对应 drop。**关键**：autogenerate 会读 `models/__init__.py` 导出的新模型，故必须先完成 step 1 的导出。

#### 3. Tushare 客户端扩展（`server/src/services/data_acquisition/tushare_client.py`）

范式参照 `get_top10_float_holders`（line 698-728）：`pro = self._get_pro_api()` + 内部 `_fetch` 闭包 + `df = self._execute_with_retry(_fetch)`；空数据返回 `[]`；import pandas。

- `async def get_broker_recommend(self, month: str) -> List[dict]`：
  - 接口原生支持 month 入参（Tushare doc 267 核实）：`_fetch = lambda: pro.broker_recommend(month=month)`（month 为 YYYYMM 如 "202606"）
  - 返回字段已确认（doc 267）：`ts_code / trade_date / name / broker / reason`
  - df → `df.to_dict('records')` 返回 raw dict 列表
  - 空数据 logger.warning + 返回 `[]`
  - **不再需要** `get_last_trade_date_of_month`（架构 ADR-2 简化：接口 month 入参直接返回该月数据，无需 trade_cal 映射）

#### 4. 同步服务（`server/src/services/data_init_broker_recommend.py`）

范式**完全照搬** `server/src/services/data_init_top10_holder.py` 的 `Top10HolderDataInitService`：

- 类签名 `class BrokerRecommendDataInitService`：`def __init__(self, session: AsyncSession)`，内部 `self.session = session`、`self.tushare = DataSourceFactory.create()`（import：`from src.services.data_acquisition import DataSourceFactory`，`from src.services.data_acquisition.tushare_client import TushareDataSource`，范式参照 data_init_top10_holder.py line 17-19）、`self._progress_callback = None`、`self._cancel_check = None`。
- `set_progress_callback(callback)` / `set_cancel_check(check)` / `async _check_cancelled()` / `async _update_progress(current, total, message)`：**逐字复制** Top10 的实现（含 `asyncio.CancelledError` 取消语义）。
- `async def sync_broker_recommend(self, month: str) -> dict`（参数 month = YYYYMM）：
  1. 月初 date：`month_date = datetime.strptime(f"{month}01", "%Y%m%d").date()`
  2. 拉取该月全部记录：`records = await self.tushare.get_broker_recommend(month)`（ADR-2，接口原生支持 month 入参）
  3. 空数据：logger.warning，返回 `{"added": 0, "failed": 0}`
  4. 按 (ts_code, broker) 去重（ADR-2）：同券商对同股当月多次推荐时，保留 trade_date 最新的一条（避免重复堆积）。算法：用 dict 以 `(ts_code, broker)` 为 key，遍历 records 保留 trade_date 最大者。
  5. 先删后写（ADR-1 幂等）：`DELETE FROM broker_recommend WHERE month = :month_date`（`delete(BrokerRecommend).where(BrokerRecommend.month == month_date)`）
  6. 逐条 `_parse_record` → `BrokerRecommend` 实例列表；`batch_size`（如 500）分批 `add_all` + `flush` + `commit`，每批后 `_update_progress` + `_check_cancelled`
  7. 返回 `{"added": added, "failed": failed}`
- `_parse_record(self, record: dict, month_date: date) -> Optional[BrokerRecommend]`：字段映射集中此处（字段名已与 doc 267 核实一致：`ts_code/trade_date/name/broker/reason`）；从 record 取 `ts_code`/`trade_date`/`broker`/`name`/`reason`；`symbol` = ts_code 的数字部分（`ts_code.split('.')[0]`，范式参照 data_init_top10_holder.py line 177-181）；`trade_date` 解析为 date（`datetime.strptime(trade_date_str, "%Y%m%d").date()`）；缺失必要字段（broker/ts_code）→ 返回 None 跳过。

#### 5. Task 注册（`server/src/services/task_handlers.py`）

- `TaskType` 枚举新增（line 65 `SYNC_TOP10_HOLDERS` 后）：
  `SYNC_BROKER_RECOMMEND = "sync_broker_recommend"`
- 新增 handler（范式照搬 line 1172-1236 的 `sync_top10_holders_task`）：
  ```python
  @TaskRegistry.register(TaskType.SYNC_BROKER_RECOMMEND)
  async def sync_broker_recommend_task(task_id, params, manager):
      from src.services.data_init_broker_recommend import BrokerRecommendDataInitService
      month = params.get("month")
      if not month:
          await manager.log_message(task_id, "ERROR", "Missing required parameter: month")
          raise ValueError("Missing required parameter: month")
      service = BrokerRecommendDataInitService(manager.db)
      callback = await _make_progress_callback(manager, task_id)
      service.set_progress_callback(callback)
      # cancel_check 直查 AsyncTask.status 标量（与 sync_top10_holders_task 一致，line 1212-1218）
      async def _check_cancelled():
          result = await manager.db.execute(select(AsyncTask.status).where(AsyncTask.task_id == task_id))
          return result.scalar_one_or_none() == "cancelled"
      service.set_cancel_check(_check_cancelled)
      await manager.log_message(task_id, "INFO", f"Starting broker recommend sync (month={month})")
      try:
          result = await service.sync_broker_recommend(month)
          await manager.log_message(task_id, "INFO", f"Broker recommend sync completed (month={month}): added={result.get('added')}, failed={result.get('failed')}")
      except Exception as e:
          original_error = getattr(e, "original_error", None)
          detail = f"{e}" + (f" | 原始错误: {original_error}" if original_error else "")
          await manager.log_message(task_id, "ERROR", f"Broker recommend sync failed (month={month}): {detail}")
          raise
  ```
  - import 已在文件头（`from sqlalchemy import select` line 12，`from src.models.async_task import AsyncTask` line 15）。
- **可观测性（架构 §8.5）**：进度通过 `_make_progress_callback`（`manager.log_message` INFO）记录；失败/异常 ERROR 级记录原因；同步任务进度更新到 AsyncTask，数据管理页可查看进度与失败原因。使用项目现有 logging（`logger = logging.getLogger(__name__)`）输出结构化日志。

#### 6. Admin 同步 API（`server/src/api/admin/init_broker_recommend.py`）

范式照搬 `server/src/api/admin/init_top10_holders.py`（已读确认）：

- `router = APIRouter(prefix="/init", tags=["Admin - Broker Recommend Init"])`
- `class InitBrokerRecommendRequest(BaseModel)`：`month: str = Field(..., description="月份 YYYYMM", pattern=r"^\d{6}$")`（pattern 改 6 位）
- `@router.post("/broker-recommend", response_model=ApiResponse[dict])`：
  - 并发保护：`select(AsyncTask).where(and_(AsyncTask.task_type == TaskType.SYNC_BROKER_RECOMMEND.value, AsyncTask.status.in_(["pending", "running"])))`；有则 `ApiResponse(success=False, data=None, message="已有券商金股同步任务正在运行，请等待当前任务完成")`
  - `from src.services.task_manager import TaskManager`（延迟导入）；`manager = TaskManager(session)`；`task = await manager.create_task(task_type=TaskType.SYNC_BROKER_RECOMMEND.value, params={"month": request.month}, max_retries=3, timeout_seconds=3600, created_by=_admin.id)`；`await session.commit()`
  - 返回 `ApiResponse(success=True, data={"task_id": task.task_id}, message=f"券商金股同步任务已创建（月份: {request.month}）")`
- import：`from src.api.deps import get_session, require_admin`、`from src.api.schemas.response import ApiResponse`、`from src.models.async_task import AsyncTask`、`from src.models.user import User`、`from src.services.task_handlers import TaskType`、`from sqlalchemy import select, and_`（全部与 init_top10_holders.py 一致）。
- 注册：`server/src/api/admin/__init__.py` 追加 `from .init_broker_recommend import router as init_broker_recommend_router` + `router.include_router(init_broker_recommend_router)  # /api/v1/admin/init/broker-recommend`（范式参照 line 16/31）。

### 前端部分

无（本功能为纯后端；前端同步面板在 plan-03）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新建 `BrokerRecommend` 模型 + `models/__init__.py` 导出 | backend | done | 字段/索引见实现规格 #1 |
| 2 | 生成 alembic 迁移并核对 up/down | backend | done | `alembic revision --autogenerate -m "create broker_recommend table"`；手动剔除 autogenerate 噪音（sector_classification/fund_portfolio/funds） |
| 3 | Tushare 客户端新增 get_broker_recommend(month) | backend | done | 范式参照 get_top10_float_holders；接口原生支持 month 入参（doc 267 已核实字段 ts_code/trade_date/name/broker/reason） |
| 4 | 新建 BrokerRecommendDataInitService（sync_broker_recommend + _parse_record + ts_code,broker 去重） | backend | done | 完全复用 Top10 同步范式（先删后写逐批 commit + 回调）；按 ts_code,broker 去重保留最新 trade_date |
| 5 | TaskType 新增 SYNC_BROKER_RECOMMEND + sync_broker_recommend_task handler | backend | done | 范式照搬 sync_top10_holders_task（含 cancel_check 直查 status 标量） |
| 6 | 新建 admin init_broker_recommend 路由 + 注册 | backend | done | pattern `^\d{6}$`，并发保护，create_task(params={"month":...}) |

## 验收标准

### 数据同步验收（AC-08）

- [ ] AC-08a `BrokerRecommend` 模型字段与索引齐全（month 为该月第一天 Date、trade_date 为接口返回的推荐日期 Date），`alembic upgrade head` 成功创建表
- [ ] AC-08b admin API `POST /api/v1/admin/init/broker-recommend`（body `{"month":"202605"}`）创建任务返回 `task_id`；已有同类 running 任务时返回并发保护提示
- [ ] AC-08c `TaskType.SYNC_BROKER_RECOMMEND` 在枚举中存在且 handler 被 `TaskRegistry.register` 注册
- [ ] AC-08d 同步服务直接用 `pro.broker_recommend(month=YYYYMM)` 拉取该月数据（接口原生支持，无需 trade_cal 映射）
- [ ] AC-08e 先删后写幂等：重复调用同月份不堆积（DELETE WHERE month 后重写）
- [ ] AC-08f 同券商对同股当月多次推荐时按 (ts_code, broker) 去重保留最新 trade_date，不堆积

### 执行验证（task handler 强制项，不可豁免）

- [ ] AC-08-execute-1 触发任务：`curl -X POST http://localhost:8000/api/v1/admin/init/broker-recommend -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" -d '{"month":"202605"}'` 返回 `{"success":true,"data":{"task_id":"..."}}`
- [ ] AC-08-execute-2 等待任务完成：轮询 `GET /api/admin/tasks/<task_id>`（或查 AsyncTask），最终 `status == "completed"`
- [ ] AC-08-execute-3 查表确认数据写入：`SELECT month, trade_date, symbol, broker, name, reason FROM broker_recommend WHERE month = '2026-05-01' LIMIT 5;` 返回 ≥1 行，字段值正确（month=2026-05-01、broker 非空、symbol 为纯数字、trade_date 为该月某交易日）
- [ ] AC-08-execute-4 重复触发同月为覆盖式刷新：再次 POST 同月份，任务完成后 `SELECT count(*) FROM broker_recommend WHERE month='2026-05-01'` 与首次一致（先删后写，不堆积）

### 可观测性（架构 §8.5）

- [ ] 任务进度通过 `manager.log_message` 记录 INFO 日志，数据管理页可查看进度百分比
- [ ] 同步失败（网络超时/接口异常）任务 status=failed 且日志记录原因，不影响历史数据

### 构建与类型

- [ ] `cd server && alembic upgrade head` 通过（表创建成功）
- [ ] `cd server && python -c "from src.models import BrokerRecommend; from src.services.task_handlers import TaskType; print(TaskType.SYNC_BROKER_RECOMMEND)"` 无 ImportError
- [ ] `cd server && pytest -q`（既有测试不回归）

## 验证命令

```bash
# 1. 迁移与 import 校验
cd server
alembic upgrade head
python -c "from src.models import BrokerRecommend; from src.services.task_handlers import TaskType; from src.services.data_init_broker_recommend import BrokerRecommendDataInitService; from src.api.admin.init_broker_recommend import router; print(TaskType.SYNC_BROKER_RECOMMEND)"

# 2. 启动后端
uvicorn src.main:app --reload

# 3. admin 触发同步（需 admin token，AC-08-execute）
curl -X POST http://localhost:8000/api/v1/admin/init/broker-recommend \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"month":"202605"}'

# 4. 轮询任务状态
curl http://localhost:8000/api/admin/tasks/<task_id> -H "Authorization: Bearer <admin_token>"

# 5. 查表确认数据（AC-08-execute-3）
psql -c "SELECT month, trade_date, symbol, broker, reason FROM broker_recommend WHERE month = '2026-05-01' LIMIT 5;"

# 6. 既有测试不回归
pytest -q
```

端到端：本功能为纯后端数据同步，用户可观察性通过"执行验证"（触发任务→completed→查表）覆盖，无前端 E2E。task handler 是数据写入的唯一执行者，执行验证不可豁免。

## 交接上下文

- **架构章节**: §4.1（变更点）、§4.2（BrokerRecommendDataInitService + 复用声明验证）、§6.3（数据同步任务链路）、§7.1/§7.5（broker_recommend 表）、§9 Phase A、§8.5（可观测性）
- **相关代码**:
  - 范式源：`server/src/models/top10_float_holder.py`、`server/src/services/data_init_top10_holder.py`、`server/src/services/task_handlers.py`（sync_top10_holders_task line 1172）、`server/src/api/admin/init_top10_holders.py`、`server/src/services/data_acquisition/tushare_client.py`（get_top10_float_holders line 698）
  - 本功能产出：`server/src/models/broker_recommend.py`、`server/src/services/data_init_broker_recommend.py`、`server/src/api/admin/init_broker_recommend.py`
- **契约 / 数据对象**: `BrokerRecommend` 模型；TaskType.SYNC_BROKER_RECOMMEND；admin 请求 `{month: "YYYYMM"}` → `{task_id}`
- **下游消费方**:
  - **plan-02**（BrokerRecommendRepository + BrokerRecommendAnalysisService）：依赖本功能 `BrokerRecommend` 模型与 broker_recommend 表做只读聚合
  - **plan-03**（前端同步面板 BrokerRecommendSyncPanel + 分析页）：依赖 admin API `/api/v1/admin/init/broker-recommend` 触发同步；前端面板用固定 SWR key `task_types=sync_broker_recommend` 查自己的同步记录（范式参照 StockTop10SyncPanel）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 2（alembic autogenerate）必须在 Task 1（模型 + `__init__.py` 导出）完成后，否则 autogenerate 读不到新模型。
- **验证失败排查方向**:
  - 任务一直 running / 不被拾取 → 检查 `TaskRegistry.register(TaskType.SYNC_BROKER_RECOMMEND)` 是否执行（import 链是否被 main.py 加载）
  - 任务"取消后一直跑" → 检查 cancel_check 是否直查 `AsyncTask.status` 标量列（不能用 `manager.get_task()`，会因 identity map/expire_on_commit 读不到外部取消，参照 sync_top10_holders_task 注释）
  - 同步返回空数据 → 确认该月券商金股已发布（接口一般每月 1-3 日更新当月数据，doc 267）；该月未发布时 added=0 属正常
- **允许修改的额外文件**: 无（如 TaskRegistry 注册机制需调整另议）
- **E2E 不适用说明**: 本功能为纯后端数据同步 task handler，无用户可直接观察的前端 UI。但 task handler 是数据写入唯一执行者，已用「执行验证」（AC-08-execute-1~4，触发任务→completed→查表）作为强制验收项，不豁免。
- **风险备注**:
  - Tushare 积分已满足（代理服务相当于 15000 积分，broker_recommend 需 6000），无积分风险
  - 接口字段名已通过 doc 267 核实（ts_code/trade_date/name/broker/reason），无字段风险

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| broker_recommend 接口返回空（该月未发布） | service 记录 warning，返回 {added:0}，任务正常 completed | todo |
| 同券商对同股当月多次推荐 | 按 (ts_code, broker) 去重保留最新 trade_date，不堆积 | todo |
| 重复触发同月（覆盖式刷新） | DELETE WHERE month 后重写，幂等不堆积 | todo |
| 已有同类 running 任务 | admin API 并发保护拒绝创建，返回提示 | todo |
| 任务执行中被取消 | cancel_check 命中抛 asyncio.CancelledError，任务 cancelled | todo |
| Tushare 接口异常/网络超时 | _execute_with_retry 捕获，service 抛异常，task handler 记录 ERROR，任务 failed（不影响历史数据） | todo |
| 单批 commit 失败 | 逐批 commit 隔离，rollback 该批继续（参照 Top10 逐股票 rollback 范式） | todo |

### 前端边界场景

无（本功能无前端代码）。
