-- 板块数据源迁移前的人工清空脚本（停机窗口执行）
-- 注意：该脚本会不可逆地清空相关表数据。

TRUNCATE TABLE
    sector_classification,
    strength_scores,
    moving_average_data,
    daily_market_data,
    sector_stocks,
    sectors
RESTART IDENTITY CASCADE;
