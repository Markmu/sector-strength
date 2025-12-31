# 数据库表结构设计（基于均线系统）

## 一、设计原则

1. **精简高效**: 专注于均线系统的数据存储
2. **查询优化**: 针对排名查询和历史曲线优化
3. **可扩展性**: 预留扩展字段，支持未来添加其他指标

## 二、核心表结构

### 2.1 个股强度快照表 (stock_strength_snapshots)

存储个股每日的强度数据快照（主表）

```sql
CREATE TABLE stock_strength_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,

    -- 综合强度
    composite_score NUMERIC(10,2) NOT NULL,           -- 综合强度得分 (0-100)
    strength_grade VARCHAR(3),                         -- 强度等级 (S+/S/A+/A/B+/B/C+/C/D+/D)

    -- 三大维度得分
    price_position_score NUMERIC(10,2),               -- 价格位置得分 (0-100)
    ma_alignment_score NUMERIC(10,2),                 -- 均线排列得分 (0-100)
    ma_slope_score NUMERIC(10,2),                     -- 均线斜率得分 (0-100)

    -- 短中长期强度
    short_term_score NUMERIC(10,2),                   -- 短期强度 (MA5/10/20)
    medium_term_score NUMERIC(10,2),                  -- 中期强度 (MA30/60)
    long_term_score NUMERIC(10,2),                    -- 长期强度 (MA90/120/240)
    trend_strength_score NUMERIC(10,2),               -- 趋势强度

    -- 当前价格和均线值
    current_price NUMERIC(10,2),
    ma5 NUMERIC(10,2),
    ma10 NUMERIC(10,2),
    ma20 NUMERIC(10,2),
    ma30 NUMERIC(10,2),
    ma60 NUMERIC(10,2),
    ma90 NUMERIC(10,2),
    ma120 NUMERIC(10,2),
    ma240 NUMERIC(10,2),

    -- 价格相对各均线的位置（百分比）
    price_above_ma5 NUMERIC(5,2),                     -- 价格相对MA5位置 (%)
    price_above_ma10 NUMERIC(5,2),
    price_above_ma20 NUMERIC(5,2),
    price_above_ma30 NUMERIC(5,2),
    price_above_ma60 NUMERIC(5,2),
    price_above_ma90 NUMERIC(5,2),
    price_above_ma120 NUMERIC(5,2),
    price_above_ma240 NUMERIC(5,2),

    -- 均线斜率（百分比，最近5日变化）
    ma5_slope NUMERIC(5,2),
    ma10_slope NUMERIC(5,2),
    ma20_slope NUMERIC(5,2),
    ma30_slope NUMERIC(5,2),
    ma60_slope NUMERIC(5,2),
    ma90_slope NUMERIC(5,2),
    ma120_slope NUMERIC(5,2),
    ma240_slope NUMERIC(5,2),

    -- 均线排列状态
    ma_alignment_state VARCHAR(20),                   -- perfect_bull/bull/neutral/bear/perfect_bear

    -- 辅助指标
    ma_divergence NUMERIC(5,2),                       -- 均线发散度

    -- 排名和变化
    rank_in_market INTEGER,                           -- 市场排名
    rank_change INTEGER,                              -- 排名变化
    score_change_1d NUMERIC(5,2),                     -- 得分1日变化
    score_change_5d NUMERIC(5,2),                     -- 得分5日变化

    -- 金叉死叉信号
    golden_cross VARCHAR(100),                        -- 金叉列表 (JSON)
    death_cross VARCHAR(100),                         -- 死叉列表 (JSON)

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT chk_composite_score_range CHECK (composite_score >= 0 AND composite_score <= 100),
    CONSTRAINT chk_price_position_score_range CHECK (price_position_score >= 0 AND price_position_score <= 100),
    CONSTRAINT chk_ma_alignment_score_range CHECK (ma_alignment_score >= 0 AND ma_alignment_score <= 100),
    CONSTRAINT chk_ma_slope_score_range CHECK (ma_slope_score >= 0 AND ma_slope_score <= 100),

    -- 唯一约束
    UNIQUE(stock_id, date)
);

-- 索引
CREATE INDEX idx_stock_snapshot_stock_date ON stock_strength_snapshots(stock_id, date DESC);
CREATE INDEX idx_stock_snapshot_date ON stock_strength_snapshots(date DESC);
CREATE INDEX idx_stock_snapshot_composite ON stock_strength_snapshots(composite_score DESC, date DESC);
CREATE INDEX idx_stock_snapshot_grade ON stock_strength_snapshots(strength_grade, date DESC);
CREATE INDEX idx_stock_snapshot_rank ON stock_strength_snapshots(rank_in_market, date DESC);
CREATE INDEX idx_stock_snapshot_ma_state ON stock_strength_snapshots(ma_alignment_state, date DESC);

-- 覆盖索引用于常见查询
CREATE INDEX idx_stock_snapshot_cover ON stock_strength_snapshots(
    stock_id, date DESC,
    composite_score, strength_grade,
    short_term_score, medium_term_score, long_term_score
);
```

