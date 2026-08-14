# 数据同步模块 Clean Code 评审报告

- **日期**: 2026-08-15
- **评审方法**: 按《代码整洁之道》(Robert C. Martin) 规条逐类扫描（死代码 / 重复 / 函数规条 / 命名与表达 / 结构 / 注释 / 边界行为 / 测试），5 个子模块并行全文评审，只读不改码。
- **评审范围**: `server/src/services/` 下数据同步相关约 **12,000 行**：

| 子模块 | 文件 | 行数 |
|---|---|---|
| 任务处理器 | task_handlers.py, task_fence.py | 2,538 |
| 任务执行/管理/调度 | task_executor.py, task_manager.py, scheduler/job_manager.py | 2,396 |
| 数据获取层 | data_acquisition/（tushare_client.py 等 7 文件） | 3,374 |
| 数据更新器 | data_updater/collector.py, data_update.py, calculator_updater/orchestrator.py, margin_daily_sync.py | 1,858 |
| 数据初始化 | data_init.py + data_init_* 系列 7 文件 | ~4,000 |

- **问题总数**: **154 条**（高 16 / 中 ~73 / 低 ~65）
- **测试安全网**: 总体扎实。task_manager（约 60 用例）、task_executor（fencing 全路径）、tushare market_daily/margin、data_init 主路径、margin_daily_sync（全分支）均有高质量测试；缺口见 §6。

---

## 1. 总体结论

模块的**并发基础设施和防御性设计是扎实的**（token fencing、条件 UPDATE 首因胜出、行锁双检、分页完整性守卫、5% 误删阈值），docstring 里大量"为什么"注释和实测教训记录是加分项。但整个模块患同一种病：**复制粘贴式扩展**。每个新数据域都是把上一个域的代码整段拷贝再改几个字段——31 个任务 handler 中 26 个同骨架、tushare_client 29 个取数方法 40-45% 是重复样板、executor 为 margin 整段复制了 350 行锁方法族、16/17 期三对基础设施函数 100% 相同。更严重的是**新标准建立后旧代码不回修**：同文件里有守卫的分页与裸奔的分页并存、三种行级异常策略并存、两种错误契约并存。此外发现 **8 个真实功能缺陷**（不只是整洁问题），其中 3 个涉及数据安全/静默失效，建议优先处理。

---

## 2. 真实功能缺陷（优先修复，均已人工复核源码）

| # | 缺陷 | 位置 | 影响 |
|---|---|---|---|
| B1 | `trigger_job` 调 `job.modify()` **无参**——APScheduler no-op，不触发任何执行，但记日志并返回 True；被真实端点 `POST /api/v1/admin/scheduler/trigger/{job_id}` 调用 | job_manager.py:374 | 管理员手动触发定时任务**静默失效**。测试只断言返回 True 未断言执行，放过了该 bug |
| B2 | `data_init_limit.py` 全文件**无一处 rollback**：`sync_limit_data` 表 1 的 delete 已进事务后若表 2 拉取抛错，异常被 range 循环的 `except: continue` 吞掉，失败日的 pending delete 随下一日 commit 一并提交 | data_init_limit.py:219, 327-331 | **误删当日已有数据**（删旧后无新数据写入）。且该服务零测试 |
| B3 | CalculationOrchestrator 是未完成脚手架：`np.random.randn` 造随机价、`_calculate_sector_from_stocks` 返回常量 50.0、两处 "TODO: 更新数据库"，但 `run_all_calculations` **每天挂在日更链上跑**，`calculations_performed` 统计的是随机数算出的分数 | orchestrator.py:123, 158, 178-211, 289 | 每日以 completed 状态上报随机结果；另有一处 session close 后继续传参的 use-after-close（orchestrator.py:143-155），一旦接入真实查询即踩雷 |
| B4 | `get_fund_list` / `get_fund_portfolio` 两个 offset 分页 `while True` 循环**无页数上限、无页签名重复守卫**——而同文件 1658/2225 行已实测注明"代理忽略 offset 重复回页"是真实故障模式（lifecycle 和 market_daily 均已加守卫） | tushare_client.py:658-688, 714-744 | 同一代理故障下**无限循环 + 内存无限膨胀**，OOM/永不返回 |
| B5 | `cancel_task` 读-判-写三步无行锁无条件更新（TOCTOU）：与 `complete_task` 竞态可把已 completed 任务覆盖成 cancelled；同文件 `request_cancel`:617 已示范条件 UPDATE 正解 | task_manager.py:184-202 | 竞态下任务终态被错误改写 |
| B6 | 生产模块 `from unittest.mock import AsyncMock, Mock`，并以 `isinstance(self.session, AsyncMock)` 分叉生产行为（两个 backfill 各一份） | data_update.py:13, 170, 352 | 测试逻辑泄漏进生产代码；`data_init.py:43` 的 `_safe_nested_tx` 同病（savepoint 创建失败被静默降级为无保护执行） |
| B7 | `get_top10_float_holders` / `get_broker_recommend` 声明 `async def` 但体内无任何 await——同步阻塞（网络+重试 sleep）伪装异步，调用方在事件循环里 await 会**卡住整个 loop** | tushare_client.py:1309, 1358 | 事件循环阻塞 |
| B8 | `fetch_missing_dates` 用 `weekday() < 5` 当交易日，忽略法定节假日，与全系统 TradingCalendar 口径不一致 | data_update.py:539-544 | 节假日必误报缺失，触发无意义补齐任务 |

