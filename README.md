# Sector Strength - 股票市场板块强弱指标系统

基于多周期均线的股票板块强度实时可视化分析系统。

## 🚀 功能特性

- 📊 板块强度热力图可视化
- 📈 多周期均线强度计算
- 🏆 板块和个股排名系统
- 🔍 详细的板块和个股分析
- 📱 响应式设计，支持多设备

## 🛠️ 技术栈

### 前端
- **框架**: Next.js 14 + TypeScript
- **UI组件**: shadcn/ui + Radix UI
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **图表**: ECharts

### 后端
- **框架**: FastAPI + Python 3.11
- **数据库**: PostgreSQL
- **ORM**: SQLAlchemy + asyncpg
- **数据源**: AkShare

### 部署
- **容器化**: Docker + Docker Compose
- **数据库**: PostgreSQL容器化
- **反向代理**: Nginx

## 📦 项目结构

```
sector-strength/
├── web/                 # Next.js前端应用
├── server/              # FastAPI后端应用
├── shared/              # 共享类型定义
├── docs/                # 项目文档
├── scripts/             # 脚本文件
├── docker-compose.yml   # Docker编排配置
├── Dockerfile.frontend  # 前端Docker配置
├── Dockerfile.backend   # 后端Docker配置
└── .env.example         # 环境变量模板
```

## 🚀 快速开始

### 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+
- Python 3.11+

### 开发环境启动

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd sector-strength
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑.env文件设置您的配置
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

4. **访问应用**
   - 前端: http://localhost:3000
   - 后端API: http://localhost:8000
   - API文档: http://localhost:8000/docs

## 📖 文档

- [产品需求文档](docs/prd.md)
- [技术架构文档](docs/architecture.md)
- [用户故事](docs/stories/)

## 🤝 开发贡献

1.  Fork项目
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  开启Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 数据来源: [AkShare](https://github.com/akfamily/akshare)
- UI组件: [shadcn/ui](https://ui.shadcn.com/)
- 图表库: [ECharts](https://echarts.apache.org/)