### 2.2 均线历史数据表 (stock_ma_history)

存储各周期的均线历史数据，用于计算斜率

```sql
CREATE TABLE stock_ma_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,

    -- 各周期均线值
    ma5 NUMERIC(10,2),
    ma10 NUMERIC(10,2),
    ma20 NUMERIC(10,2),
    ma30 NUMERIC(10,2),
    ma60 NUMERIC(10,2),
    ma90 NUMERIC(10,2),
    ma120 NUMERIC(10,2),
    ma240 NUMERIC(10,2),

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(stock_id, date)
);

-- 索引
CREATE INDEX idx_ma_history_stock_date ON stock_ma_history(stock_id, date DESC);
CREATE INDEX idx_ma_history_date ON stock_ma_history(date DESC);
```

### 2.3 板块强度快照表 (sector_strength_snapshots)

存储板块每日的强度数据

```sql
CREATE TABLE sector_strength_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id INTEGER NOT NULL,
    date DATE NOT NULL,

    -- 综合强度
    composite_score NUMERIC(10,2) NOT NULL,
    strength_grade VARCHAR(3),

    -- 三大维度得分
    price_position_score NUMERIC(10,2),
    ma_alignment_score NUMERIC(10,2),
    ma_slope_score NUMERIC(10,2),

    -- 短中长期强度
    short_term_score NUMERIC(10,2),
    medium_term_score NUMERIC(10,2),
    long_term_score NUMERIC(10,2),
    trend_strength_score NUMERIC(10,2),

    -- 当前价格和均线值
    current_price NUMERIC(10,2),
    ma5 NUMERIC(10,2),
    ma10 NUMERIC(10,2),
    ma20 NUMERIC(10,2),
    ma30 NUMERIC(10,2),
    ma60 NUMERIC(10,2),
    ma90 NUMERIC(10,2),
    ma120 NUMERIC(10,2),
    ma240 NUMERIC(10,2),

    -- 价格相对各均线的位置
    price_above_ma5 NUMERIC(5,2),
    price_above_ma10 NUMERIC(5,2),
    price_above_ma20 NUMERIC(5,2),
    price_above_ma60 NUMERIC(5,2),

    -- 均线排列状态
    ma_alignment_state VARCHAR(20),

    -- 板块特有统计
    stock_count INTEGER,                              -- 成分股数量
    avg_stock_score NUMERIC(10,2),                    -- 成分股平均得分
    weighted_stock_score NUMERIC(10,2),               -- 市值加权得分
    strong_stock_ratio NUMERIC(5,4),                  -- 强势股占比 (得分>60)
    up_stock_ratio NUMERIC(5,4),                      -- 上涨股占比

    -- 排名
    rank_in_market INTEGER,
    rank_change INTEGER,

    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sector_id, date)
);

-- 索引
CREATE INDEX idx_sector_snapshot_sector_date ON sector_strength_snapshots(sector_id, date DESC);
CREATE INDEX idx_sector_snapshot_date ON sector_strength_snapshots(date DESC);
CREATE INDEX idx_sector_snapshot_composite ON sector_strength_snapshots(composite_score DESC, date DESC);
CREATE INDEX idx_sector_snapshot_strong_ratio ON sector_strength_snapshots(strong_stock_ratio DESC, date DESC);
```

