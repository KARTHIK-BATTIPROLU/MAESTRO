require('dotenv').config();

module.exports = {
  port: process.env.PORT || 5000,
  agentServiceUrl: process.env.AGENT_SERVICE_URL || 'http://localhost:8000',
  nodeEnv: process.env.NODE_ENV || 'development',
  corsOrigins: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : ['http://localhost:5173', 'http://localhost:3000']
};