---

## 3. 跨模块共性主题（结构性问题根因）

### 主题 A：复制粘贴式扩展（最大问题，估计可净删 ~2,000 行 / ~16%）

| 重复点 | 规模 | 提取方案 |
|---|---|---|
| task_handlers：31 个 handler 中 26 个同骨架，分三组（A 组 result 字典驱动 12 个 / B 组异常驱动 14 个 / C 组 fence 逐日循环 2 个） | B 组每个 35-50 行仅差 3 点 | 装饰器工厂 `simple_sync_task(...)` / `result_service_task(...)`；C 组抽 `_run_fenced_daily_range` 模板 |
| 16/17 期三对基础设施函数**逐字 100% 相同**：`_build_*_result`、`_persist_*_result`、`_finalize_*_stop` | ~150 行 | 合并为单一通用函数（净删 ~150 行） |
| task_executor：margin 锁方法族是 mm 族整段复制（`_ensure/_close/_maintain/_on_acquired/_lose/_consume_stop` 六对） | ~350 行 | 引入 `OwnerLockState` 数据对象，六套方法参数化为单套 |
| tushare_client：29 个取数方法共享"取 pro→_fetch 闭包→重试→空判→行转换→日志"骨架 | 骨架占全文 40-45%（约 950-1,000 行） | 第一步抽 `_call_pro(endpoint, **params)`，18 个透传方法各缩至 3-8 行（净删 ~600 行） |
| data_init 系列 7 文件：进度回调（7 份逐字相同）、取消检查、`_parse_date`/`_to_decimal` 等 helper 同名不同语义、范围回灌循环 3 份 | ~330 行样板 + ~270 行回灌 | `data_init/_base.py` 基类 + `_convert.py` + `backfill_trading_days()` 通用循环（合计净删 ~650-750 行） |
| 首因胜出算法（cancel/timeout 比较、同刻 cancel 优先）3 处手工复制 | task_executor.py:692/872, task_manager.py:850 | 抽 `_first_stop_cause()` 放 task_fence |
| **fenced 类型集合 4 处独立定义**（task_fence.py:37、task_manager.py:32+57、task_executor.py:46 别名），靠"与 XX 对齐"注释人工同步，漏改零报错 | 跨 3 文件 | task_fence 单一定义源，其余 import |
| data_update.py：`backfill_by_range` 与 `backfill_by_date` ~150 行主体逐行相同 | 仅日期维度不同 | 拆 `_upsert_symbol_quotes()` 共享 |

### 主题 B：新旧两套体系并存（迁移遗留未收敛）

