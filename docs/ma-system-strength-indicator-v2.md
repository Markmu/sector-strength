# 基于均线系统的强度指标设计（简化版）

## 一、设计理念

**聚焦核心，简单有效**

强度计算基于均线系统的两个核心维度：
1. **价格位置**：当前价格相对于各周期均线的位置
2. **均线排列**：各条均线之间的排列关系（多头/空头）

## 二、均线系统设计

### 2.1 均线周期配置

使用8条均线覆盖短期到长期的所有时间维度：

| 均线 | 周期 | 说明 | 价格位置权重 | 排列权重 |
|------|------|------|--------------|----------|
| MA5 | 5日 | 超短期趋势 | 15% | ✓ |
| MA10 | 10日 | 短期趋势 | 15% | ✓ |
| MA20 | 20日 | 短期中期趋势 | 18% | ✓ |
| MA30 | 30日 | 中期趋势 | 15% | ✓ |
| MA60 | 60日 | 中长期趋势 | 15% | ✓ |
| MA90 | 90日 | 长期趋势 | 10% | ✓ |
| MA120 | 120日 | 半年线 | 7% | ✓ |
| MA240 | 240日 | 年线 | 5% | ✓ |

**权重分配逻辑：**
- 中期均线（MA20）权重最高，是关键支撑/阻力位
- 短期均线（MA5、MA10）次之
- 长期均线权重较低，用于确认长期趋势

## 三、综合强度计算

### 3.1 主公式

```
综合强度 = 价格位置得分 + 均线排列得分
```

两个维度各自独立计分（0-100），直接相加得到综合强度（0-200），然后归一化到0-100：

```
最终强度 = (价格位置得分 + 均线排列得分) / 2
```

### 3.2 价格位置得分 (0-100分)

计算当前价格相对于各条均线的位置，加权平均。

#### 价格位置比率计算

```python
价格位置比率 = (当前价格 - 均线值) / 均线值 × 100%
```

#### 价格位置评分函数

```python
def price_position_score(ratio):
    """
    根据价格位置比率计算得分

    评分标准:
        ratio > +5%:  100分 (远高于均线)
        ratio > +3%:  90分
        ratio > +1%:  75分
        ratio > +0.5%: 60分
        ratio ∈ [-0.5%, +0.5%]: 50分 (接近均线)
        ratio < -0.5%: 40分
        ratio < -1%:  25分
        ratio < -3%:  10分
        ratio < -5%:  0分  (远低于均线)
    """
    if ratio > 5:
        return 100
    elif ratio > 3:
        return 90 + (ratio - 3) * 5  # 90-100
    elif ratio > 1:
        return 75 + (ratio - 1) * 7.5  # 75-90
    elif ratio > 0.5:
        return 60 + (ratio - 0.5) * 30  # 60-75
    elif ratio > -0.5:
        return 50
    elif ratio > -1:
        return 40 + (ratio + 1) * 20  # 40-50
    elif ratio > -3:
        return 25 + (ratio + 3) * 7.5  # 25-40
    elif ratio > -5:
        return 10 + (ratio + 5) * 7.5  # 10-25
    else:
        return max(0, (ratio + 5) * 2)  # 0-10
```

#### 加权平均价格位置得分

```python
def calculate_price_position_score(price, ma_values):
    """
    计算加权平均价格位置得分

    权重分配:
        MA5: 15%, MA10: 15%, MA20: 18%, MA30: 15%,
        MA60: 15%, MA90: 10%, MA120: 7%, MA240: 5%
    """
    weights = {
        5: 0.15, 10: 0.15, 20: 0.18, 30: 0.15,
        60: 0.15, 90: 0.10, 120: 0.07, 240: 0.05
    }

    total_score = 0
    total_weight = 0

    for period, weight in weights.items():
        if period in ma_values:
            ma_value = ma_values[period]
            ratio = (price - ma_value) / ma_value * 100
            score = price_position_score(ratio)
            total_score += score * weight
            total_weight += weight

    return total_score / total_weight if total_weight > 0 else 50
```

### 3.3 均线排列得分 (0-100分)

计算各条均线之间的排列关系，评估多头/空头排列的完整度。

#### 排列状态检测

