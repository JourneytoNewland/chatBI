-- ChatBI 数据库初始化Schema
-- 基于星型模式（Star Schema）设计
-- 维度表（Dimension Tables）+ 事实表（Fact Tables）

-- ============================================
-- Dimension Tables (维度表)
-- ============================================

-- 1. 时间维度表
CREATE TABLE IF NOT EXISTS dim_date (
    date_id DATE PRIMARY KEY,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    week INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    is_weekend BOOLEAN DEFAULT FALSE,
    month_name VARCHAR(10),
    quarter_name VARCHAR(10)
);

-- 2. 地区维度表
CREATE TABLE IF NOT EXISTS dim_region (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(50) UNIQUE NOT NULL,
    country VARCHAR(50) DEFAULT '中国',
    tier INT DEFAULT 2
);

-- 3. 品类维度表
CREATE TABLE IF NOT EXISTS dim_category (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    parent_category_id INT REFERENCES dim_category(category_id),
    level INT DEFAULT 1,
    description TEXT
);

-- 4. 渠道维度表
CREATE TABLE IF NOT EXISTS dim_channel (
    channel_id SERIAL PRIMARY KEY,
    channel_name VARCHAR(50) UNIQUE NOT NULL,
    channel_type VARCHAR(20)
);

-- 5. 用户等级维度表
CREATE TABLE IF NOT EXISTS dim_user_level (
    level_id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) UNIQUE NOT NULL,
    min_score INT,
    max_score INT
);

-- ============================================
-- Fact Tables (事实表)
-- ============================================

-- 1. 订单事实表（GMV、订单量、客单价等）
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id BIGINT PRIMARY KEY,
    date_id DATE REFERENCES dim_date(date_id),
    region_id INT REFERENCES dim_region(region_id),
    category_id INT REFERENCES dim_category(category_id),
    channel_id INT REFERENCES dim_channel(channel_id),
    user_level_id INT REFERENCES dim_user_level(level_id),

    -- 度量字段
    order_amount DECIMAL(12, 2) NOT NULL,
    quantity INT DEFAULT 1,
    is_paid BOOLEAN DEFAULT FALSE,
    is_refunded BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_region ON fact_orders(region_id);
CREATE INDEX IF NOT EXISTS idx_fact_orders_category ON fact_orders(category_id);