| 并存的两套 | 位置 | 后果 |
|---|---|---|
| 同一张 `stock_daily_market_data` 两条写入路径：手动补齐 select-then-write 且 `change=None`；自动日更 `pg_insert + on_conflict` 且计算 change/change_percent | data_update.py:246-282, 417-452 vs collector.py:325-364 | 同一行数据经两条路径落库**字段口径不同**。应收敛为单一 upsert 服务 |
| 取消机制：DataInitService 用 `cancel()` 置位 + InterruptedError；系列 6 文件用 cancel-check 回调 + CancelledError | data_init.py:113 vs data_init_limit.py:58 等 | 任务框架要同时伺候两种异常 |
| 错误契约：同文件内 `raise` 与返回 `{"success": False}` 并存；返回信封 `{"success":...}` vs `{"added"/"failed"}` 两套 | data_init.py:822/1112/1256；:343 vs limit:108 | 调用方无法统一处理 |
| tushare 两代代码：第 16 期带完整性守卫/硬失败 vs 早期静默吞行（`except: pass`）／无守卫分页 | tushare_client.py:425, 526, 310 vs 1651+ | 新标准未回修旧代码（B4 即后果） |
| 命名双轨：`get_daily_data` 返回 typed 模型（千元已转元）vs `get_index_daily` 返回原始 dict（原始单位） | tushare_client.py:429 vs 1464 | 同族方法不同返回契约，易误用 |

### 主题 C：迭代期号注释（日志式注释，5 个子模块均存在）

"第 14 期""plan-05""16 期 §8.2-5"等期号/章节号注释遍布 task_handlers（枚举值 68-96）、task_executor/manager 模块 docstring、collector、data_init 系列。它们对当期读者是噪声、对后期读者是考古题。保留"为什么"的句子，期号交 git/CHANGELOG。另发现一处**注释撒谎**：job_manager.py:217 断言"APScheduler 默认会移除抛异常的 job"与 3.x 实际行为不符，且与 `_daily_data_update` 的 raise 行为矛盾。

### 主题 D：测试逻辑泄漏进生产代码

- data_update.py:13 `AsyncMock` import + isinstance 分叉（B6）
- data_init.py:43 `_safe_nested_tx` 为 AsyncMock 测试把 savepoint 失败静默降级
- collector.py:61 `get_session` 自述"为测试 patch 而存在"；同文件三种取 session 方式并存
- task_fence.py:95 `register_coroutine`/`unregister` 生产零调用（仅测试在调），`invalidate()` 声称的"取消全部注册协程"能力从未生效——文档说有、实际没有

### 主题 E：死代码规模可观（零风险先删，约 -300 行）

- tushare_client：`get_fund_share`、`get_fund_nav`（docstring 自述已被取代）+ models.py 5 个零引用模型 + exceptions.py 2 个从未 raise 的异常 + sector_types 2 个零引用常量（~180 行）
- job_manager：55 行注释掉的 job 注册代码 + 3 个零调用回调（`_etf_daily_snapshot` 等，其中一个注释声称"保留以兼容引用"经 grep 不成立）+ 2 个仅被测试养活的方法
- 各文件未使用导入/函数内重复导入/不可达防御分支约 15 处
- tests/test_data_acquisition/ 目录已空仅剩 stale pyc（akshare 测试被整体删除）

---

## 4. 各子模块问题清单（摘要）

> 完整逐条清单（含行号与修复建议）见评审过程记录；以下为每模块 Top 问题。风险：🔴高 🟡中 ⚪低。

### 4.1 task_handlers.py + task_fence.py（32 条：高5/中12/低15）

- 🔴 三对 16/17 期函数逐字复制（1762-1877 vs 2092-2183）；`sync_market_metrics_task` 205 行 / `sync_market_margin_task` 157 行且骨架 90% 相同（1880-2084, 2186-2342）
- 🔴 `_check_cancelled` 闭包 + identity-map 坑关键注释三处逐字复制（1051/1127/1196）；`original_error` 拼接 4 处复制
- 🔴 fenced 集合 3 处定义（见主题 A）
- 🟡 `raise Exception` 裸异常 13 处；可选日期解析 7 处复制；`__all__` 缺 5 个 handler 且位于文件中部（641-669）；handler 直调 `tushare._get_pro_api()` 等 3 处私有方法；"取今天"两种时区口径（1476 vs 1720）；逐日任务失败语义两套（部分失败静默成功 vs 抛摘要异常）；`_persist_*_result` 名字掩蔽 commit 副作用；backfill_ma_task 循环内重建 service + 双写日志
- ⚪ 约 40 处复述式注释；枚举期号注释；`_make_progress_callback` 假 async；魔术数 days=60 等