```python
def calculate_ma_alignment_score(price, ma_values):
    """
    计算均线排列得分

    检查项目:
        1. 价格与MA5的关系
        2. MA5与MA10的关系
        3. MA10与MA20的关系
        4. MA20与MA30的关系
        5. MA30与MA60的关系
        6. MA60与MA90的关系
        7. MA90与MA120的关系
        8. MA120与MA240的关系

    共8个检查项，每项符合多头排列得1分
    """
    checks = []

    # 价格 > MA5
    if 5 in ma_values:
        checks.append(1 if price > ma_values[5] else 0)

    # MA5 > MA10 > MA20 > MA30 > MA60 > MA90 > MA120 > MA240
    periods = [5, 10, 20, 30, 60, 90, 120, 240]
    for i in range(len(periods) - 1):
        short = periods[i]
        long = periods[i + 1]
        if short in ma_values and long in ma_values:
            checks.append(1 if ma_values[short] > ma_values[long] else 0)

    bull_count = sum(checks)
    total = len(checks)

    # 完美多头: 8/8 → 100分
    # 强势多头: 6-7/8 → 80-90分
    # 偏多头: 4-5/8 → 60-70分
    # 中性: 3-4/8 → 40-50分
    # 偏空头: 1-2/8 → 20-30分
    # 完美空头: 0/8 → 0分

    if bull_count == total:
        return 100, "perfect_bull"
    elif bull_count >= total * 0.75:
        return 80 + (bull_count - total * 0.75) * 10, "strong_bull"
    elif bull_count >= total * 0.5:
        return 60 + (bull_count - total * 0.5) * 10, "bull"
    elif bull_count >= total * 0.25:
        return 40 + (bull_count - total * 0.25) * 10, "neutral"
    else:
        return bull_count * 10, "bear"
```

### 3.4 综合强度计算

```python
def calculate_composite_strength(price, ma_values):
    """
    计算综合强度得分

    公式: (价格位置得分 + 均线排列得分) / 2
    """
    # 1. 计算价格位置得分
    price_score = calculate_price_position_score(price, ma_values)

    # 2. 计算均线排列得分
    alignment_score, alignment_state = calculate_ma_alignment_score(price, ma_values)

    # 3. 综合得分
    composite = (price_score + alignment_score) / 2

    return {
        'composite_score': round(composite, 2),
        'price_position_score': round(price_score, 2),
        'ma_alignment_score': round(alignment_score, 2),
        'ma_alignment_state': alignment_state
    }
```

## 四、强度等级定义

| 等级 | 得分范围 | 中文 | 特征描述 |
|------|----------|------|----------|
| S+ | 90-100 | 极强 | 价格远高于所有均线，完美多头排列 |
| S | 80-89 | 很强 | 价格高于大部分均线，强势多头 |
| A+ | 70-79 | 强 | 价格高于关键均线，多头排列 |
| A | 60-69 | 偏强 | 价格高于中期均线 |
| B+ | 50-59 | 中性偏强 | 价格在中期均线附近，略偏多 |
| B | 40-49 | 中性 | 价格在均线密集区 |
| C+ | 30-39 | 中性偏弱 | 价格低于中期均线，略偏空 |
| C | 20-29 | 偏弱 | 价格低于关键均线 |
| D+ | 10-19 | 弱 | 价格低于大部分均线，空头排列 |
| D | 0-9 | 很弱 | 价格远低于所有均线，完美空头 |

## 五、细分指标

### 5.1 短期强度

基于MA5、MA10、MA20的价格位置：

```python
短期强度 = 价格相对MA5得分 × 35% +
           价格相对MA10得分 × 35% +
           价格相对MA20得分 × 30%
```

### 5.2 中期强度

基于MA30、MA60的价格位置：

```python
中期强度 = 价格相对MA30得分 × 50% +
           价格相对MA60得分 × 50%
```

### 5.3 长期强度

基于MA90、MA120、MA240的价格位置：

```python
长期强度 = 价格相对MA90得分 × 40% +
           价格相对MA120得分 × 30% +
           价格相对MA240得分 × 30%
```

## 六、数据表结构（Alembic 迁移）

### 6.1 强度得分表优化设计

**设计原则：**
- 通用支持个股和板块
- 移除个股特有字段（ma5_score, volume_score, momentum_score 等）
- 字段对所有实体类型通用
- 通过 Alembic 生成迁移脚本

**优化后的 strength_scores 表结构：**