### 2.4 板块成分股强度明细表 (sector_stock_strength_details)

存储板块成分股的详细强度数据

```sql
CREATE TABLE sector_stock_strength_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,

    -- 个股强度数据
    composite_score NUMERIC(10,2),
    strength_grade VARCHAR(3),
    current_price NUMERIC(10,2),
    market_cap NUMERIC(18,2),                         -- 个股市值
    weight_in_sector NUMERIC(5,4),                    -- 在板块中的权重 (0-1)

    -- 贡献度
    contribution_to_sector NUMERIC(10,2),             -- 对板块强度的贡献

    -- 状态标记
    is_strong BOOLEAN DEFAULT 0,                      -- 是否强势股 (得分>60)
    is_up_today BOOLEAN DEFAULT 0,                    -- 今日是否上涨

    -- 均线数据
    ma5 NUMERIC(10,2),
    ma20 NUMERIC(10,2),
    ma60 NUMERIC(10,2),
    price_above_ma20 NUMERIC(5,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(sector_id, stock_id, date)
);

-- 索引
CREATE INDEX idx_sector_stock_detail_sector_date ON sector_stock_strength_details(sector_id, date DESC, composite_score DESC);
CREATE INDEX idx_sector_stock_detail_stock_date ON sector_stock_strength_details(stock_id, date DESC);
CREATE INDEX idx_sector_stock_detail_strong ON sector_stock_strength_details(sector_id, date, is_strong);
```

### 2.5 均线交叉信号表 (ma_cross_signals)

记录均线金叉和死叉信号

```sql
CREATE TABLE ma_cross_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    signal_type VARCHAR(10) NOT NULL,                 -- 'golden' or 'death'
    short_ma VARCHAR(10) NOT NULL,                    -- 短期均线 (MA5/MA10/MA20)
    long_ma VARCHAR(10) NOT NULL,                     -- 长期均线 (MA10/MA20/MA30/MA60)
    short_value NUMERIC(10,2),
    long_value NUMERIC(10,2),
    price_at_cross NUMERIC(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_ma_cross_stock_date ON ma_cross_signals(stock_id, date DESC);
CREATE INDEX idx_ma_cross_signal_type ON ma_cross_signals(signal_type, date DESC);
CREATE INDEX idx_ma_cross_date ON ma_cross_signals(date DESC);
```

### 2.6 权重配置表 (weight_configs)

存储用户自定义的权重配置（预留）

```sql
CREATE TABLE weight_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    config_name VARCHAR(50) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,

    -- 权重配置 JSON
    weights_json JSON NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 默认配置
INSERT INTO weight_configs (user_id, config_name, description, is_default, weights_json) VALUES
(NULL, '默认配置', '系统默认的均线权重配置', 1, '{
  "price_position": 0.40,
  "ma_alignment": 0.35,
  "ma_slope": 0.25,
  "ma_weights": {
    "MA5": 0.10,
    "MA10": 0.12,
    "MA20": 0.15,
    "MA30": 0.15,
    "MA60": 0.18,
    "MA90": 0.12,
    "MA120": 0.10,
    "MA240": 0.08
  }
}');
```

## 三、数据视图

### 3.1 个股强度综合视图

```sql
CREATE VIEW v_stock_strength AS
SELECT
    s.id AS stock_id,
    s.symbol,
    s.name,
    ss.date,
    ss.composite_score,
    ss.strength_grade,
    ss.price_position_score,
    ss.ma_alignment_score,
    ss.ma_slope_score,
    ss.short_term_score,
    ss.medium_term_score,
    ss.long_term_score,
    ss.trend_strength_score,
    ss.current_price,
    ss.ma5,
    ss.ma10,
    ss.ma20,
    ss.ma60,
    ss.price_above_ma20,
    ss.ma_alignment_state,
    ss.rank_in_market,
    ss.score_change_1d
FROM stock_strength_snapshots ss
JOIN stocks s ON ss.stock_id = s.id
WHERE ss.date = (SELECT MAX(date) FROM stock_strength_snapshots);
```

### 3.2 板块强度综合视图

