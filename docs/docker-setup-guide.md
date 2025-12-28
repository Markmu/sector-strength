# Docker 开发环境设置指南

## 快速开始

### 1. 环境准备

确保您的系统已安装：
- Docker Desktop (Windows/Mac) 或 Docker Engine (Linux)
- Docker Compose v2.0+
- Git

### 2. 克隆项目

```bash
git clone <repository-url>
cd sector-strength
```

### 3. 配置环境变量

复制环境变量模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件，至少修改以下值：
```env
POSTGRES_PASSWORD=your-secure-password-here
JWT_SECRET=your-super-secret-jwt-key-here
```

### 4. 启动开发环境

一键启动所有服务：
```bash
docker-compose up -d
```

### 5. 验证服务

检查所有服务状态：
```bash
docker-compose ps
```

访问服务：
- 前端应用: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs
- 数据库: localhost:5432

### 6. 初始化数据库

首次启动后，需要使用 Alembic 初始化数据库结构：

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行数据库迁移
cd server
alembic upgrade head

# 退出容器
exit
```

### 7. 停止服务

```bash
docker-compose down
```

## 服务详情

### PostgreSQL 数据库
- **端口**: 5432
- **用户**: sector_user (默认)
- **密码**: 在 .env 文件中配置
- **数据库**: sector_strength
- **数据持久化**: 映射到 `./data/postgres`

### FastAPI 后端
- **端口**: 8000
- **热重载**: 开发模式自动启用
- **API文档**: http://localhost:8000/docs
- **代码挂载**: `./server:/app/server`

### Next.js 前端
- **端口**: 3000
- **热重载**: 开发模式自动启用
- **代码挂载**: `./web:/app/web`

## 开发工作流

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 重新构建服务
```bash
# 重新构建并启动
docker-compose up --build -d

# 重新构建特定服务
docker-compose up --build backend -d
```

### 进入容器
```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 进入数据库容器
docker-compose exec postgres psql -U sector_user -d sector_strength
```

### 数据库迁移（Alembic）

项目使用 Alembic 管理数据库迁移：

```bash
# 进入后端容器
docker-compose exec backend bash

# 查看当前迁移状态
cd server
alembic current

# 生成新的迁移文件（在修改模型后）
alembic revision --autogenerate -m "描述变更内容"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history
```

注意：Alembic 优先使用环境变量 `DATABASE_URL`，所以确保在容器内正确设置。

### 清理环境
```bash
# 停止并删除容器、网络、卷
docker-compose down -v

# 仅删除未使用的镜像
docker image prune -f
```

## 故障排除

### 端口冲突
如果遇到端口占用，修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8001:8000"  # 将主机端口改为8001
```

### 权限问题 (Linux)
确保 Docker 有足够权限访问项目目录：
```bash
sudo chown -R $USER:$USER .
```

### 数据库连接问题
1. 确保数据库服务已启动：`docker-compose ps`
2. 检查环境变量是否正确
3. 查看后端日志：`docker-compose logs backend`

### 前端构建失败
1. 清除 node_modules：
```bash
docker-compose exec frontend rm -rf node_modules
docker-compose exec frontend npm install
```
2. 重新启动前端服务：
```bash
docker-compose restart frontend
```

## 生产环境部署

生产环境使用不同的构建目标：
```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d
```

## 注意事项

1. **首次启动**可能需要较长时间，因为需要下载镜像和安装依赖
2. **数据持久化**：数据库数据存储在 `./data/postgres` 目录
3. **热重载**：代码更改会自动重启服务（后端）或热更新（前端）
4. **网络隔离**：所有服务在同一个 Docker 网络中，可以通过服务名相互访问

## 环境变量参考

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| POSTGRES_DB | sector_strength | 数据库名称 |
| POSTGRES_USER | sector_user | 数据库用户 |
| POSTGRES_PASSWORD | - | 数据库密码（必须设置） |
| DATABASE_URL | - | 数据库连接字符串 |
| ENVIRONMENT | development | 运行环境 |
| JWT_SECRET | - | JWT密钥（必须设置） |
| AKSHARE_TIMEOUT | 30 | AkShare API 超时时间（秒） |
| LOG_LEVEL | INFO | 日志级别 |

## 下一步

1. 查看 [API 文档](http://localhost:8000/docs) 了解可用的端点
2. 阅读 [开发指南](development-guide.md) 了解代码结构
3. 查看 [测试指南](testing-guide.md) 了解如何运行测试

## 技术支持

如遇到问题，请：
1. 查看本指南的故障排除部分
2. 检查 Docker 日志
3. 确认环境变量配置正确
4. 在项目 Issues 中搜索相关问题