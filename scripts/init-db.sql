-- 初始化sector_strength数据库

-- 创建枚举类型
CREATE TYPE sector_type AS ENUM ('industry', 'concept');
CREATE TYPE entity_type AS ENUM ('stock', 'sector');

-- 创建板块表
CREATE TABLE sectors (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    type sector_type NOT NULL,
    description TEXT,
    strength_score NUMERIC(10, 4) DEFAULT 0,
    trend_direction NUMERIC(5, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建个股表
CREATE TABLE stocks (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    current_price NUMERIC(10, 2) DEFAULT 0,
    market_cap NUMERIC(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建板块-个股关联表
CREATE TABLE sector_stocks (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    sector_id VARCHAR(36) NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    stock_id VARCHAR(36) NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sector_id, stock_id)
);

-- 创建周期配置表
CREATE TABLE period_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    period VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    days INTEGER NOT NULL,
    weight NUMERIC(5, 2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建日线行情数据表
CREATE TABLE daily_market_data (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type entity_type NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    close NUMERIC(10, 2),
    volume NUMERIC(15, 2),
    turnover NUMERIC(15, 2),
    change NUMERIC(10, 2),
    change_percent NUMERIC(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, date)
);

-- 创建均线数据表
CREATE TABLE moving_average_data (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type entity_type NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    date DATE NOT NULL,
    period VARCHAR(10) NOT NULL,
    ma_value NUMERIC(10, 2),
    price_ratio NUMERIC(10, 4),
    trend NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, date, period)
);

-- 创建索引以提高查询性能
CREATE INDEX idx_sectors_type ON sectors(type);
CREATE INDEX idx_sectors_strength ON sectors(strength_score);
CREATE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_sector_stocks_sector ON sector_stocks(sector_id);
CREATE INDEX idx_sector_stocks_stock ON sector_stocks(stock_id);
CREATE INDEX idx_daily_market_data_entity ON daily_market_data(entity_type, entity_id);
CREATE INDEX idx_daily_market_data_date ON daily_market_data(date);
CREATE INDEX idx_moving_average_data_entity ON moving_average_data(entity_type, entity_id);
CREATE INDEX idx_moving_average_data_date ON moving_average_data(date);

-- 插入默认的周期配置
INSERT INTO period_configs (period, name, days, weight, is_active) VALUES
('5d', '5日', 5, 1.0, TRUE),
('10d', '10日', 10, 1.2, TRUE),
('20d', '20日', 20, 1.5, TRUE),
('30d', '30日', 30, 1.8, TRUE),
('60d', '60日', 60, 2.0, TRUE);
