require('dotenv').config();

const config = {
  // Server configuration
  port: parseInt(process.env.PORT, 10) || 5000,
  nodeEnv: process.env.NODE_ENV || 'development',

  // Service URLs
  // Render's fromService.property=host gives a bare hostname — add https:// if missing
  agentServiceUrl: (() => {
    const raw = process.env.AGENT_SERVICE_URL || 'http://localhost:8000';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    // Render internal hostnames (e.g. service-name:10000) use HTTP, not HTTPS
    return `http://${raw}`;
  })(),

  // CORS configuration
  corsOrigins: process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map(s => s.trim())
    : ['http://localhost:5173', 'http://localhost:3000'],

  // MongoDB configuration
  mongodbUri: process.env.MONGODB_URI || null,
  dbEnabled: !!process.env.MONGODB_URI,

  // Resilience settings
  agentTimeoutMs: parseInt(process.env.AGENT_TIMEOUT_MS, 10) || 300_000,
  circuitFailureThreshold: parseInt(process.env.CIRCUIT_FAILURE_THRESHOLD, 10) || 3,
  circuitRecoveryTimeoutMs: parseInt(process.env.CIRCUIT_RECOVERY_TIMEOUT_MS, 10) || 60_000,

  // Rate limiting
  rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10) || 15 * 60 * 1000,
  rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX, 10) || 100,
};

// ─── Startup Validation ─────────────────────────────────────────────────

function validateConfig() {
  const warnings = [];
  if (!config.agentServiceUrl) warnings.push('AGENT_SERVICE_URL not set');
  if (!config.dbEnabled) warnings.push('MONGODB_URI not set — database features disabled');
  if (config.nodeEnv === 'production' && config.corsOrigins.includes('*')) {
    warnings.push('CORS allows * in production — restrict CORS_ORIGINS');
  }
  if (Number.isNaN(config.port) || config.port < 1 || config.port > 65535) {
    warnings.push(`Invalid PORT=${process.env.PORT}, defaulting to 5000`);
    config.port = 5000;
  }
  for (const w of warnings) {
    console.warn(`⚠️  CONFIG: ${w}`);
  }
  return warnings.length === 0;
}

config.validateConfig = validateConfig;

module.exports = config;
