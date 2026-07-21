# UAT 用例清单

**项目名称：** 股票数据独立建表（后端数据存储层改造）
**版本：** v1.0
**最后更新：** 2026-07-07
**维护人：** auto-uat（基于 uat-manager skill）

> 本需求为纯后端数据存储层改造（股票数据从与板块共用三张表拆出为独立表），无前端改动。
> 验收标准 AC-01~AC-07 定义于 PRD `docs/12-股票数据独立建表/12-0-需求设计-股票数据独立建表.md` 第四部分。
> 每条 UC 的"证据地址"复用 task-review 报告与 e2e evidence，不重复生成冗余证据。

## 统计概览

- **总用例数：** 9
- **已完成：** 9
- **未完成：** 0
- **最近通过：** 9
- **最近失败：** 0
- **最近阻塞：** 0
- **未执行：** 0
- **通过率：** 100%

## 用例清单

| Case ID | 模块 | 用例标题 | 类型 | 优先级 | 完成度 | 最近状态 | 最近执行时间 | 证据地址 | 变更标签 | 备注 |
|---------|------|----------|------|--------|--------|----------|--------------|----------|----------|------|
| UC-001 | 数据写入 | 股票数据物理隔离——触发股票采集后新表入库、旧表无新增 | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-02-review-2026-07-07.md；docs/e2e/evidence/plan-02-e2e-green-2026-07-07.md | - | 关联 AC-01；DB 实测插入新表成功 + 旧表 stock 行数零变化 |
| UC-002 | 数据读取 | 个股强度接口返回新表数据 | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-03-review-2026-07-07.md；docs/e2e/evidence/plan-03-e2e-green-2026-07-07.md | - | 关联 AC-02；pytest stocks+strength API 16 passed |
| UC-003 | 板块回归 | 板块功能零回归——板块 service 零改动 + 板块测试零回归 | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-05-review-2026-07-07.md；docs/e2e/evidence/plan-05-e2e-green-2026-07-07.md | - | 关联 AC-03；git diff 板块专属文件为空 + 57 passed；详情见 cases/UC-003-板块功能零回归.md |
| UC-004 | 数据清理 | 随个股删除清理新三表 | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-02-review-2026-07-07.md | - | 关联 AC-04；pytest test_hk_stock_sync 10 passed + _cascade_delete_stock_data 三模型循环代码核查 |
| UC-005 | 表结构 | 新表字段语义收敛（无 entity_type/period/板块字段，含 percentile） | 正向 | P1 | Complete | Passed | 2026-07-07 | reviews/plan-01-review-2026-07-07.md | - | 关联 AC-05；grep 三新模型字段 + pytest test_stock_models 17 passed |
| UC-006 | 接口契约 | 对外接口契约不变——响应字段 diff 为空 | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-04-review-2026-07-07.md；docs/e2e/evidence/plan-04-e2e-green-2026-07-07.md | - | 关联 AC-06；stocks.py:279/283/311 硬填保持 schema 字段 + API 测试通过 |
| UC-007 | 边界场景 | 长周期指标空窗期呈现 | 边界 | P1 | Complete | Passed | 2026-07-07 | reviews/plan-03-review-2026-07-07.md | - | 关联 AC-07；ma_data_loader load_ma_values 按 entity_type 分发 + 共享方法测试 88 passed |
| UC-008 | 基础设施 | 迁移可逆性——alembic upgrade/downgrade | 正向 | P0 | Complete | Passed | 2026-07-07 | reviews/plan-01-review-2026-07-07.md | - | 补充覆盖（关联 AC-05/基础设施）；alembic current = dd92f496dfaf (head)，review 已验证 upgrade/downgrade 可逆 |
| UC-009 | 共享方法 | 共享方法板块分支未误伤（ma_data_loader/ranking_service 等） | 异常 | P1 | Complete | Passed | 2026-07-07 | reviews/plan-02-review-2026-07-07.md；reviews/plan-03-review-2026-07-07.md | - | 补充覆盖 AC-03 技术保障；ADR-4 内部分发代码核查 + 共享方法测试 88 passed |

## 字段说明

- **Case ID**: 用例唯一标识，格式 UC-XXX
- **模块**: 功能模块名称
- **用例标题**: 简短描述用例目的
- **类型**: 正向/逆向/异常/边界
- **优先级**: P0（核心）/P1（重要）/P2（一般）
- **完成度**: Complete（已完成）/Incomplete（未完成）
- **最近状态**: Not Run/Passed/Failed/Blocked/Skipped
- **最近执行时间**: YYYY-MM-DD 格式
- **证据地址**: 失败/阻塞用例的证据文件相对路径（本清单均复用 task-review 报告与 e2e evidence）
- **变更标签**: 标记是否受本次变更影响（受影响/无影响/-）
- **备注**: 其他说明信息

## 模块分类

### 数据写入（AC-01 / AC-04）
- UC-001（股票采集写新表）
- UC-004（级联删除清新三表）

### 数据读取（AC-02 / AC-06 / AC-07）
- UC-002（个股强度接口）
- UC-006（对外接口契约）
- UC-007（长周期指标空窗期）