```sql
CREATE VIEW v_sector_strength AS
SELECT
    sec.id AS sector_id,
    sec.code,
    sec.name,
    sec.type,
    ss.date,
    ss.composite_score,
    ss.strength_grade,
    ss.short_term_score,
    ss.medium_term_score,
    ss.long_term_score,
    ss.stock_count,
    ss.strong_stock_ratio,
    ss.up_stock_ratio,
    ss.rank_in_market
FROM sector_strength_snapshots ss
JOIN sectors sec ON ss.sector_id = sec.id
WHERE ss.date = (SELECT MAX(date) FROM sector_strength_snapshots);
```

## 四、数据分区建议

对于大规模数据，建议按月分区：

```sql
-- 按月分区示例
CREATE TABLE stock_strength_snapshots_2025_01 PARTITION OF stock_strength_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE stock_strength_snapshots_2025_02 PARTITION OF stock_strength_snapshots
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

## 五、数据迁移

### 5.1 从旧表迁移

如果需要从旧的 `strength_scores` 表迁移数据：

```sql
INSERT INTO stock_strength_snapshots (
    stock_id,
    date,
    composite_score,
    price_position_score,
    ma_alignment_score,
    ma_slope_score,
    created_at
)
SELECT
    entity_id AS stock_id,
    date,
    score AS composite_score,
    score AS price_position_score,  -- 临时使用相同的值
    50 AS ma_alignment_score,       -- 默认值
    50 AS ma_slope_score,           -- 默认值
    created_at
FROM strength_scores
WHERE entity_type = 'stock'
ON CONFLICT(stock_id, date) DO NOTHING;
```

## 六、性能优化建议

### 6.1 定期维护

```sql
-- 定期分析表
ANALYZE stock_strength_snapshots;

-- 定期重建索引
REINDEX TABLE stock_strength_snapshots;

-- 定期清理旧数据（可选）
DELETE FROM stock_strength_snapshots WHERE date < '2020-01-01';
```

### 6.2 查询优化

```sql
-- 使用覆盖索引避免回表
-- 查询最近N天的排名数据
SELECT stock_id, composite_score, strength_grade, rank_in_market
FROM stock_strength_snapshots
WHERE date = '2024-12-28'
ORDER BY composite_score DESC
LIMIT 100;

-- 使用准备语句提高性能
PREPARE get_stock_strength (INT, DATE) AS
SELECT * FROM stock_strength_snapshots
WHERE stock_id = $1 AND date = $2;

EXECUTE get_stock_strength(123, '2024-12-28');
```

### 6.3 缓存策略

- 当日强度数据缓存到 Redis，TTL 5分钟
- 排名数据缓存，TTL 1分钟
- 历史曲线数据缓存，TTL 30分钟

## 七、数据完整性

### 7.1 触发器

```sql
-- 确保得分在0-100范围内
CREATE TRIGGER trg_check_score_range
BEFORE INSERT OR UPDATE ON stock_strength_snapshots
FOR EACH ROW
BEGIN
    IF NEW.composite_score < 0 OR NEW.composite_score > 100 THEN
        SIGNAL('SQLSTATE' '45000', SET MESSAGE_TEXT = '综合得分必须在0-100范围内');
    END IF;
END;
```

### 7.2 自动更新时间戳

```sql
-- 自动更新 updated_at 字段
CREATE TRIGGER trg_update_timestamp
BEFORE UPDATE ON stock_strength_snapshots
FOR EACH ROW
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
END;
```

## 八、备份策略

### 8.1 定期备份

```bash
# 每日全量备份
pg_dump -h localhost -U user -d dbname -F c -b -v -f backup_$(date +%Y%m%d).dump

# 仅备份强度相关表
pg_dump -h localhost -U user -d dbname -t stock_strength_snapshots -t stock_ma_history \
  -t sector_strength_snapshots -f strength_backup_$(date +%Y%m%d).sql
```

### 8.2 数据归档

```sql
-- 归档1年前的数据到归档表
INSERT INTO stock_strength_snapshots_archive
SELECT * FROM stock_strength_snapshots WHERE date < DATE('now', '-1 year');

-- 删除已归档的数据
DELETE FROM stock_strength_snapshots WHERE date < DATE('now', '-1 year');
```
