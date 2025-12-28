from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取异步数据库连接URL
DATABASE_URL = os.getenv("DATABASE_URL_ASYNC", "postgresql+asyncpg://sector_user:sector_pass@localhost:5432/sector_strength")

# 创建主异步引擎（用于 API 请求）
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 关闭SQL日志以提高性能
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    connect_args={
        "server_settings": {"jit": "off"},  # 关闭JIT以提高简单查询性能
        "command_timeout": 60,
    },
)

# 创建异步会话工厂（主引擎）
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 用于后台任务执行器的独立引擎（在独立线程中使用）
_task_executor_engine = None
_task_executor_session_factory = None


def get_task_executor_engine():
    """
    获取或创建任务执行器专用的数据库引擎

    这个引擎会在独立线程的 event loop 中使用，
    必须与主引擎分开以避免 event loop 冲突。
    """
    global _task_executor_engine, _task_executor_session_factory

    if _task_executor_engine is None:
        _task_executor_engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=5,  # 任务执行器需要的连接较少
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {"jit": "off"},
                "command_timeout": 60,
            },
        )
        _task_executor_session_factory = async_sessionmaker(
            bind=_task_executor_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    return _task_executor_engine, _task_executor_session_factory


async def close_task_executor_engine():
    """关闭任务执行器数据库引擎"""
    global _task_executor_engine, _task_executor_session_factory

    if _task_executor_engine is not None:
        await _task_executor_engine.dispose()
        _task_executor_engine = None
        _task_executor_session_factory = None


# 依赖注入函数
async def get_db():
    """获取数据库会话的依赖函数"""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()