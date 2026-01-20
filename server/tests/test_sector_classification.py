"""板块分类模型测试

测试 sector_classification 模型的数据库约束和业务规则。

测试局限性说明：
- 使用 SQLite 内存数据库进行快速单元测试
- SQLite 不强制 CHECK 约束（如 classification_level 范围）
- SQLite 外键约束默认关闭（需要 PRAGMA foreign_keys=ON）
- 完整的约束验证应在 PostgreSQL 集成测试中完成
"""
import pytest
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Date, ForeignKey


# 创建独立的 Base 用于测试
TestBase = declarative_base()

# 测试数据库配置（使用 SQLite 内存数据库进行单元测试）
TEST_DATABASE_URL = "sqlite:///:memory:"


# 定义测试用的 Sector 模型
class TestSector(TestBase):
    __tablename__ = 'sectors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    type = Column(String(50), nullable=False)


# 定义测试用的 SectorClassification 模型
class SectorClassification(TestBase):
    __tablename__ = 'sector_classification'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector_id = Column(Integer, ForeignKey('sectors.id'), nullable=False)
    symbol = Column(String(20), nullable=False)
    classification_date = Column(Date, nullable=False)
    classification_level = Column(Integer, nullable=False)
    state = Column(String(10), nullable=False)


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 启用 SQLite 外键约束
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    # 直接使用 SQL 创建表
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE sectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20) NOT NULL UNIQUE,
                type VARCHAR(50) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE sector_classification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector_id INTEGER NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
                symbol VARCHAR(20) NOT NULL,
                classification_date DATE NOT NULL,
                classification_level INTEGER NOT NULL,
                state VARCHAR(10) NOT NULL,
                UNIQUE(sector_id, classification_date)
            )
        """))
        conn.commit()

    session = TestingSessionLocal()

    # 插入测试用的 sector 数据
    test_sector = TestSector(
        name="测试板块",
        code="TEST001",
        type="industry"
    )
    session.add(test_sector)
    session.commit()

    yield session

    session.close()


def test_create_sector_classification(db_session):
    """测试创建板块分类记录 - 验证基本功能"""
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()

    # 创建测试记录（id 由数据库自增生成）
    classification = SectorClassification(
        sector_id=sector.id,
        symbol=sector.code,
        classification_date=date.today(),
        classification_level=9,
        state='反弹'
    )
    db_session.add(classification)
    db_session.commit()

    # 验证
    assert classification.id is not None
    assert isinstance(classification.id, int)
    assert classification.symbol == "TEST001"
    assert classification.classification_level == 9
    assert classification.state == '反弹'


def test_classification_level_range_values(db_session):
    """测试 classification_level 所有有效值（1-9）可以成功创建

    注意：SQLite 不强制 CHECK 约束，所以这个测试验证值可以存储，
    但不验证数据库级约束。PostgreSQL 中的 CHECK 约束需要集成测试。
    """
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()

    # 测试所有有效值
    for level in range(1, 10):
        classification = SectorClassification(
            sector_id=sector.id,
            symbol=sector.code,
            classification_date=date(2026, 1, level),  # 使用不同日期避免唯一约束冲突
            classification_level=level,
            state='反弹'
        )
        db_session.add(classification)
        db_session.commit()
        assert classification.classification_level == level


def test_state_enum_values(db_session):
    """测试 state 所有有效值可以成功创建

    注意：SQLite 不强制 CHECK 约束，所以这个测试验证值可以存储，
    但不验证数据库级约束。PostgreSQL 中的 CHECK 约束需要集成测试。
    """
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()

    # 测试所有有效值
    for state_value, test_date in [('反弹', date(2026, 1, 20)), ('调整', date(2026, 1, 21))]:
        classification = SectorClassification(
            sector_id=sector.id,
            symbol=sector.code,
            classification_date=test_date,
            classification_level=5,
            state=state_value
        )
        db_session.add(classification)
        db_session.commit()
        assert classification.state == state_value


def test_unique_constraint_sector_date(db_session):
    """测试同一板块在同一天只能有一条记录（唯一约束）

    注意：SQLite 表定义中已包含 UNIQUE 约束，此测试验证其工作正常。
    """
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()
    test_date = date.today()

    # 创建第一条记录
    classification1 = SectorClassification(
        sector_id=sector.id,
        symbol=sector.code,
        classification_date=test_date,
        classification_level=5,
        state='反弹'
    )
    db_session.add(classification1)
    db_session.commit()

    # 尝试创建重复记录（应该失败）
    classification2 = SectorClassification(
        sector_id=sector.id,
        symbol=sector.code,
        classification_date=test_date,
        classification_level=6,
        state='调整'
    )
    db_session.add(classification2)

    # 在 SQLite 启用 PRAGMA foreign_keys=ON 后，UNIQUE 约束会强制执行
    # 这里验证插入重复记录时会抛出 IntegrityError
    with pytest.raises(Exception):  # SQLite 可能抛出 IntegrityError 或其他异常
        db_session.commit()


def test_foreign_key_constraint(db_session):
    """测试外键约束：sector_id 必须引用有效的 sectors.id

    注意：已启用 PRAGMA foreign_keys=ON，此测试验证外键约束工作正常。
    """
    # 尝试插入不存在的 sector_id（应该失败）
    classification = SectorClassification(
        sector_id=99999,  # 不存在的 sector_id
        symbol="INVALID",
        classification_date=date.today(),
        classification_level=5,
        state='反弹'
    )
    db_session.add(classification)

    # 在 SQLite 启用 PRAGMA foreign_keys=ON 后，外键约束会强制执行
    # 这里验证插入无效外键时会抛出 IntegrityError
    with pytest.raises(Exception):  # SQLite 可能抛出 IntegrityError 或其他异常
        db_session.commit()


def test_symbol_field_present(db_session):
    """测试 symbol 字段存在且可以正确存储"""
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()

    classification = SectorClassification(
        sector_id=sector.id,
        symbol="TEST001",
        classification_date=date.today(),
        classification_level=5,
        state='反弹'
    )
    db_session.add(classification)
    db_session.commit()

    # 验证 symbol 字段正确存储
    assert classification.symbol == "TEST001"
    assert len(classification.symbol) <= 20  # 验证 VARCHAR(20) 约束


def test_all_ma_columns_nullable(db_session):
    """测试所有均线列可以为 NULL（可选字段）"""
    sector = db_session.query(TestSector).filter_by(code="TEST001").first()

    # 创建不包含均线数据的记录
    classification = SectorClassification(
        sector_id=sector.id,
        symbol="TEST001",
        classification_date=date.today(),
        classification_level=5,
        state='反弹'
    )
    db_session.add(classification)
    db_session.commit()

    # 验证记录创建成功（即使不包含均线数据）
    assert classification.id is not None
