"""完整的企业指标体系."""

from typing import List, Dict, Any, Optional


# 指标定义
METRIC_CATALOG = {
    # ========== 电商指标 ==========
    "gmv": {
        "metric_id": "gmv",
        "name": "GMV",
        "code": "gmv",
        "name_en": "Gross Merchandise Volume",
        "description": "成交总额，一定时期内成交商品的总金额",
        "domain": "电商",
        "category": "交易",
        "formula": "SUM(order_amount)",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "品类", "渠道", "用户等级"],
        "synonyms": ["成交金额", "交易额", "成交总额", "销售额", "流水"],
        "related_metrics": ["arpu", "aoe", "conversion_rate", "order_count"],
        "calculation_type": "SUM",
        "data_source": "order_table"
    },
    "gmv_by_category": {
        "metric_id": "gmv_by_category",
        "name": "分类GMV",
        "code": "gmv_category",
        "name_en": "GMV by Category",
        "description": "按商品分类统计的成交金额",
        "domain": "电商",
        "category": "交易",
        "formula": "SUM(order_amount) GROUP BY category",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["品类", "一级分类", "二级分类"],
        "synonyms": ["品类GMV", "分类成交额"],
        "related_metrics": ["gmv"],
        "calculation_type": "SUM",
        "data_source": "order_table"
    },
    "order_count": {
        "metric_id": "order_count",
        "name": "订单量",
        "code": "order_count",
        "name_en": "Order Count",
        "description": "一定时期内的订单总数",
        "domain": "电商",
        "category": "交易",
        "formula": "COUNT(order_id)",
        "unit": "单",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "品类", "渠道"],
        "synonyms": ["订单数", "下单量", "成交订单数"],
        "related_metrics": ["gmv", "conversion_rate"],
        "calculation_type": "COUNT",
        "data_source": "order_table"
    },
    "conversion_rate": {
        "metric_id": "conversion_rate",
        "name": "转化率",
        "code": "conversion_rate",
        "name_en": "Conversion Rate",
        "description": "访客转化为下单用户的比例",
        "domain": "营销",
        "category": "转化",
        "formula": "COUNT(orders) / COUNT(visitors) * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["渠道", "活动", "用户来源"],
        "synonyms": ["转化比率", "访问转化率", "下单转化率"],
        "related_metrics": ["visit_count", "order_count"],
        "calculation_type": "RATIO",
        "data_source": "traffic_table"
    },
    "cart_rate": {
        "metric_id": "cart_rate",
        "name": "加购率",
        "code": "cart_rate",
        "name_en": "Cart Rate",
        "description": "访客加购的比例",
        "domain": "营销",
        "category": "转化",
        "formula": "COUNT(users_with_cart) / COUNT(visitors) * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["品类", "渠道"],
        "synonyms": ["购物车转化率", "加购转化率"],
        "related_metrics": ["conversion_rate"],
        "calculation_type": "RATIO",
        "data_source": "traffic_table"
    },
    "pay_rate": {
        "metric_id": "pay_rate",
        "name": "支付率",
        "code": "pay_rate",
        "name_en": "Payment Rate",
        "description": "下单用户完成支付的比例",
        "domain": "营销",
        "category": "转化",
        "formula": "COUNT(paid_orders) / COUNT(orders) * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["支付方式", "渠道"],
        "synonyms": ["支付成功率", "订单支付率"],
        "related_metrics": ["conversion_rate"],
        "calculation_type": "RATIO",
        "data_source": "order_table"
    },

    # ========== 用户指标 ==========
    "dau": {
        "metric_id": "dau",
        "name": "DAU",
        "code": "dau",
        "name_en": "Daily Active Users",
        "description": "日活跃用户数，当日启动应用或访问网站的用户数",
        "domain": "用户",
        "category": "活跃度",
        "formula": "COUNT(DISTINCT user_id WHERE activity_date = current_date)",
        "unit": "人",
        "granularity": ["day"],
        "dimensions": ["地区", "渠道", "设备类型", "用户等级"],
        "synonyms": ["日活", "日活跃用户", "每日活跃用户"],
        "related_metrics": ["mau", "wau", "dau_mau_ratio"],
        "calculation_type": "COUNT",
        "data_source": "user_activity_log"
    },
    "mau": {
        "metric_id": "mau",
        "name": "MAU",
        "code": "mau",
        "name_en": "Monthly Active Users",
        "description": "月活跃用户数，当月活跃的用户数",
        "domain": "用户",
        "category": "活跃度",
        "formula": "COUNT(DISTINCT user_id WHERE activity_month = current_month)",
        "unit": "人",
        "granularity": ["month"],
        "dimensions": ["地区", "渠道", "设备类型", "用户等级"],
        "synonyms": ["月活", "月活跃用户", "每月活跃用户"],
        "related_metrics": ["dau", "wau"],
        "calculation_type": "COUNT",
        "data_source": "user_activity_log"
    },
    "new_users": {
        "metric_id": "new_users",
        "name": "新增用户",
        "code": "new_users",
        "name_en": "New Users",
        "description": "一定时期内新注册的用户数",
        "domain": "用户",
        "category": "增长",
        "formula": "COUNT(user_id WHERE register_date >= start_date AND register_date <= end_date)",
        "unit": "人",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "渠道", "获客来源"],
        "synonyms": ["新用户数", "新增注册", "注册用户数"],
        "related_metrics": ["dau", "user_growth_rate"],
        "calculation_type": "COUNT",
        "data_source": "user_profile"
    },
    "retention_rate": {
        "metric_id": "retention_rate",
        "name": "留存率",
        "code": "retention_rate",
        "name_en": "Retention Rate",
        "description": "用户在一段时间后继续使用的比例",
        "domain": "用户",
        "category": "留存",
        "formula": "COUNT(returning_users_day_N) / COUNT(active_users_day_0) * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "渠道", "用户群"],
        "synonyms": ["用户留存", "保留率", "用户保留"],
        "related_metrics": ["dau", "mau", "churn_rate"],
        "calculation_type": "RATIO",
        "data_source": "user_activity_log"
    },
    "churn_rate": {
        "metric_id": "churn_rate",
        "name": "流失率",
        "code": "churn_rate",
        "name_en": "Churn Rate",
        "description": "用户不再活跃的比例",
        "domain": "用户",
        "category": "留存",
        "formula": "100 - retention_rate",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "渠道", "用户群"],
        "synonyms": ["用户流失", "流失比例"],
        "related_metrics": ["retention_rate", "dau", "mau"],
        "calculation_type": "RATE",
        "data_source": "user_activity_log"
    },
    "arpu": {
        "metric_id": "arpu",
        "name": "ARPU",
        "code": "arpu",
        "name_en": "Average Revenue Per User",
        "description": "平均每用户收入",
        "domain": "营收",
        "category": "价值",
        "formula": "SUM(revenue) / COUNT(active_users)",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "渠道", "用户等级"],
        "synonyms": ["人均收入", "每用户平均收入", "客单价"],
        "related_metrics": ["gmv", "dau", "ltv"],
        "calculation_type": "AVG",
        "data_source": "revenue_table"
    },
    "ltv": {
        "metric_id": "ltv",
        "name": "LTV",
        "code": "ltv",
        "name_en": "Lifetime Value",
        "description": "用户生命周期价值，用户在整个生命周期内贡献的收入",
        "domain": "营收",
        "category": "价值",
        "formula": "SUM(revenue_per_user)",
        "unit": "元",
        "granularity": ["month", "quarter", "year"],
        "dimensions": ["地区", "渠道", "用户群"],
        "synonyms": ["生命周期价值", "用户价值", "CLV"],
        "related_metrics": ["arpu", "retention_rate"],
        "calculation_type": "SUM",
        "data_source": "revenue_table"
    },

    # ========== 营收指标 ==========
    "revenue": {
        "metric_id": "revenue",
        "name": "营收",
        "code": "revenue",
        "name_en": "Revenue",
        "description": "一定时期内的总收入",
        "domain": "营收",
        "category": "收入",
        "formula": "SUM(revenue)",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "业务线", "产品"],
        "synonyms": ["收入", "总收入", "营业额"],
        "related_metrics": ["gmv", "profit", "arpu"],
        "calculation_type": "SUM",
        "data_source": "finance_table"
    },
    "profit": {
        "metric_id": "profit",
        "name": "利润",
        "code": "profit",
        "name_en": "Profit",
        "description": "总收入减去总成本",
        "domain": "营收",
        "category": "盈利",
        "formula": "revenue - cost",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "业务线", "产品"],
        "synonyms": ["净利润", "盈利", "收益"],
        "related_metrics": ["revenue", "cost", "profit_margin"],
        "calculation_type": "SUM",
        "data_source": "finance_table"
    },
    "profit_margin": {
        "metric_id": "profit_margin",
        "name": "利润率",
        "code": "profit_margin",
        "name_en": "Profit Margin",
        "description": "利润占收入的比例",
        "domain": "营收",
        "category": "盈利",
        "formula": "profit / revenue * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "业务线"],
        "synonyms": ["净利率", "利润占比", "毛利率"],
        "related_metrics": ["revenue", "profit"],
        "calculation_type": "RATIO",
        "data_source": "finance_table"
    },
    "roi": {
        "metric_id": "roi",
        "name": "ROI",
        "code": "roi",
        "name_en": "Return on Investment",
        "description": "投资回报率，投资收益与投资成本的比率",
        "domain": "营销",
        "category": "效率",
        "formula": "(revenue - cost) / cost * 100",
        "unit": "%",
        "granularity": ["week", "month", "quarter"],
        "dimensions": ["渠道", "活动", "产品"],
        "synonyms": ["投资回报", "回报率"],
        "related_metrics": ["revenue", "cost"],
        "calculation_type": "RATE",
        "data_source": "marketing_table"
    },
    "roas": {
        "metric_id": "roas",
        "name": "ROAS",
        "code": "roas",
        "name_en": "Return on Ad Spend",
        "description": "广告支出回报率，广告收入与广告成本的比率",
        "domain": "营销",
        "category": "效率",
        "formula": "ad_revenue / ad_cost * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["渠道", "活动", "广告组"],
        "synonyms": ["广告回报率", "广告ROI"],
        "related_metrics": ["ad_revenue", "ad_cost"],
        "calculation_type": "RATIO",
        "data_source": "marketing_table"
    },

    # ========== 增长指标 ==========
    "gmv_growth_rate": {
        "metric_id": "gmv_growth_rate",
        "name": "GMV增长率",
        "code": "gmv_growth",
        "name_en": "GMV Growth Rate",
        "description": "GMV相比上一时期的增长百分比",
        "domain": "增长",
        "category": "增长率",
        "formula": "(current_gmv - previous_gmv) / previous_gmv * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "品类"],
        "synonyms": ["成交额增长", "GMV增速"],
        "related_metrics": ["gmv", "dau"],
        "calculation_type": "RATE",
        "data_source": "order_table"
    },
    "user_growth_rate": {
        "metric_id": "user_growth_rate",
        "name": "用户增长率",
        "code": "user_growth",
        "name_en": "User Growth Rate",
        "description": "用户数相比上一时期的增长百分比",
        "domain": "增长",
        "category": "增长率",
        "formula": "(current_users - previous_users) / previous_users * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "渠道"],
        "synonyms": ["新增用户增速", "用户增长速度"],
        "related_metrics": ["new_users", "dau", "mau"],
        "calculation_type": "RATE",
        "data_source": "user_profile"
    },
    "dau_mau_ratio": {
        "metric_id": "dau_mau_ratio",
        "name": "DAU/MAU比值",
        "code": "dau_mau_ratio",
        "name_en": "DAU/MAU Ratio",
        "description": "日活与月活的比值，反映用户粘性",
        "domain": "用户",
        "category": "活跃度",
        "formula": "dau / mau * 100",
        "unit": "%",
        "granularity": ["day", "month"],
        "dimensions": ["地区", "渠道"],
        "synonyms": ["日月活比", "用户活跃比"],
        "related_metrics": ["dau", "mau"],
        "calculation_type": "RATIO",
        "data_source": "user_activity_log"
    },

    # ========== 运营指标 ==========
    "avg_order_value": {
        "metric_id": "avg_order_value",
        "name": "客单价",
        "code": "aov",
        "name_en": "Average Order Value",
        "description": "平均每个订单的金额",
        "domain": "电商",
        "category": "交易",
        "formula": "SUM(order_amount) / COUNT(order_id)",
        "unit": "元",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "品类", "渠道"],
        "synonyms": ["平均订单金额", "客单", "单均"],
        "related_metrics": ["gmv", "order_count"],
        "calculation_type": "AVG",
        "data_source": "order_table"
    },
    "repeat_purchase_rate": {
        "metric_id": "repeat_purchase_rate",
        "name": "复购率",
        "code": "repeat_purchase",
        "name_en": "Repeat Purchase Rate",
        "description": "用户重复购买的比例",
        "domain": "电商",
        "category": "复购",
        "formula": "COUNT(users_with_multiple_orders) / COUNT(purchasing_users) * 100",
        "unit": "%",
        "granularity": ["month", "quarter"],
        "dimensions": ["地区", "品类"],
        "synonyms": ["复购比例", "再购买率", "回头客比例"],
        "related_metrics": ["retention_rate", "ltv"],
        "calculation_type": "RATIO",
        "data_source": "order_table"
    },
    "refund_rate": {
        "metric_id": "refund_rate",
        "name": "退款率",
        "code": "refund_rate",
        "name_en": "Refund Rate",
        "description": "退款订单占总订单的比例",
        "domain": "客服",
        "category": "售后",
        "formula": "COUNT(refunded_orders) / COUNT(orders) * 100",
        "unit": "%",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "品类", "退款原因"],
        "synonyms": ["退货率", "退款比例"],
        "related_metrics": ["gmv", "order_count"],
        "calculation_type": "RATIO",
        "data_source": "order_table"
    },
    "customer_satisfaction": {
        "metric_id": "csat",
        "name": "客户满意度",
        "code": "csat",
        "name_en": "Customer Satisfaction",
        "description": "用户对产品或服务的满意程度评分",
        "domain": "客服",
        "category": "体验",
        "formula": "AVG(satisfaction_score)",
        "unit": "分",
        "granularity": ["day", "week", "month"],
        "dimensions": ["地区", "客服组"],
        "synonyms": ["满意度", "NPS", "好评率"],
        "related_metrics": ["refund_rate", "retention_rate"],
        "calculation_type": "AVG",
        "data_source": "survey_table"
    },
}