### 4.2 task_executor.py + task_manager.py + job_manager.py（34 条：高4/中13/中低8/低9）

- 🔴 B1 trigger_job no-op；`_execute_task` 130 行状态机全内联（352-482）
- 🟡 B5 cancel_task TOCTOU；executor mm/margin 350 行成对复制；`_poll_and_execute` 78 行六区段混杂；首因胜出算法 3 处复制；`_log_message` 名字掩蔽 commit（终态原子性依赖日志函数的隐藏行为——谁"优化"掉就静默破坏行锁原子性）；`update_progress` 双 UPDATE 非原子；`check_task_timeout` N+1；三个"取消"层级命名仅靠中缀区分；CancelledError 内 await DB 写可被二次 cancel 中断
- ⚪ job_manager 55 行注释代码 + 3 个死回调；`getattr(job, 'next_run_time')` 防御掩盖真实错误；超时 14400 等魔术数

### 4.3 data_acquisition/（33 条：高1/中14/低18）

- 🔴 B4 fund 分页无守卫
- 🟡 19 处手写 `_df_to_rows` 等价循环 + 空判 idiom 25 次 + `_fetch` 闭包 33 个；限流重试引擎与 akshare 整段复制且关键词表已漂移（akshare 版把 "empty"/"no data" 当不可重试关键词，"Empty reply from server" 会被误判跳过重试）；B7 假 async 两方法；基类签名与实现漂移（`get_sector_daily_data` 缺 `sector_code`，经基类调 SW 必抛 ValueError）；行级异常三套标准并存（`except: pass` 静默丢行）；THS 分支每次全量拉板块列表按名称线性反查；单类 2278 行承载 8 个业务域
- ⚪ 死代码 ~180 行；`datetime.now()` 做限流基准（时钟回拨多睡）；`MarketDataIntegrityError` 定义在 models.py；假开关 `DATA_SOURCE_TYPE`（校验后无条件 Tushare）

### 4.4 collector.py + data_update.py + orchestrator.py + margin_daily_sync.py（27 条：高4/中13/低10）

- 🔴 B3 orchestrator 随机数据不落库挂日更链 + use-after-close；B6 AsyncMock 泄漏；两套写入体系并存（主题 B）
- 🟡 collector 吞掉 CalculationOrchestrator import 失败换成 no-op stub（日更静默"计算 0 实体"仍 completed）；"refresh_range + 开市守卫"骨架早间/日更 job 两写；backfill 两方法 ~150 行重复；fetch_missing_dates 节假日误报（B8）；先查全部 symbol 再逐个回查 Stock 的 N+1；`_update_market_data` 125 行 / `run_daily_update` 120 行 / `_update_sector_fund_flow` 100 行混杂层级
- ✅ margin_daily_sync.py 是四个文件中最整洁的（单一职责、时间可注入、不越权写库、10 用例全分支覆盖），可作为后续 sync 入口模板

### 4.5 data_init.py + data_init_* 系列（28 条：高2/中13/低13）

- 🔴 B2 limit 无 rollback；三个历史数据函数逐 quote 逐条 SELECT 查存在性（~5,882 股 × 60 日 ≈ 35 万次查询 N+1，文件自己承认该规模）
- 🟡 三份"取标的→查存在→构造→commit→汇报"骨架 ~250 行重复；limit 三表同步同段复制三遍；范围回灌循环 3 份；同名 helper 不同语义（`_to_decimal` 三版，仅一版查 NaN）；`skipped` 计数语义二义；范围超限三种策略；进度两阶段不衔接；取消机制/错误契约/提交粒度各两三套（主题 B）
- ⚪ 18 个超百行函数（最长 init_sectors 210 行）；范围同步靠置 `self._progress_callback = None` 再闭包绕过自设短路，脆弱不可重入
- ✅ `init_stocks_lifecycle`（preload + diff + 批量 upsert）是全系列最佳实践模板，推广它可同时解决重复与 N+1；灾难边界防御（港股失败跳过清理避免误删、5% 删除阈值）值得肯定

---

## 5. 建议修复次序（按 clean-code 简化次序 + 风险排序）

