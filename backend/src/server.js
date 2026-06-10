/**
 * MAESTRO Backend Server
 * Express.js API Gateway
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const config = require('./config');
const apiRoutes = require('./routes/api');
const { connectDB } = require('./db/connection');

// Initialize Express app
const app = express();

// Trust reverse proxy (required for Render & express-rate-limit)
app.set('trust proxy', 1);

// Security middleware
app.use(helmet());

// CORS configuration
app.use(cors({
  origin: config.corsOrigins,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Lightweight health check for uptime monitoring (bypasses rate limiting and logging)
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: { error: 'Too many requests, please try again later.' }
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Logging
if (config.nodeEnv === 'development') {
  app.use(morgan('dev'));
} else {
  app.use(morgan('combined'));
}

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    name: 'MAESTRO Backend API',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      health: '/api/health',
      startOnboarding: 'POST /api/start-onboarding',
      sendResponse: 'POST /api/send-user-response',
      process: 'POST /api/process',
      getOutput: 'GET /api/get-agent-output/:sessionId'
    },
    timestamp: new Date().toISOString()
  });
});

// API routes
app.use('/api', apiRoutes);

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Route ${req.method} ${req.url} not found`
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
    ...(config.nodeEnv === 'development' && { stack: err.stack })
  });
});

// Start server
const PORT = config.port;

async function startServer() {
  // Validate configuration before anything else
  config.validateConfig();

  // Connect to MongoDB first (if configured)
  if (config.dbEnabled) {
    try {
      await connectDB();
    } catch (error) {
      console.error('❌ Failed to connect to MongoDB:', error.message);
      console.warn('⚠️  Server starting without database connection');
    }
  } else {
    console.log('ℹ️  MongoDB not configured (MONGODB_URI not set)');
  }

  // Start Express server AFTER DB connection
  app.listen(PORT, () => {
    console.log(`
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀 MAESTRO Backend Server                                  ║
║                                                              ║
║   Server:   http://localhost:${PORT}                            ║
║   Env:      ${config.nodeEnv.padEnd(10)}                                    ║
║   Agent:    ${config.agentServiceUrl.slice(0, 40).padEnd(40)} ║
║   Database: ${config.dbEnabled ? 'Connected ✅' : 'Disabled ⚠️ '}                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    `);
  });
}

// ─── Graceful Shutdown ──────────────────────────────────────────────────

function gracefulShutdown(signal) {
  console.log(`\n${signal} received — shutting down gracefully`);
  // Give in-flight requests 5 seconds to finish
  setTimeout(() => {
    console.log('Forcing shutdown after timeout');
    process.exit(1);
  }, 5000);
  process.exit(0);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

startServer();

module.exports = app;