```sql
-- strength_scores 表（优化后）
CREATE TABLE strength_scores (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,

    -- 实体标识（通用字段，支持股票和板块）
    entity_type VARCHAR(10) NOT NULL,                 -- 'stock' or 'sector'
    entity_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,                      -- 股票代码或板块代码

    -- 时间和周期
    date DATE NOT NULL,
    period VARCHAR(10) NOT NULL,                      -- 'all', '5d', '10d', '20d', etc.

    -- ========== 核心得分字段（通用） ==========
    -- 综合强度得分
    score NUMERIC(10,2) NOT NULL,                     -- 综合强度得分 (0-100)

    -- 两大维度得分
    price_position_score NUMERIC(10,2),               -- 价格位置得分 (0-100)
    ma_alignment_score NUMERIC(10,2),                 -- 均线排列得分 (0-100)
    ma_alignment_state VARCHAR(20),                   -- 排列状态

    -- 短中长期强度
    short_term_score NUMERIC(10,2),                   -- 短期强度 (MA5/10/20)
    medium_term_score NUMERIC(10,2),                  -- 中期强度 (MA30/60)
    long_term_score NUMERIC(10,2),                    -- 长期强度 (MA90/120/240)

    -- ========== 均线数据（通用） ==========
    current_price NUMERIC(10,2),                      -- 当前价格/指数
    ma5 NUMERIC(10,2),
    ma10 NUMERIC(10,2),
    ma20 NUMERIC(10,2),
    ma30 NUMERIC(10,2),
    ma60 NUMERIC(10,2),
    ma90 NUMERIC(10,2),
    ma120 NUMERIC(10,2),
    ma240 NUMERIC(10,2),

    -- 价格相对均线位置（百分比）
    price_above_ma5 NUMERIC(5,2),
    price_above_ma10 NUMERIC(5,2),
    price_above_ma20 NUMERIC(5,2),
    price_above_ma30 NUMERIC(5,2),
    price_above_ma60 NUMERIC(5,2),
    price_above_ma90 NUMERIC(5,2),
    price_above_ma120 NUMERIC(5,2),
    price_above_ma240 NUMERIC(5,2),

    -- ========== 排名和变化 ==========
    rank INTEGER,                                     -- 市场排名
    change_rate_1d NUMERIC(5,2),                      -- 1日得分变化率

    -- ========== 等级和状态 ==========
    strength_grade VARCHAR(3),                         -- S+/S/A+/A/B+/B/C+/C/D+/D

    -- ========== 时间戳 ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ========== 约束 ==========
    CONSTRAINT chk_score_range CHECK (score >= 0 AND score <= 100),
    CONSTRAINT chk_period_values CHECK (period IN ('all', '5d', '10d', '20d', '30d', '60d', '90d', '120d', '240d')),
    CONSTRAINT chk_entity_type CHECK (entity_type IN ('stock', 'sector')),

    -- ========== 唯一约束 ==========
    UNIQUE(entity_type, entity_id, date, period)
);
```

### 6.2 索引设计

```sql
-- 主查询索引
CREATE INDEX idx_strength_scores_symbol_date
ON strength_scores(symbol, date DESC, period);

CREATE INDEX idx_strength_scores_entity_date
ON strength_scores(entity_type, entity_id, date DESC);

CREATE INDEX idx_strength_scores_date_period
ON strength_scores(date DESC, period);

-- 排名查询索引
CREATE INDEX idx_strength_scores_score_desc
ON strength_scores(score DESC, date DESC)
WHERE period = 'all';

-- 等级筛选索引
CREATE INDEX idx_strength_scores_grade_date
ON strength_scores(strength_grade, date DESC)
WHERE period = 'all';

-- 排列状态索引
CREATE INDEX idx_strength_scores_state_date
ON strength_scores(ma_alignment_state, date DESC)
WHERE period = 'all';

-- 覆盖索引（用于常见查询）
CREATE INDEX idx_strength_scores_cover
ON strength_scores(entity_type, date, period, score, strength_grade, rank)
INCLUDE (symbol, price_position_score, ma_alignment_score);
```

### 6.3 通过 Alembic 生成迁移脚本

**步骤说明：**

#### 1. 更新 SQLAlchemy 模型

首先更新 `server/src/models/strength_score.py` 中的 `StrengthScore` 模型：

