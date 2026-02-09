/**
 * AutoVizEngine: 前端自适应可视化引擎
 * 负责根据数据特征自动选择图表类型，并处理交互事件
 */
class AutoVizEngine {
    constructor(canvasId) {
        this.ctx = document.getElementById(canvasId);
        this.chart = null;
    }

    /**
     * 渲染图表的主入口
     * @param {Array} data 数据数组
     * @param {Object} intent 意图信息
     */
    render(data, intent) {
        console.log("AutoVizEngine.render called", { dataLength: data ? data.length : 0, intent });

        if (!this.ctx) {
            console.error("AutoVizEngine: Canvas element not found");
            return;
        }

        if (typeof Chart === 'undefined') {
            console.error("AutoVizEngine: Chart.js library not loaded");
            this.ctx.innerHTML = '<div style="color:red; pading:20px;">Error: Chart.js not loaded</div>';
            return;
        }

        if (this.chart) {
            this.chart.destroy();
        }

        try {
            const chartType = this._determineChartType(data, intent);
            console.log("AutoVizEngine: Determined chart type:", chartType);

            const config = this._generateChartConfig(chartType, data, intent);
            console.log("AutoVizEngine: Generated config:", config);

            this.chart = new Chart(this.ctx, config);
            console.log("AutoVizEngine: Chart created successfully");

            // 手动添加点击监听作为备份
            const manualClickHandler = (evt) => {
                // Remove existing listener to verify we don't stack them if render is called multiple times? 
                // Actually render destroys chart, but doesn't replace canvas. 
                // Best to be simple:
                // nearest mode with intersect: false allows clicking anywhere in the vertical slice
                const points = this.chart.getElementsAtEventForMode(evt, 'nearest', { intersect: false }, true);
                if (points.length) {
                    const firstPoint = points[0];
                    const label = this.chart.data.labels[firstPoint.index];
                    const value = this.chart.data.datasets[firstPoint.datasetIndex].data[firstPoint.index];
                    console.log(`🖱️ Manual Event: Drill-down on ${label} (${value})`);
                    this._handleDrillDown(label, intent);
                }
            };

            // 移除旧的以防重复 (if we store it) - for now just add. 
            // Better: assign to property to remove later
            if (this._manualClickHandler) {
                this.ctx.removeEventListener('click', this._manualClickHandler);
            }
            this._manualClickHandler = manualClickHandler;
            this.ctx.addEventListener('click', manualClickHandler);
            console.log("AutoVizEngine: Added manual click listener");
        } catch (e) {
            console.error("AutoVizEngine: Error creating chart:", e);
        }
    }

    /**
     * 自动推断最佳图表类型
     */
    _determineChartType(data, intent) {
        // 1. 如果意图显式指定了图表类型（未来支持），优先使用
        // if (intent.visualization_type) return intent.visualization_type;

        if (!data || data.length === 0) return 'bar';

        const sample = data[0];
        const hasDate = sample.date || (intent.dimensions && intent.dimensions.includes('date'));
        const hasCategories = sample.dimension || (intent.dimensions && intent.dimensions.length > 0);

        // 2. 时间序列数据 -> 折线图
        if (hasDate) {
            return 'line';
        }

        // 3. 只有1个数据点 -> 指标卡/柱状图
        if (data.length === 1) {
            return 'bar'; // 或者 'metric_card' (如果支持)
        }

        // 4. 类别数据 -> 柱状图 或 饼图
        if (hasCategories) {
            // 如果数据点少且差异明显 -> 饼图
            if (data.length <= 5 && !intent.comparison_type) {
                return 'pie'; // 简单的占比分析
            }
            return 'bar'; // 默认柱状图
        }

        return 'bar';
    }

    /**
     * 生成Chart.js配置
     */
    _generateChartConfig(type, data, intent) {
        const labels = data.map(d => d.date || d.dimension || d.name || '未知');
        const values = data.map(d => d.value || d.metric_value || 0);
        const metricName = intent.core_query || '数值';

        // 基础配置
        const baseConfig = {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    label: metricName,
                    data: values,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: { display: true },
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(45, 55, 72, 0.95)',
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const val = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                                return `${metricName}: ${val.toLocaleString()}`;
                            }
                        }
                    }
                },
                onClick: (event, elements, chart) => {
                    console.log("🖱️ Chart onClick trigger:", { event, elements, chart });
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const label = this.chart.data.labels[index];
                        const value = this.chart.data.datasets[0].data[index];
                        console.log(`🖱️ User clicked on data point: Index=${index}, Label=${label}, Value=${value}`);
                        this._handleDrillDown(label, intent);
                    } else {
                        console.log("🖱️ Click off-element");
                    }
                }
            }
        };

        // 类型特异性样式
        if (type === 'line') {
            baseConfig.data.datasets[0].borderColor = '#667eea';
            baseConfig.data.datasets[0].backgroundColor = 'rgba(102, 126, 234, 0.1)';
            baseConfig.data.datasets[0].fill = true;
            baseConfig.data.datasets[0].tension = 0.4;
            baseConfig.data.datasets[0].pointRadius = 4;
            baseConfig.data.datasets[0].pointHoverRadius = 6;
            baseConfig.options.scales = {
                y: { beginAtZero: false, grid: { color: '#f7fafc' } },
                x: { grid: { display: false } }
            };
        } else if (type === 'bar') {
            baseConfig.data.datasets[0].backgroundColor = values.map((_, i) =>
                i % 2 === 0 ? 'rgba(102, 126, 234, 0.7)' : 'rgba(118, 75, 162, 0.7)'
            );
            baseConfig.data.datasets[0].borderColor = 'transparent';
            baseConfig.data.datasets[0].borderRadius = 4;
            baseConfig.options.scales = {
                y: { beginAtZero: true, grid: { color: '#f7fafc' } },
                x: { grid: { display: false } }
            };
        } else if (type === 'pie') {
            baseConfig.data.datasets[0].backgroundColor = [
                '#667eea', '#764ba2', '#48bb78', '#ed8936', '#4299e1',
                '#f56565', '#ed64a6', '#ecc94b'
            ];
            baseConfig.options.aspectRatio = 2;
            baseConfig.options.cutout = '50%'; // 甜甜圈图
        }

        return baseConfig;
    }

    /**
     * 处理下钻交互
     */
    _handleDrillDown(label, intent) {
        console.log(`🖱️ User clicked on: ${label}`);

        // 简单的下钻逻辑：如果点击的是维度值，尝试将其作为过滤条件
        // 这里我们触发一个全局事件或调用全局函数，让主页面处理查询
        // 例如：用户点击了 "East"，我们生成 "East地区的[Current Metric]"

        let nextQuery = "";

        // 判断 label 是时间还是维度
        const isDate = /^\d{4}-\d{2}-\d{2}$/.test(label);

        if (isDate) {
            // 时间点下钻 -> 看该日的详细分解?
            nextQuery = `看${label}的数据详情`;
        } else {
            // 维度值下钻 -> 过滤该维度
            nextQuery = `只看${label}的数据`;
        }

        if (window.setQueryAndExecute) {
            // 提示用户正在下钻
            const guide = document.getElementById('queryInput');
            if (guide) guide.value = nextQuery;

            // 自动执行
            window.setQueryAndExecute(nextQuery);
        }
    }
}
