require('dotenv').config();

module.exports = {
  // Server configuration
  port: process.env.PORT || 5000,
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // Service URLs
  agentServiceUrl: process.env.AGENT_SERVICE_URL || 'http://localhost:8000',
  
  // CORS configuration
  corsOrigins: process.env.CORS_ORIGINS 
    ? process.env.CORS_ORIGINS.split(',') 
    : ['http://localhost:5173', 'http://localhost:3000'],
  
  // MongoDB configuration
  mongodbUri: process.env.MONGODB_URI || null,
  
  // Database feature flag (enable when MONGODB_URI is set)
  dbEnabled: !!process.env.MONGODB_URI,
};
