---
feat_id: "plan-01"
title: "后端数据层与管理API"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 后端数据层与管理API

## 1. 功能概要

- **目标**: 建立股东监控组的数据层基础（两张新表 + Alembic 迁移含预定义种子数据），并提供管理员端的分组 CRUD API，使管理员能增删改监控组及其匹配规则。
- **完成后可观察结果**: 数据库中存在 `shareholder_groups` 和 `shareholder_group_rules` 两张表，内含 5 个预定义监控组及其匹配关键词。管理员可通过 curl 调用 Admin API 执行分组的增删改查操作，编辑匹配关键词后调用 preview 接口能看到匹配股数，新增的分组在列表 API 中可见，删除后不再出现。
- **依赖**: 无
- **关联验收标准**: [AC-06, AC-07, AC-10]
- **涉及架构模块**: ShareholderGroup Model, ShareholderGroupRule Model, ShareholderGroupRepository, ShareholderGroupService, Admin API routes
- **前置条件**: PostgreSQL 运行中，05 期 top10_float_holders 表已存在（preview 依赖股东数据）
- **不在范围**: 用户侧聚合查询 API（plan-02）、前端页面（plan-03/04）、数据同步

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/shareholder_group.py` | ShareholderGroup + ShareholderGroupRule 两个 Model |
| modify | `server/src/models/__init__.py` | 追加 import 语句和注册新 Model 到 __all__ |
| create | `server/src/repositories/shareholder_group_repository.py` | 继承 BaseRepository，扩展分组+规则联合查询方法 |
| modify | `server/src/repositories/__init__.py` | 追加 import 语句和导出新 Repository |
| create | `server/src/services/shareholder_group_service.py` | 分组管理 CRUD 服务 |
| create | `server/src/api/admin/shareholder_groups.py` | 管理端分组 API 路由 |
| modify | `server/src/api/admin/__init__.py` | 注册新路由 |

## 3. 实现规格

### 后端部分

#### 1. Model 定义

新建 `server/src/models/shareholder_group.py`：

**ShareholderGroup**：
- `id`: Integer, primary_key, autoincrement
- `name`: String(100), unique=True, nullable=False — 组名
- `description`: Text, nullable=True — 描述
- `sort_order`: Integer, default=0 — 排序权重
- `is_system`: Boolean, default=False — 是否系统预定义
- `created_at`: DateTime, server_default=func.now()
- `updated_at`: DateTime, onupdate=func.now(), nullable=True
- relationship: `rules` → ShareholderGroupRule（back_populates="group", cascade="all, delete-orphan"）

**ShareholderGroupRule**：
- `id`: Integer, primary_key, autoincrement
- `group_id`: Integer, ForeignKey("shareholder_groups.id", ondelete="CASCADE"), nullable=False
- `keyword`: String(200), nullable=False — 匹配关键词
- `created_at`: DateTime, server_default=func.now()
- relationship: `group` → ShareholderGroup（back_populates="rules"）
- Index: `ix_sgr_group_id` on group_id

在 `server/src/models/__init__.py` 的 `__all__` 列表中追加 `"ShareholderGroup"` 和 `"ShareholderGroupRule"`。

#### 2. Repository

新建 `server/src/repositories/shareholder_group_repository.py`，继承 `BaseRepository[ShareholderGroup]`。**构造函数参照兄弟 repo**（如 `FundRepository` / `SectorRepository`）：

```python
class ShareholderGroupRepository(BaseRepository[ShareholderGroup]):
    def __init__(self, session: AsyncSession):
        super().__init__(ShareholderGroup, session)  # BaseRepository.__init__ 需双参 (model, session)