class MetricRegistry:
    """指标注册表."""

    def __init__(self):
        """初始化指标注册表."""
        self.metrics = METRIC_CATALOG

    def get_metric(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """获取指标定义."""
        return self.metrics.get(metric_id.lower())

    def search_metrics(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索指标."""
        query = query.lower()
        results = []

        for metric_id, metric in self.metrics.items():
            score = 0.0

            # 精确匹配名称
            if query == metric["name"].lower():
                score = 1.0
            # 精确匹配code
            elif query == metric["code"].lower():
                score = 0.98
            # 精确匹配同义词
            elif any(query == syn.lower() for syn in metric["synonyms"]):
                score = 0.95
            # 名称包含查询
            elif query in metric["name"].lower():
                score = 0.85
            # 描述包含查询
            elif query in metric["description"].lower():
                score = 0.75
            # 同义词包含查询
            elif any(query in syn.lower() for syn in metric["synonyms"]):
                score = 0.80

            if score > 0:
                results.append({**metric, "score": score})

        # 排序并限制数量
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_metrics_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """按业务域获取指标."""
        return [
            metric for metric in self.metrics.values()
            if metric["domain"] == domain
        ]

    def get_metrics_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类获取指标."""
        return [
            metric for metric in self.metrics.values()
            if metric["category"] == category
        ]

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """获取所有指标."""
        return list(self.metrics.values())


# 全局注册表实例
registry = MetricRegistry()


# 测试
if __name__ == "__main__":
    print("\n🧪 测试指标体系")
    print("=" * 60)

    print(f"\n📊 指标总数: {len(registry.metrics)}")

    # 搜索指标
    print("\n🔍 搜索 'GMV':")
    results = registry.search_metrics("GMV")
    for r in results:
        print(f"   - {r['name']} ({r['name_en']}) - {r['description']}")

    # 按域获取
    print(f"\n📈 电商域指标 ({len(registry.get_metrics_by_domain('电商'))}个):")
    for metric in registry.get_metrics_by_domain('电商'):
        print(f"   - {metric['name']}")

    print("\n" + "=" * 60)