```python
# server/src/models/strength_score.py

class StrengthScore(Base):
    """强度得分模型 - 优化后"""
    __tablename__ = "strength_scores"

    id = Column(Integer, primary_key=True, index=True)

    # 实体标识
    entity_type = Column(String(10), nullable=False, index=True)  # 'stock' or 'sector'
    entity_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)

    # 时间和周期
    date = Column(Date, nullable=False, index=True)
    period = Column(String(10), nullable=False, index=True)

    # 核心得分
    score = Column(Numeric(precision=10, scale=2), nullable=False)
    price_position_score = Column(Numeric(precision=10, scale=2))
    ma_alignment_score = Column(Numeric(precision=10, scale=2))
    ma_alignment_state = Column(String(20))

    # 短中长期强度
    short_term_score = Column(Numeric(precision=10, scale=2))
    medium_term_score = Column(Numeric(precision=10, scale=2))
    long_term_score = Column(Numeric(precision=10, scale=2))

    # 均线数据
    current_price = Column(Numeric(precision=10, scale=2))
    ma5 = Column(Numeric(precision=10, scale=2))
    ma10 = Column(Numeric(precision=10, scale=2))
    ma20 = Column(Numeric(precision=10, scale=2))
    ma30 = Column(Numeric(precision=10, scale=2))
    ma60 = Column(Numeric(precision=10, scale=2))
    ma90 = Column(Numeric(precision=10, scale=2))
    ma120 = Column(Numeric(precision=10, scale=2))
    ma240 = Column(Numeric(precision=10, scale=2))

    # 价格相对均线位置
    price_above_ma5 = Column(Numeric(precision=5, scale=2))
    price_above_ma10 = Column(Numeric(precision=5, scale=2))
    price_above_ma20 = Column(Numeric(precision=5, scale=2))
    price_above_ma30 = Column(Numeric(precision=5, scale=2))
    price_above_ma60 = Column(Numeric(precision=5, scale=2))
    price_above_ma90 = Column(Numeric(precision=5, scale=2))
    price_above_ma120 = Column(Numeric(precision=5, scale=2))
    price_above_ma240 = Column(Numeric(precision=5, scale=2))

    # 排名和变化
    rank = Column(Integer)
    change_rate_1d = Column(Numeric(precision=5, scale=2))
    strength_grade = Column(String(3))

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 表级约束
    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='chk_score_range'),
        CheckConstraint("period IN ('all', '5d', '10d', '20d', '30d', '60d', '90d', '120d', '240d')",
                       name='chk_period_values'),
        CheckConstraint("entity_type IN ('stock', 'sector')", name='chk_entity_type'),
        Index('idx_strength_scores_symbol_date', 'symbol', sa.text('date DESC'), 'period'),
        Index('idx_strength_scores_score_desc', sa.text('score DESC'), sa.text('date DESC')),
        UniqueConstraint('entity_type', 'entity_id', 'date', 'period', name='uq_strength_scores_entity_date_period'),
    )
```

#### 2. 生成 Alembic 迁移脚本

```bash
# 进入项目目录
cd /path/to/project

# 生成迁移脚本（自动检测模型变化）
alembic revision --autogenerate -m "optimize strength_scores table"

# 生成的文件位于：alembic/versions/YYYYMMDDHHMMSS_optimize_strength_scores_table.py
```

#### 3. 检查生成的迁移脚本

查看生成的文件，确认以下内容正确：

```python
# alembic/versions/YYYYMMDDHHMMSS_optimize_strength_scores_table.py

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('strength_scores', sa.Column('symbol', sa.String(length=20), nullable=True))
    op.add_column('strength_scores', sa.Column('price_position_score', sa.Numeric(precision=10, scale=2), nullable=True))
    # ... 其他新字段

    op.create_check_constraint('chk_score_range', 'strength_scores', 'score >= 0 AND score <= 100')
    # ... 其他约束和索引
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('chk_score_range', 'strength_scores')
    # ... 删除约束、索引和字段
    # ### end Alembic commands ###
```

#### 4. 手动补充数据迁移逻辑

自动生成的脚本可能需要补充数据迁移逻辑：

