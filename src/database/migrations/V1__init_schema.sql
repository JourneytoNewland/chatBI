-- ============================================
-- chatBI 智能问数系统 - PostgreSQL 初始化Schema
-- ============================================
-- 版本: v1.0
-- 创建时间: 2026-02-07
-- 说明: 维度表 + 事实表 + 索引
-- ============================================

-- ============================================
-- 1. 维度表 (Dimension Tables)
-- ============================================

-- 1.1 日期维度表
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,  -- 格式: 20240201
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    week INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 1=周一, 7=周日
    day_name VARCHAR(10) NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_name VARCHAR(50),
    quarter_name VARCHAR(10) GENERATED ALWAYS AS ('Q' || quarter::TEXT) STORED
);

-- 1.2 地区维度表
CREATE TABLE IF NOT EXISTS dim_region (
    region_key SERIAL PRIMARY KEY,
    region_id VARCHAR(50) NOT NULL UNIQUE,
    region_name VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL DEFAULT '中国',
    tier INTEGER NOT NULL,  -- 城市等级: 1=一线, 2=二线, 3=三线
    parent_region_id VARCHAR(50),  -- 上级区域ID
    description TEXT
);

-- 1.3 品类维度表
CREATE TABLE IF NOT EXISTS dim_category (
    category_key SERIAL PRIMARY KEY,
    category_id VARCHAR(50) NOT NULL UNIQUE,
    category_name VARCHAR(100) NOT NULL,
    parent_category_id VARCHAR(50),  -- 父品类ID
    level INTEGER NOT NULL,  -- 层级: 1=一级品类, 2=二级品类
    description TEXT
);

-- 1.4 渠道维度表
CREATE TABLE IF NOT EXISTS dim_channel (
    channel_key SERIAL PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL UNIQUE,
    channel_name VARCHAR(50) NOT NULL,  -- APP, 小程序, H5, PC
    channel_type VARCHAR(20) NOT NULL,  -- mobile, web, miniprogram
    description TEXT
);

-- 1.5 用户等级维度表
CREATE TABLE IF NOT EXISTS dim_user_level (
    level_key SERIAL PRIMARY KEY,
    level_id VARCHAR(50) NOT NULL UNIQUE,
    level_name VARCHAR(50) NOT NULL,  -- 普通, 黄金, 铂金, 钻石
    min_points INTEGER NOT NULL DEFAULT 0,
    max_points INTEGER,
    benefits TEXT
);

-- ============================================
-- 2. 事实表 (Fact Tables)
-- ============================================

-- 2.1 订单事实表 (GMV相关)
CREATE TABLE IF NOT EXISTS fact_orders (
    order_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    category_key INTEGER NOT NULL,
    channel_key INTEGER NOT NULL,
    user_level_key INTEGER NOT NULL,

    -- 度量指标
    order_count BIGINT NOT NULL DEFAULT 0,
    total_order_amount DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 订单总额
    total_discount DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 折扣金额
    gmv DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 成交金额 (GMV)
    average_order_value DECIMAL(18, 2) GENERATED ALWAYS AS (
        CASE WHEN order_count > 0 THEN total_order_amount / order_count ELSE 0 END
    ) STORED,

    -- 元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (region_key) REFERENCES dim_region(region_key),
    FOREIGN KEY (category_key) REFERENCES dim_category(category_key),
    FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key),
    FOREIGN KEY (user_level_key) REFERENCES dim_user_level(level_key)
);

