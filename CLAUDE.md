# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sector Strength — 股票市场板块强弱指标系统。基于多周期均线计算板块/个股强度，提供热力图、排名、分析等可视化功能。

## Architecture

前后端分离架构，通过 Docker Compose 编排。

### Frontend (`web/`)

- **Next.js 16 + React 19 + TypeScript** — App Router，`src/` 目录结构
- **状态管理**: Redux Toolkit（`src/store/slices/`）+ SWR（数据获取 hooks 在 `src/hooks/`）
- **UI**: shadcn/ui + Radix UI + Tailwind CSS v4 + ECharts
- **认证**: 自定义 JWT 认证，token 存 localStorage，`middleware.ts` 做路由守卫
- **API 客户端**: `src/lib/api.ts`（ApiClient 类）+ `src/lib/fetcher.ts`（SWR fetcher），统一从 `NEXT_PUBLIC_API_URL` 拼接后端地址
- **路由保护**: `web/middleware.ts` — `/dashboard` 路径需要 access_token cookie
- **Providers**: `src/components/Providers.tsx` — Redux Store → AuthProvider 嵌套

### Backend (`server/`)

- **FastAPI + Python 3.11** — async，入口 `main.py`，业务代码在 `src/`
- **数据库**: PostgreSQL，**SQLAlchemy async**（asyncpg），双引擎架构：
  - 主引擎：API 请求用（`src/db/database.py` 的 `AsyncSessionLocal`）
  - 任务引擎：后台任务执行器用（`get_task_executor_engine()`），独立 event loop 避免冲突
- **数据源**: Tushare（中国股票市场数据）
- **后台任务**: `src/services/task_executor.py`（轮询 AsyncTask 表）+ `src/services/scheduler/job_manager.py`（APScheduler 定时任务）
- **认证**: JWT（`src/core/auth_service.py`），RBAC 管理员权限（`src/api/admin/rbac.py`）
- **迁移**: Alembic（`server/alembic/`）

### Backend Service Layers

```
API routes (src/api/) → Services (src/services/) → Repositories (src/repositories/) → Models (src/models/)
```

- `src/api/v1/` — 业务路由（sectors, stocks, strength, rankings, heatmap, analysis）
- `src/api/auth/` — 认证路由（login, registration, password reset, profile）
- `src/api/admin/` — 管理路由（数据初始化、任务管理、RBAC）
- `src/services/data_acquisition/` — Tushare 数据获取
- `src/services/calculation/` — 均线计算、强度计算、趋势分析
- `src/services/cache/` — 缓存管理（含 backends）
- `src/services/scheduler/` — APScheduler 定时任务
- `src/services/monitoring/` — 数据质量监控

### API Proxy

Next.js `next.config.ts` 将 `/api/:path*` 代理到后端 `NEXT_PUBLIC_API_URL`。后端路由有两个前缀可访问：`/api/v1/*` 和 `/v1/*`（兼容旧路径）。

## Commands

### Frontend (in `web/`)

```bash
npm run dev          # 开发服务器 (port 3000)
npm run build        # 生产构建
npm run lint         # ESLint
npm run test         # Jest 单元测试
npm run test:watch   # Jest watch 模式
```

### Backend (in `server/`)

```bash
uvicorn server.main:app --reload --port 8000   # 开发服务器
alembic revision --autogenerate -m "desc"       # 生成迁移
alembic upgrade head                             # 执行迁移
pytest                                           # 运行测试（配置在 pytest.ini）
pytest tests/test_auth.py -v                     # 运行单个测试文件
pytest -m "not slow"                             # 排除 slow 标记的测试
pytest -m integration                            # 只跑集成测试
```

### Docker

```bash
docker-compose up -d            # 启动全部服务（PostgreSQL + backend + frontend）
docker-compose up postgres -d   # 只启动数据库
```

## Environment

复制 `.env.example` 为 `.env` 并配置。关键变量：
- `DATABASE_URL_ASYNC` — 后端异步数据库连接
- `NEXT_PUBLIC_API_URL` — 前端访问后端的地址（开发: `http://localhost:8000`）
- `SECRET_KEY` — JWT 签名密钥

## Key Conventions

- 前端路径别名：`@/` → `web/src/`
- 后端 pytest 需要 PostgreSQL 实例运行，测试用 `ENVIRONMENT=test` 标识，测试环境使用 NullPool
- 后端模型基类：`src/models/base.py`（SQLAlchemy declarative_base）
- 认证 token 存在 localStorage（`accessToken`, `tokenType`），管理员 API 继承 `ApiClient` 自动携带 token
- 异步任务系统：任务类型通过 `TaskRegistry.register` 装饰器注册到 `task_handlers.py`
