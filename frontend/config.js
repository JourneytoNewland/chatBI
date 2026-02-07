/**
 * 前端配置文件
 * 
 * 优先级：环境变量 > 构建配置 > 默认值
 * 
 * 使用方式：
 * 1. 开发环境：创建 .env.local 文件
 * 2. 生产环境：通过构建时注入环境变量
 * 3. 演示环境：使用默认值（localhost）
 */

const config = {
  // API服务端点
  apiBaseUrl: window.API_BASE_URL || 
              window.env?.API_BASE_URL || 
              import.meta.env?.VITE_API_BASE_URL || 
              'http://localhost:8000',

  // 向量数据库服务（仅展示）
  qdrantUrl: window.QDRANT_URL || 
             'http://localhost:6333',

  // 图数据库服务（仅展示）
  neo4jUrl: window.NEO4J_URL || 
             'bolt://localhost:7687',

  // 应用配置
  app: {
    name: '智能问数系统',
    version: '1.0.0',
    environment: window.env?.NODE_ENV || 'development'
  },

  // 功能开关
  features: {
    enableVectorSearch: true,
    enableGraphRecall: true,
    enableLLM: true,
    enableMQL: true,
    enableDataQuery: true,
    enableInterpretation: true
  },

  // 性能配置
  performance: {
    queryTimeout: 30000,  // 30秒
    chartAnimationDuration: 1000,
    autoRefreshInterval: 0  // 0 = 不自动刷新
  },

  // 安全配置
  security: {
    enableRateLimit: true,
    maxRequestsPerMinute: 60,
    enableCORS: true,
    allowedOrigins: [
      'http://localhost:8080',
      'http://127.0.0.1:8080'
    ]
  }
};

// 冻结配置对象，防止运行时修改
Object.freeze(config);
Object.freeze(config.app);
Object.freeze(config.features);
Object.freeze(config.performance);
Object.freeze(config.security);

export default config;