```

- `get_with_rules()` → `selectinload(ShareholderGroup.rules)` 查询所有分组及关联规则
- `get_by_id_with_rules(id)` → 单个分组及规则，不存在则抛异常
- `replace_rules(group_id, keywords: list[str])` → 事务内：删除该组所有旧规则 → 批量插入新规则（使用 SQLAlchemy bulk_insert_mappings 或循环 add）

> **BaseRepository 基本方法使用说明**：Service 层的 create_group / update_group / delete_group 直接使用 BaseRepository 提供的 `create()` / `update()` / `delete()` 通用方法。自定义 Repository 方法（get_with_rules / get_by_id_with_rules / replace_rules）仅用于需要 join rules 的查询和规则替换场景。list_groups 中读取所有分组也使用 `get_with_rules()` 而非 BaseRepository 的 `list()` 方法，因为需要同时加载关联规则。

在 `server/src/repositories/__init__.py` 追加导出。

#### 3. Service

新建 `server/src/services/shareholder_group_service.py`：

**`list_groups()`**：
1. 调用 repo.get_with_rules() 获取所有分组
2. 对每个分组，查询 top10_float_holders 表用最新报告期 + 该组所有关键词做 LIKE 匹配，统计匹配的去重股票数
3. 返回 GroupListItem 列表：id, name, description, is_system, rule_count=len(rules), matched_stock_count, keywords=[r.keyword for r in rules]

**`create_group(name, description, keywords)`**：
1. 校验 name 唯一性（查询是否存在同名组）
2. 创建 ShareholderGroup 记录
3. 批量创建 ShareholderGroupRule 记录
4. 返回创建的分组

**`update_group(id, name, description, keywords)`**：
1. 获取分组（不存在则 404）
2. 若 name 有变更，校验新 name 唯一性
3. 更新分组字段
4. 若 keywords 有变更，调用 repo.replace_rules(id, keywords) 整体替换规则
5. 返回更新后的分组

**`delete_group(id)`**：
1. 获取分组（不存在则 404）
2. 删除分组（CASCADE 自动删除关联规则）
3. 返回成功

**`preview_match(keywords: list[str], exclude_group_id: int | None)`**：
1. 查询 top10_float_holders 最新报告期
2. 用所有 keywords 对 holder_name 做 `LIKE '%keyword%'` 匹配（OR 组合）
3. 统计去重股票数
4. 返回 `{ matched_stock_count: int }`

**安全要求（架构 §8.3）**：
- 所有 keyword 使用参数绑定，禁止字符串拼接 SQL
- LIKE 通配符转义：`keyword.replace('%', '\\%').replace('_', '\\_')`
- preview_match 方法中对每个 keyword 先转义再用 `f"%{escaped_keyword}%"` 做 LIKE 参数
- Admin API 路由使用 `require_admin` 依赖注入（`from src.api.deps import require_admin`），所有端点参数添加 `_admin: User = Depends(require_admin)`

#### 4. Admin API 路由

新建 `server/src/api/admin/shareholder_groups.py`，**文件内必须声明 prefix**：`router = APIRouter(prefix="/shareholder-groups", tags=["Admin - Shareholder Groups"])`（参照 `users.py` / `data_status.py`，`admin/__init__.py` 注册时不再加前缀——这是前端 `/admin/shareholder-groups` 命中 `/api/v1/admin/shareholder-groups` 的前提）：

- `GET /api/admin/shareholder-groups` → `service.list_groups()`
- `POST /api/admin/shareholder-groups` → `service.create_group(name, description, keywords)`
  - Request body: `{ name: str, description?: str, keywords: str[] }`（user_input）
- `PATCH /api/admin/shareholder-groups/{id}` → `service.update_group(id, name, description, keywords)`
  - Request body: `{ name?: str, description?: str, keywords?: str[] }`（user_input）
- `DELETE /api/admin/shareholder-groups/{id}` → `service.delete_group(id)`
- `GET /api/admin/shareholder-groups/preview` → `service.preview_match(keywords, exclude_group_id)`
  - Query params: keywords（逗号分隔，user_input）, exclude_group_id（可选，user_input）

在 `server/src/api/admin/__init__.py` 中注册路由：`router.include_router(shareholder_groups_router)`

**Response 命名约定**：Admin API 响应（含 `GroupListItem`）统一用 `to_camel`（参照 `users.py`）—— Service 返回 snake_case dict（如 `is_system`/`rule_count`/`matched_stock_count`），Pydantic `response_model` 经 `to_camel` alias 输出 camelCase（`isSystem`/`ruleCount`/`matchedStockCount`），与用户侧 API 一致（见 plan-02 §3.6 / 架构 §7.6）。

#### 5. Alembic 迁移（含种子数据）

运行 `alembic revision --autogenerate -m "add_shareholder_groups_tables"` 生成迁移文件。

手动编辑迁移文件，在 `upgrade()` 末尾追加种子数据插入（使用 `INSERT ... ON CONFLICT DO NOTHING` 保证幂等）：

预定义分组及关键词：

| 组名 | 描述 | 关键词 |
| --- | --- | --- |
| 国家队 | 汇金、证金等国家队资金 | 中央汇金, 中国证券金融, 国家外汇管理局, 国新投资, 基本养老保险基金 |
| 外资投行 | 著名外资投资银行 | 高盛, 摩根士丹利, 摩根大通, 瑞士银行, 美林, 花旗, 渣打 |
| 社保基金 | 全国社会保障基金 | 全国社保基金 |
| 保险公司 | 保险资金 | 中国人寿, 中国平安, 中国太保, 新华保险, 泰康资产 |
| 私募基金 | 知名私募机构 | 高毅资产, 景林资产, 淡水泉, 重阳投资, 幻方量化, 九坤投资 |

运行 `alembic upgrade head` 执行迁移。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 ShareholderGroup 和 ShareholderGroupRule Model | backend | done | 按实现规格 §1 定义 |
| 2 | 注册新 Model 到 models/__init__.py | backend | done | 追加到 __all__ 列表和 import |
| 3 | 创建 ShareholderGroupRepository | backend | done | 继承 BaseRepository，实现 get_with_rules / get_by_id_with_rules / replace_rules |
| 4 | 注册新 Repository 到 repositories/__init__.py | backend | done | 追加导出 |
| 5 | 创建 ShareholderGroupService | backend | done | 实现 list_groups / create_group / update_group / delete_group / preview_match |
| 6 | 创建 Admin API 路由 | backend | done | 5 个端点：列表 / 新增 / 编辑 / 删除 / 预览 |
| 7 | 注册新路由到 admin/__init__.py | backend | done | include_router |
| 8 | 生成 Alembic 迁移并添加种子数据 | backend | done | autogenerate 后手动编辑种子数据，ON CONFLICT DO NOTHING |
| 9 | 执行迁移验证 | backend | done | alembic upgrade head + 查库确认数据（5 组 / 24 规则） |

## 5. 验收标准

### AC-06 验收：管理员新增监控组

- [ ] AC-06 `POST /api/admin/shareholder-groups` 传入 `{ name: "QFII", keywords: ["瑞士银行", "摩根大通"] }` 返回 200 且新分组出现在 `GET /api/admin/shareholder-groups` 列表中
- [ ] name 重复时返回 400/409 错误

### AC-07 验收：管理员编辑匹配规则

- [ ] AC-07 `PATCH /api/admin/shareholder-groups/1` 传入 `{ keywords: ["中央汇金", "中国证券金融", "国新投资"] }` 返回 200，调用 `GET /api/admin/shareholder-groups` 确认规则已更新

### AC-10 验收：管理员删除监控组

- [ ] AC-10 `DELETE /api/admin/shareholder-groups/{id}` 返回 200，调用列表 API 确认该组不再出现

### 预览与列表验收

- [ ] `GET /api/admin/shareholder-groups/preview?keywords=中央汇金,社保` 返回 matched_stock_count > 0（前提：top10_float_holders 有数据）
- [ ] `GET /api/admin/shareholder-groups` 返回 5 个预定义分组，每组含 rule_count 和 keywords

### 数据层验收

- [ ] Alembic 迁移执行成功，数据库中 shareholder_groups 有 5 条记录，shareholder_group_rules 有约 25 条记录
- [ ] 重复执行迁移不报错（幂等性）

### 性能验收（架构 §8.1 目标）

- [ ] 管理端 CRUD API 响应时间 < 1s（curl 计时确认）

### 构建验收

- [ ] 后端启动无报错：`uvicorn server.main:app --port 8000` 可正常启动
- [ ] Alembic 迁移脚本语法正确，`alembic upgrade head` 成功

## 6. 验证命令

```bash
# 执行迁移
cd server && alembic upgrade head