```python
def upgrade():
    # ... 自动生成的添加字段代码 ...

    # ============ 手动添加：数据迁移 ============
    # 填充 symbol 字段
    from sqlalchemy.sql import table, column
    from sqlalchemy import select

    # 连接到数据库
    connection = op.get_bind()

    # 从 stocks 表获取 symbol
    connection.execute(
        sa.text("""
            UPDATE strength_scores s
            SET symbol = (SELECT symbol FROM stocks WHERE id = s.entity_id)
            WHERE s.entity_type = 'stock' AND symbol IS NULL
        """)
    )

    # 从 sectors 表获取 code 作为 symbol
    connection.execute(
        sa.text("""
            UPDATE strength_scores s
            SET symbol = (SELECT code FROM sectors WHERE id = s.entity_id)
            WHERE s.entity_type = 'sector' AND symbol IS NULL
        """)
    )

    # 设置 symbol 为 NOT NULL
    op.alter_column('strength_scores', 'symbol', nullable=False)
    # ============ 数据迁移结束 ============
```

#### 5. 执行迁移

```bash
# 查看待执行的迁移
alembic current

# 执行迁移
alembic upgrade head

# 验证迁移成功
alembic current
```

### 6.4 数据存储策略

**period 字段使用规范：**

| period 值 | 说明 | 适用实体 |
|-----------|------|----------|
| `'all'` | **新方法**：综合8条均线的强度得分 | stock, sector |
| `'5d'`, `'10d'` 等 | **保留**：单周期强度得分（旧数据） | stock, sector |

**示例数据：**

```sql
-- 个股综合强度（新方法）
INSERT INTO strength_scores (
    entity_type, entity_id, symbol, date, period,
    score, price_position_score, ma_alignment_score,
    ma_alignment_state, short_term_score, medium_term_score, long_term_score,
    current_price, ma5, ma10, ma20, ma30, ma60, ma90, ma120, ma240,
    price_above_ma5, price_above_ma10, price_above_ma20, price_above_ma30,
    price_above_ma60, price_above_ma90, price_above_ma120, price_above_ma240,
    strength_grade
) VALUES (
    'stock', 123, '600519', '2024-12-28', 'all',
    78.5, 82.3, 75.0, 'strong_bull', 75.2, 78.5, 68.3,
    1850.0, 1835.2, 1825.8, 1810.5, 1798.2, 1775.0, 1752.0, 1728.0, 1680.0,
    0.81, 1.33, 2.18, 2.79, 4.23, 5.65, 7.12, 10.12,
    'A'
);

-- 板块综合强度（新方法）
INSERT INTO strength_scores (
    entity_type, entity_id, symbol, date, period,
    score, price_position_score, ma_alignment_score,
    ma_alignment_state, short_term_score, medium_term_score, long_term_score,
    current_price, ma5, ma10, ma20, ma30, ma60, ma90, ma120, ma240,
    price_above_ma5, price_above_ma10, price_above_ma20, price_above_ma30,
    price_above_ma60, price_above_ma90, price_above_ma120, price_above_ma240,
    strength_grade
) VALUES (
    'sector', 45, 'BK0426', '2024-12-28', 'all',
    72.5, 70.0, 75.0, 'strong_bull', 68.5, 72.0, 70.0,
    4850.0, 4830.0, 4810.0, 4780.0, 4750.0, 4720.0, 4680.0, 4620.0, 4500.0,
    0.41, 0.83, 1.45, 2.05, 2.75, 3.63, 5.02, 7.78,
    'A'
);
```

### 6.5 使用现有均线数据表

**注意**：均线历史数据使用现有的 `moving_average_data` 表，该表已存储各周期均线数据。

**现有表结构：**
```sql
-- moving_average_data 表（已存在）
CREATE TABLE moving_average_data (
    id INTEGER PRIMARY KEY,
    entity_type VARCHAR(10) NOT NULL,                 -- 'stock' or 'sector'
    entity_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    period VARCHAR(10) NOT NULL,                      -- '5d', '10d', '20d', etc.
    ma_value NUMERIC(10,2),                           -- 均线值
    price_ratio NUMERIC(10,4),                        -- 价格与均线的比率
    trend NUMERIC(5,2),                              -- 趋势方向
    created_at TIMESTAMP
);
```