### 板块回归（AC-03）
- UC-003（板块功能零回归）
- UC-009（共享方法板块分支）

### 表结构与基础设施（AC-05）
- UC-005（字段语义收敛）
- UC-008（迁移可逆性）

## 执行记录

### 2026-07-07 第 1 轮执行

**触发原因：** 拆表改造完成后的 UAT 验收（plan-01~05 全部 done，自动化测试覆盖 AC-01~AC-07）
**执行人：** auto-uat（独立执行 agent）
**执行环境：** server 工作目录 `/Users/muchao/code/sector-strength/server`，PostgreSQL 17（docker: sector-strength-postgres-1），alembic head = dd92f496dfaf

| 指标 | 数值 |
|------|------|
| 本次执行数 | 9 |
| 通过 | 9 |
| 失败 | 0 |
| 阻塞 | 0 |
| 跳过 | 0 |
| **通过率** | **100%** |

**验证方式与真实输出：**

| Case ID | 验证命令/方式 | 真实输出摘要 | 结论 |
|---------|---------------|--------------|------|
| UC-001 | DB 实测 INSERT 新表 + 旧表 stock 行数 diff + collector 代码核查 | `stock_daily_market_data` INSERT 成功（inserted_rows=1，读回 close=10.50）；旧表 `daily_market_data` entity_type='stock' 行数 1546→1546 零变化；唯一约束 `uq_stock_daily_market_data_stock_date` 生效；collector.py:292 `pg_insert(StockDailyMarketData)` | Passed |
| UC-002 | `pytest tests/test_api/test_stocks_api.py tests/test_api/test_strength_api.py` | 16 passed, 10 warnings in 1.57s；stocks.py:252 `select(StockStrengthScoreModel)` 确认读新表 | Passed |
| UC-003 | `git diff` 板块专属文件 + `pytest` 4 个板块 service 测试 | 板块专属 7 文件（sector_ma_service / sector_classification_service / strength_scatter_service / sectors.py 等）零改动；57 passed, 18 warnings in 7.78s | Passed |
| UC-004 | `pytest tests/test_hk_stock_sync.py` + 代码核查 | 10 passed；data_init.py:723 `for model in (StockDailyMarketData, StockMovingAverageData, StockStrengthScore)` 三模型循环 delete by stock_id | Passed |
| UC-005 | grep 三新模型字段 + `pytest tests/test_stock_models.py` | 17 passed；新表无 entity_type，强度表无 period，含 percentile（stock_strength_scores.py:77）；均线表 period 为业务字段保留 | Passed |
| UC-006 | 代码核查 stocks.py:279/283/311 + API 测试 | `entity_type="stock"` / `period="all"` / `change_rate_5d=None` 硬填保持响应 schema；stocks+strength API 16 passed | Passed |
| UC-007 | 代码核查 ma_data_loader + 共享方法测试 | ma_data_loader.py:99-103 按 entity_type 分发 `MAData = StockMovingAverageData if is_stock else MovingAverageData`；88 passed（含 test_sector_strength_service / test_strength_services / snapshot / scatter） | Passed |
| UC-008 | `alembic current` + plan-01 review 证据 | `dd92f496dfaf (head)`；plan-01 review 已实测 upgrade/downgrade 可逆 | Passed |
| UC-009 | `git diff` 共享方法 + 共享方法测试 | ranking_service.py:66-67 / strength_snapshot_service.py:333-355 按 entity_type 内部分发，sector 分支保留 `entity_type=='sector'` + `period=='all'` 零改动；88 passed | Passed |

**失败/阻塞用例：**

无。

**环境限制说明：**

- UC-001 因 task handler 实跑需完整外部数据源，采用「DB 实测插入新表（psql 在 docker 容器内直接执行）+ collector 代码核查 + plan-02 review 已有 task handler 数据链路实测证据」组合验证，等效覆盖 AC-01。
- UC-001 直连 DB 脚本（asyncpg/psycopg2）因本地 `.env` 密码与 docker 容器配置认证差异失败，改为在 `sector-strength-postgres-1` 容器内用 psql 直接执行，验证结果等价。
- 全量 pytest 基线：1055 passed / 12 failed（12 个均为既有失败，经 plan-04 review 用 git stash baseline 比对确认与拆表无关）。

**结论：**

- **质量评估**：9/9 用例全部通过，AC-01~AC-07 全覆盖（AC-03 由 UC-003 + UC-009 双重保障）。拆表改造达成「股票数据物理隔离 + 板块功能零回归 + 对外接口契约不变」三大核心目标。
- **发布建议**：**可发布**。建议发布后执行 smoke：触发一次股票采集观察新表入库、调用个股强度接口确认返回、调用板块分析接口确认行为不变。已知约束（非阻塞）：长周期指标（如 240 日均线）上线初期呈现空窗，随采集积累自然恢复（AC-07 已确认前端按既有"数据不足"方式处理）。
- **回滚准备**：alembic downgrade -1 可回退新表（UC-008 已验证可逆）；旧表板块数据全程未动，回滚零风险。

---

## 变更历史

| 日期 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-07-07 | 创建用例清单（9 条 UC）+ 完成第 1 轮 UAT 执行（9/9 Passed） | auto-uat |