# 查库确认种子数据
psql $DATABASE_URL -c "SELECT id, name, is_system FROM shareholder_groups ORDER BY id;"
psql $DATABASE_URL -c "SELECT group_id, keyword FROM shareholder_group_rules ORDER BY group_id, id;"

# 启动后端
cd server && uvicorn server.main:app --reload --port 8000 &

# 验证 Admin API（需管理员 token）
curl -s http://localhost:8000/api/admin/shareholder-groups -H "Authorization: Bearer {token}" | python3 -m json.tool

# 新增分组
curl -s -X POST http://localhost:8000/api/admin/shareholder-groups \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"QFII","keywords":["瑞士银行","摩根大通"]}' | python3 -m json.tool

# 预览匹配
curl -s "http://localhost:8000/api/admin/shareholder-groups/preview?keywords=中央汇金" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 编辑分组
curl -s -X PATCH http://localhost:8000/api/admin/shareholder-groups/1 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"keywords":["中央汇金","中国证券金融","国新投资"]}' | python3 -m json.tool

# 删除分组（使用新增的 QFII 分组 ID）
curl -s -X DELETE http://localhost:8000/api/admin/shareholder-groups/{qfii_id} \
  -H "Authorization: Bearer {token}" | python3 -m json.tool
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责（ShareholderGroupService）、§6.4 管理员新增/编辑监控组、§6.5 管理员删除监控组、§7.1-7.2 领域对象与 Schema、§7.3 API 边界（Admin 部分）
- **相关代码**:
  - `server/src/models/top10_float_holder.py` — preview_match 查询此表
  - `server/src/repositories/base.py` — BaseRepository 基类
  - `server/src/api/admin/__init__.py` — Admin 路由注册入口