**数据获取方式：**
```python
# 查询某股票某日所有周期的均线数据
def get_ma_values(symbol: str, date: date) -> Dict[int, float]:
    """从 moving_average_data 表获取均线值"""
    records = db.query(MovingAverageData).filter(
        MovingAverageData.symbol == symbol,
        MovingAverageData.date == date,
        MovingAverageData.entity_type == 'stock'
    ).all()

    ma_values = {}
    for record in records:
        period = int(record.period.rstrip('d'))  # '5d' -> 5
        ma_values[period] = float(record.ma_value)

    return ma_values
```

## 七、计算示例

### 示例1：强势股票

```
当前价格: 100元
MA5: 95, MA10: 93, MA20: 90, MA30: 88, MA60: 85, MA90: 82, MA120: 80, MA240: 75

价格位置得分:
  MA5: (100-95)/95 = +5.3% → 100分
  MA10: (100-93)/93 = +7.5% → 100分
  MA20: (100-90)/90 = +11.1% → 100分
  ...
  加权平均 ≈ 95分

均线排列得分:
  价格>MA5 ✓, MA5>MA10 ✓, MA10>MA20 ✓, ...
  8/8 符合 → 100分

综合强度 = (95 + 100) / 2 = 97.5分 → S+
```

### 示例2：中性股票

```
当前价格: 100元
MA5: 102, MA10: 100, MA20: 98, MA30: 95, MA60: 92, MA90: 90, MA120: 88, MA240: 85

价格位置得分:
  MA5: (100-102)/102 = -2.0% → 25分
  MA10: (100-100)/100 = 0% → 50分
  MA20: (100-98)/98 = +2.0% → 75分
  ...
  加权平均 ≈ 50分

均线排列得分:
  价格>MA5 ✗, MA5>MA10 ✓, MA10>MA20 ✓, ...
  5/8 符合 → 50分

综合强度 = (50 + 50) / 2 = 50分 → B+
```

## 七、API响应示例

### 7.1 个股强度响应

```json
{
  "stock_id": 123,
  "symbol": "600519",
  "stock_name": "贵州茅台",
  "date": "2024-12-28",
  "composite_score": 78.5,
  "strength_grade": "A",
  "scores": {
    "price_position": 82.3,
    "ma_alignment": 75.0
  },
  "ma_alignment_state": "strong_bull",
  "term_scores": {
    "short_term": 75.2,
    "medium_term": 78.5,
    "long_term": 68.3
  },
  "ma_data": {
    "current_price": 1850.0,
    "ma5": 1835.2,
    "ma10": 1825.8,
    "ma20": 1810.5,
    "ma30": 1798.2,
    "ma60": 1775.0,
    "ma90": 1752.0,
    "ma120": 1728.0,
    "ma240": 1680.0
  },
  "price_positions": {
    "above_ma5": 0.81,
    "above_ma10": 1.33,
    "above_ma20": 2.18,
    "above_ma30": 2.79,
    "above_ma60": 4.23,
    "above_ma90": 5.65,
    "above_ma120": 7.12,
    "above_ma240": 10.12
  },
  "rank_in_market": 156
}
```

### 7.2 历史曲线响应

```json
{
  "symbol": "600519",
  "stock_name": "贵州茅台",
  "start_date": "2024-12-01",
  "end_date": "2024-12-28",
  "data_points": [
    {
      "date": "2024-12-01",
      "composite_score": 72.5,
      "strength_grade": "A",
      "price_position_score": 70.0,
      "ma_alignment_score": 75.0,
      "ma_alignment_state": "bull",
      "short_term_score": 68.5,
      "medium_term_score": 72.0,
      "long_term_score": 68.0,
      "current_price": 1820.0,
      "ma20": 1805.0
    },
    {
      "date": "2024-12-02",
      "composite_score": 74.1,
      "strength_grade": "A",
      "price_position_score": 72.5,
      "ma_alignment_score": 75.7,
      "ma_alignment_state": "bull",
      "short_term_score": 70.2,
      "medium_term_score": 73.5,
      "long_term_score": 68.5,
      "current_price": 1825.0,
      "ma20": 1808.0
    }
    // ... 更多数据点
  ]
}
```

## 八、优势总结

1. **简单直观**: 只有两个维度，易于理解和解释
2. **计算高效**: 不需要复杂的技术指标计算
3. **数据需求低**: 只需要历史价格数据
4. **趋势明确**: 均线排列清晰反映趋势方向
5. **可扩展**: 未来可轻松添加其他维度或板块功能