-- 2.2 用户活跃度事实表 (DAU/MAU相关)
CREATE TABLE IF NOT EXISTS fact_user_activity (
    activity_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    channel_key INTEGER NOT NULL,
    user_level_key INTEGER NOT NULL,

    -- 度量指标
    dau BIGINT NOT NULL DEFAULT 0,  -- 日活跃用户数
    mau BIGINT NOT NULL DEFAULT 0,  -- 月活跃用户数
    new_users BIGINT NOT NULL DEFAULT 0,  -- 新增用户
    returning_users BIGINT NOT NULL DEFAULT 0,  -- 回访用户
    session_count BIGINT NOT NULL DEFAULT 0,  -- 会话数
    avg_session_duration DECIMAL(10, 2) NOT NULL DEFAULT 0.00,  -- 平均会话时长(秒)
    page_views BIGINT NOT NULL DEFAULT 0,  -- 页面浏览量

    -- 留存率
    retention_day1 DECIMAL(5, 4) DEFAULT NULL,  -- 次日留存率
    retention_day7 DECIMAL(5, 4) DEFAULT NULL,  -- 7日留存率
    retention_day30 DECIMAL(5, 4) DEFAULT NULL,  -- 30日留存率

    -- 元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (region_key) REFERENCES dim_region(region_key),
    FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key),
    FOREIGN KEY (user_level_key) REFERENCES dim_user_level(level_key)
);

-- 2.3 流量事实表 (转化率相关)
CREATE TABLE IF NOT EXISTS fact_traffic (
    traffic_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    channel_key INTEGER NOT NULL,

    -- 度量指标
    visitors BIGINT NOT NULL DEFAULT 0,  -- 访客数
    page_views BIGINT NOT NULL DEFAULT 0,  -- 页面浏览量
    unique_visitors BIGINT NOT NULL DEFAULT 0,  -- 独立访客
    add_to_cart_count BIGINT NOT NULL DEFAULT 0,  -- 加购次数
    checkout_count BIGINT NOT NULL DEFAULT 0,  -- 结账次数
    order_count BIGINT NOT NULL DEFAULT 0,  -- 下单次数

    -- 转化率
    cart_conversion_rate DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN visitors > 0 THEN (add_to_cart_count::DECIMAL / visitors) ELSE 0 END
    ) STORED,
    checkout_conversion_rate DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN visitors > 0 THEN (checkout_count::DECIMAL / visitors) ELSE 0 END
    ) STORED,
    order_conversion_rate DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN visitors > 0 THEN (order_count::DECIMAL / visitors) ELSE 0 END
    ) STORED,

    -- 元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (region_key) REFERENCES dim_region(region_key),
    FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key)
);

-- 2.4 收入事实表 (ARPU/LTV相关)
CREATE TABLE IF NOT EXISTS fact_revenue (
    revenue_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    user_level_key INTEGER NOT NULL,

    -- 度量指标
    total_revenue DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 总收入
    total_users BIGINT NOT NULL DEFAULT 0,  -- 总用户数
    paying_users BIGINT NOT NULL DEFAULT 0,  -- 付费用户数

    -- 计算字段
    arpu DECIMAL(18, 2) GENERATED ALWAYS AS (
        CASE WHEN total_users > 0 THEN (total_revenue / total_users) ELSE 0 END
    ) STORED,  -- ARPU (Average Revenue Per User)
    arppu DECIMAL(18, 2) GENERATED ALWAYS AS (
        CASE WHEN paying_users > 0 THEN (total_revenue / paying_users) ELSE 0 END
    ) STORED,  -- ARPPU (Average Revenue Per Paying User)

    -- LTV相关
    ltv_30d DECIMAL(18, 2) DEFAULT NULL,  -- 30天LTV
    ltv_90d DECIMAL(18, 2) DEFAULT NULL,  -- 90天LTV
    ltv_365d DECIMAL(18, 2) DEFAULT NULL,  -- 365天LTV

    -- 元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (region_key) REFERENCES dim_region(region_key),
    FOREIGN KEY (user_level_key) REFERENCES dim_user_level(level_key)
);