- **契约 / 数据对象**:
  - `ShareholderGroup`: id, name(unique), description, sort_order, is_system, created_at, updated_at
  - `ShareholderGroupRule`: id, group_id(FK CASCADE), keyword, created_at
  - `CreateGroupRequest`: { name: str, description?: str, keywords: str[] }
  - `UpdateGroupRequest`: { name?: str, description?: str, keywords?: str[] }
  - `GroupListItem`: { id, name, description, isSystem, ruleCount, matchedStockCount, keywords }
- **下游消费方**: plan-02（读取 groups/rules 做聚合查询）、plan-03（前端调用 Admin API）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（Model → Repository → Service → API → Migration）
- **验证失败排查方向**:
  1. 迁移失败 → 检查 Model 定义和 __init__.py 注册
  2. API 404 → 检查 admin/__init__.py 路由注册
  3. preview 返回 0 → 检查 top10_float_holders 表是否有数据
  4. name 唯一性报错 → 检查 Model 中 unique constraint
- **允许修改的额外文件**: 无
- **暂停条件**: 迁移失败且非明显语法问题时暂停，需用户确认数据库状态
- **E2E 不适用说明**: 本功能为纯后端 API + 数据层，无可直接观察的用户界面。通过 curl 命令验证 API 行为即可，E2E 测试由 plan-03 承接。

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 创建分组时 name 重复 | 后端返回 400/409 错误，提示"组名已存在" | done |
| 创建分组时 keywords 为空列表 | 允许创建（后续可在前端加校验） | done |
| 更新分组 name 为其他已有组名 | 后端返回 400/409 错误 | done |
| 删除不存在的分组 | 返回 404 | done |
| preview 时 top10_float_holders 表无数据 | 返回 matched_stock_count: 0 | done |
| LIKE 关键词包含 % 或 _ 通配符 | Service 层自动转义为 \% 和 \_ | done |
| 种子数据重复执行迁移 | ON CONFLICT DO NOTHING 保证幂等 | done |

### 风险备注

- preview_match 查询需要读取 top10_float_holders 表最新报告期的数据做 LIKE 匹配，如果该表数据量很大（>10万条），首次查询可能较慢。首版接受此性能特征，架构评估单期 5 万条可接受。