1. **先修真实缺陷**（§2 的 B1-B8）：每个先补回归测试再修。B1/B2/B4 优先（静默失效 + 数据误删 + OOM）。
2. **零风险清理**：删死代码/注释掉的代码/未用导入（主题 E，约 -300 行）；删复述式注释与期号注释。
3. **消最小粒度重复**：`_parse_optional_date`、`_make_cancel_checker`、`_format_error_detail`、`_first_stop_cause`、`_opt_str`、fenced 集合单一定义源。
4. **提公共骨架**（测试安全网已就位，行为不变）：
   - tushare：`_call_pro`（净删 ~600 行）→ 补 B4 守卫 → 统一重试引擎给 akshare → 再考虑按业务域 mixin 拆分
   - executor：`OwnerLockState` 参数化六对锁方法（净删 ~350 行）
   - task_handlers：B/A 组装饰器工厂 + C 组模板方法（两个 200/157 行 handler 各缩至 ~60 行）
   - data_init：`_base.py` 基类 + `_convert.py` + `backfill_trading_days()`（净删 ~650-750 行）
5. **收敛两套体系**（需产品决策，建议单独排期）：单一 upsert 写入服务、统一取消机制、统一错误契约与结果信封、orchestrator 摘除或补齐。
6. **补测试缺口**：trigger_job 断言执行、limit 服务三用例（幂等/失败继续/取消）、akshare fetcher、cancel_task 竞态、orchestrator 真实行为。

---

## 6. 测试安全网评估

| 覆盖良好 | 缺口 |
|---|---|
| task_manager ~60 用例（fencing 互斥/首因/终态/recovery 三分支/double-mark） | cancel_task TOCTOU 竞态、update_progress 双写、executor 停止/关闭竞态 |
| task_executor 753 行（token 轮换/锁丢失/standby/mm+margin 隔离） | register_coroutine 只被测试养活（掩盖 invalidate 未生效） |
| tushare market_daily 927 行（分页守卫/行校验）+ margin 358 行（重试语义） | akshare_fund_flow 0 直接测试（测试文件已删）；fund 分页 offset 失效用例缺失 |
| data_init 主路径 840 行；margin_daily_sync 10 用例全分支 | LimitDataInitService 零测试（B2 正是它能拦的）；by_date_range 断点续传分支；5% 阈值分支 |
| 两个最复杂 handler 直接测试 17 用例 | 其余 ~25 个简单 handler 无直接测试（仅 `__all__` 契约冒烟） |

---

## 7. 值得保留的优点（重构时不要丢）

1. **并发原语选型正确且锚定架构**：条件 UPDATE 首因胜出、行锁双检 token、recovery 逐行独立事务 + double-mark critical 告警；`task_fence` 的 fence 行锁双检注释（task_fence.py:136-169）是全模块最佳"为什么"注释样本。
2. **`_paginate_market_daily` 完整性守卫体系**（页签名重复/满页无新增 key/跨页重复/硬页数上限，禁止 drop_duplicates 静默修复）——应作为所有分页循环的模板回修 B4。
3. **`init_stocks_lifecycle` 的 preload+diff+批量 upsert 模式**——回修三个历史数据函数即同时解决重复与 35 万次 N+1。
4. **统一三参签名 + TaskRegistry 注册模式**：接口一致性本身是对的（重复是实现层的错，不是模式的错）。
5. **margin_daily_sync.py 的设计**（守卫/缺口/建任务单一职责、today 可注入、不越权写库）——后续新 sync 入口照此写。
6. **docstring 把 Provider 实测坑文档化**（offset 失效、suspend_d 列名漂移、margin 不传 fields 的原因）——高价值领域知识，重构时保留。

---

## 8. 统计汇总

| 子模块 | 高 | 中 | 低 | 小计 |
|---|---|---|---|---|
| task_handlers + task_fence | 5 | 12 | 15 | 32 |
| task_executor + task_manager + job_manager | 4 | 13 | 17 | 34 |
| data_acquisition | 1 | 14 | 18 | 33 |
| collector + data_update + orchestrator + margin_daily_sync | 4 | 13 | 10 | 27 |
| data_init 系列 | 2 | 13 | 13 | 28 |
| **合计** | **16** | **~65** | **~73** | **154** |

去重重构全部落地后估计可**净删约 2,000 行（~16%）**，并消除"新增一个数据域要复制 4-5 处"的扩展成本。