-- 2.5 财务事实表 (利润率相关)
CREATE TABLE IF NOT EXISTS fact_finance (
    finance_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,

    -- 度量指标
    revenue DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 营收
    cost_of_goods_sold DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 销售成本 (COGS)
    operating_expense DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 运营费用
    net_profit DECIMAL(18, 2) GENERATED ALWAYS AS (revenue - cost_of_goods_sold - operating_expense) STORED,

    -- 利润率
    gross_profit DECIMAL(18, 2) GENERATED ALWAYS AS (revenue - cost_of_goods_sold) STORED,
    gross_profit_margin DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN revenue > 0 THEN ((revenue - cost_of_goods_sold) / revenue) ELSE 0 END
    ) STORED,
    net_profit_margin DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN revenue > 0 THEN (net_profit / revenue) ELSE 0 END
    ) STORED,

    -- ROI相关
    marketing_cost DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- 营销成本
    roi DECIMAL(5, 4) GENERATED ALWAYS AS (
        CASE WHEN marketing_cost > 0 THEN ((revenue - marketing_cost) / marketing_cost) ELSE 0 END
    ) STORED,  -- 投资回报率

    -- 元数据
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (region_key) REFERENCES dim_region(region_key)
);

-- ============================================
-- 3. 索引 (Indexes)
-- ============================================

-- 3.1 维度表索引

-- 日期维度索引
CREATE INDEX IF NOT EXISTS idx_dim_date_year ON dim_date(year);
CREATE INDEX IF NOT EXISTS idx_dim_date_quarter ON dim_date(quarter);
CREATE INDEX IF NOT EXISTS idx_dim_date_month ON dim_date(month);
CREATE INDEX IF NOT EXISTS idx_dim_date_week ON dim_date(week);
CREATE INDEX IF NOT EXISTS idx_dim_date_is_holiday ON dim_date(is_holiday);

-- 地区维度索引
CREATE INDEX IF NOT EXISTS idx_dim_region_tier ON dim_region(tier);
CREATE INDEX IF NOT EXISTS idx_dim_region_parent ON dim_region(parent_region_id);

-- 品类维度索引
CREATE INDEX IF NOT EXISTS idx_dim_category_parent ON dim_category(parent_category_id);
CREATE INDEX IF NOT EXISTS idx_dim_category_level ON dim_category(level);

-- 3.2 事实表索引