-- 2. 用户活动事实表（DAU、MAU、留存率等）
CREATE TABLE IF NOT EXISTS fact_user_activity (
    activity_id BIGINT PRIMARY KEY,
    date_id DATE REFERENCES dim_date(date_id),
    region_id INT REFERENCES dim_region(region_id),
    channel_id INT REFERENCES dim_channel(channel_id),
    user_level_id INT REFERENCES dim_user_level(level_id),

    user_id BIGINT NOT NULL,
    is_new_user BOOLEAN DEFAULT FALSE,

    activity_count INT DEFAULT 1,
    session_duration_seconds INT,
    page_views INT DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_user_activity_date ON fact_user_activity(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_user_activity_user ON fact_user_activity(user_id);

-- 3. 流量事实表（转化率、加购率、支付率）
CREATE TABLE IF NOT EXISTS fact_traffic (
    traffic_id BIGINT PRIMARY KEY,
    date_id DATE REFERENCES dim_date(date_id),
    region_id INT REFERENCES dim_region(region_id),
    category_id INT REFERENCES dim_category(category_id),
    channel_id INT REFERENCES dim_channel(channel_id),

    visitors INT DEFAULT 0,
    visits INT DEFAULT 0,
    page_views INT DEFAULT 0,
    unique_visitors INT DEFAULT 0,

    cart_additions INT DEFAULT 0,
    orders INT DEFAULT 0,
    paid_orders INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_traffic_date ON fact_traffic(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_channel ON fact_traffic(channel_id);

-- 4. 营收事实表（ARPU、LTV）
CREATE TABLE IF NOT EXISTS fact_revenue (
    revenue_id BIGINT PRIMARY KEY,
    date_id DATE REFERENCES dim_date(date_id),
    region_id INT REFERENCES dim_region(region_id),
    channel_id INT REFERENCES dim_channel(channel_id),
    user_level_id INT REFERENCES dim_user_level(level_id),

    revenue DECIMAL(12, 2) NOT NULL,
    cost DECIMAL(12, 2) DEFAULT 0,
    profit DECIMAL(12, 2) GENERATED ALWAYS AS (revenue - cost) STORED,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_revenue_date ON fact_revenue(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_revenue_region ON fact_revenue(region_id);

-- 5. 财务事实表（营收、利润、利润率）
CREATE TABLE IF NOT EXISTS fact_finance (
    finance_id BIGINT PRIMARY KEY,
    date_id DATE REFERENCES dim_date(date_id),
    region_id INT REFERENCES dim_region(region_id),
    business_line VARCHAR(50),
    product_name VARCHAR(100),

    revenue DECIMAL(12, 2) NOT NULL,
    cost DECIMAL(12, 2) NOT NULL,
    profit DECIMAL(12, 2) GENERATED ALWAYS AS (revenue - cost) STORED,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_finance_date ON fact_finance(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_finance_business_line ON fact_finance(business_line);

-- ============================================
-- 初始化维度数据
-- ============================================

-- 初始化地区数据
INSERT INTO dim_region (region_name, country, tier) VALUES
    ('华东', '中国', 1),
    ('华南', '中国', 1),
    ('华北', '中国', 1),
    ('西南', '中国', 2),
    ('东北', '中国', 2)
ON CONFLICT (region_name) DO NOTHING;

-- 初始化品类数据
INSERT INTO dim_category (category_name, parent_category_id, level, description) VALUES
    ('电子产品', NULL, 1, '数码产品类'),
    ('手机', (SELECT category_id FROM dim_category WHERE category_name = '电子产品'), 2, '智能手机'),
    ('电脑', (SELECT category_id FROM dim_category WHERE category_name = '电子产品'), 2, '笔记本电脑'),
    ('服装', NULL, 1, '服装鞋帽'),
    ('男装', (SELECT category_id FROM dim_category WHERE category_name = '服装'), 2, '男士服装'),
    ('女装', (SELECT category_id FROM dim_category WHERE category_name = '服装'), 2, '女士服装')
ON CONFLICT (category_name) DO NOTHING;

-- 初始化渠道数据
INSERT INTO dim_channel (channel_name, channel_type) VALUES
    ('APP', 'organic'),
    ('小程序', 'organic'),
    ('H5', 'direct'),
    ('PC', 'direct')
ON CONFLICT (channel_name) DO NOTHING;

-- 初始化用户等级数据
INSERT INTO dim_user_level (level_name, min_score, max_score) VALUES
    ('普通', 0, 100),
    ('白银', 101, 500),
    ('黄金', 501, 1000),
    ('钻石', 1001, 99999)
ON CONFLICT (level_name) DO NOTHING;

-- 初始化时间维度（生成未来1年）
-- 注意：这里只生成示例，实际应用中应该生成完整的历史数据
INSERT INTO dim_date (date_id, year, quarter, month, week, day, day_of_week, is_weekend, month_name, quarter_name)
SELECT
    current_date + i AS date_id,
    EXTRACT(YEAR FROM current_date + i) AS year,
    EXTRACT(QUARTER FROM current_date + i) AS quarter,
    EXTRACT(MONTH FROM current_date + i) AS month,
    EXTRACT(WEEK FROM current_date + i) AS week,
    EXTRACT(DAY FROM current_date + i) AS day,
    EXTRACT(DOW FROM current_date + i) AS day_of_week,
    EXTRACT(DOW FROM current_date + i) IN (0, 6) AS is_weekend,
    TO_CHAR(current_date + i, 'YYYY-MM') AS month_name,
    TO_CHAR(current_date + i, 'YYYY"Q"Q') AS quarter_name
FROM (SELECT CURRENT_DATE AS current_date) AS dates
CROSS JOIN generate_series(0, 364) AS i
ON CONFLICT (date_id) DO NOTHING;