-- 订单事实表索引
CREATE INDEX IF NOT EXISTS idx_fact_orders_date ON fact_orders(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date_region ON fact_orders(date_key, region_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date_category ON fact_orders(date_key, category_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_date_channel ON fact_orders(date_key, channel_key);
CREATE INDEX IF NOT EXISTS idx_fact_orders_created_at ON fact_orders(created_at);

-- 用户活跃度事实表索引
CREATE INDEX IF NOT EXISTS idx_fact_user_activity_date ON fact_user_activity(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_user_activity_date_region ON fact_user_activity(date_key, region_key);
CREATE INDEX IF NOT EXISTS idx_fact_user_activity_date_channel ON fact_user_activity(date_key, channel_key);
CREATE INDEX IF NOT EXISTS idx_fact_user_activity_created_at ON fact_user_activity(created_at);

-- 流量事实表索引
CREATE INDEX IF NOT EXISTS idx_fact_traffic_date ON fact_traffic(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_date_region ON fact_traffic(date_key, region_key);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_date_channel ON fact_traffic(date_key, channel_key);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_created_at ON fact_traffic(created_at);

-- 收入事实表索引
CREATE INDEX IF NOT EXISTS idx_fact_revenue_date ON fact_revenue(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_revenue_date_region ON fact_revenue(date_key, region_key);
CREATE INDEX IF NOT EXISTS idx_fact_revenue_created_at ON fact_revenue(created_at);

-- 财务事实表索引
CREATE INDEX IF NOT EXISTS idx_fact_finance_date ON fact_finance(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_finance_date_region ON fact_finance(date_key, region_key);
CREATE INDEX IF NOT EXISTS idx_fact_finance_created_at ON fact_finance(created_at);

-- ============================================
-- 4. 物化视图 (Materialized Views) - 性能优化
-- ============================================

-- 4.1 每日GMV汇总（按地区）
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_gmv_by_region AS
SELECT
    fo.date_key,
    dr.region_id,
    dr.region_name,
    SUM(fo.gmv) as total_gmv,
    SUM(fo.order_count) as total_orders,
    AVG(fo.average_order_value) as avg_order_value
FROM fact_orders fo
JOIN dim_region dr ON fo.region_key = dr.region_key
GROUP BY fo.date_key, dr.region_id, dr.region_name
WITH DATA;

-- 4.2 每日DAU汇总（按渠道）
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_dau_by_channel AS
SELECT
    fua.date_key,
    dc.channel_id,
    dc.channel_name,
    SUM(fua.dau) as total_dau,
    SUM(fua.new_users) as total_new_users,
    AVG(fua.avg_session_duration) as avg_session_duration
FROM fact_user_activity fua
JOIN dim_channel dc ON fua.channel_key = dc.channel_key
GROUP BY fua.date_key, dc.channel_id, dc.channel_name
WITH DATA;

-- 4.3 月度财务汇总
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_finance_summary AS
SELECT
    EXTRACT(YEAR FROM dd.date)::INTEGER as year,
    dd.month,
    SUM(ff.revenue) as total_revenue,
    SUM(ff.net_profit) as total_net_profit,
    AVG(ff.net_profit_margin) as avg_net_profit_margin,
    SUM(ff.marketing_cost) as total_marketing_cost,
    AVG(ff.roi) as avg_roi
FROM fact_finance ff
JOIN dim_date dd ON ff.date_key = dd.date_key
GROUP BY EXTRACT(YEAR FROM dd.date), dd.month
WITH DATA;

-- 创建物化视图索引
CREATE INDEX IF NOT EXISTS idx_mv_daily_gmv_date ON mv_daily_gmv_by_region(date_key);
CREATE INDEX IF NOT EXISTS idx_mv_daily_dau_date ON mv_daily_dau_by_channel(date_key);
CREATE INDEX IF NOT EXISTS idx_mv_monthly_finance_year_month ON mv_monthly_finance_summary(year, month);

-- ============================================
-- 5. 注释和说明 (Comments)
-- ============================================

-- 维度表注释
COMMENT ON TABLE dim_date IS '日期维度表 - 支持时间范围分析';
COMMENT ON TABLE dim_region IS '地区维度表 - 支持地域分析';
COMMENT ON TABLE dim_category IS '品类维度表 - 支持品类层级分析';
COMMENT ON TABLE dim_channel IS '渠道维度表 - 支持渠道分析';
COMMENT ON TABLE dim_user_level IS '用户等级维度表 - 支持用户分层分析';

-- 事实表注释
COMMENT ON TABLE fact_orders IS '订单事实表 - GMV订单数据';
COMMENT ON TABLE fact_user_activity IS '用户活跃度事实表 - DAU/MAU/留存率';
COMMENT ON TABLE fact_traffic IS '流量事实表 - 转化率漏斗';
COMMENT ON TABLE fact_revenue IS '收入事实表 - ARPU/LTV';
COMMENT ON TABLE fact_finance IS '财务事实表 - 利润率ROI';

-- 物化视图注释
COMMENT ON MATERIALIZED VIEW mv_daily_gmv_by_region IS '每日GMV按地区汇总';
COMMENT ON MATERIALIZED VIEW mv_daily_dau_by_channel IS '每日DAU按渠道汇总';
COMMENT ON MATERIALIZED VIEW mv_monthly_finance_summary IS '月度财务汇总';

-- ============================================
-- 6. 触发器 - 自动更新 updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有事实表添加触发器
CREATE TRIGGER trigger_fact_orders_updated_at
    BEFORE UPDATE ON fact_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_fact_user_activity_updated_at
    BEFORE UPDATE ON fact_user_activity
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_fact_traffic_updated_at
    BEFORE UPDATE ON fact_traffic
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_fact_revenue_updated_at
    BEFORE UPDATE ON fact_revenue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_fact_finance_updated_at
    BEFORE UPDATE ON fact_finance
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Schema创建完成
-- ============================================
