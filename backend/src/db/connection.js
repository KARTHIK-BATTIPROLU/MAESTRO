/**
 * MAESTRO MongoDB Connection Module
 *
 * Provides a reusable, singleton database connection using Mongoose.
 * Supports connection pooling, auto-reconnection, and graceful shutdown.
 */

const mongoose = require('mongoose');

// ─── State ────────────────────────────────────────────────────────────────────
let isConnected = false;
let connectionAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// ─── Options ──────────────────────────────────────────────────────────────────
const connectionOptions = {
  maxPoolSize: 10,
  minPoolSize: 1,
  serverSelectionTimeoutMS: 30000, // 30s for Atlas cold starts
  socketTimeoutMS: 45000,
  connectTimeoutMS: 30000,
  heartbeatFrequencyMS: 10000,
  retryWrites: true,
  retryReads: true,
  // bufferCommands: true means Mongoose queues operations until connected
  // rather than immediately throwing an error
  bufferCommands: true,
};

// ─── Connect ──────────────────────────────────────────────────────────────────
async function connectDB() {
  if (isConnected && mongoose.connection.readyState === 1) {
    return mongoose;
  }

  const mongoURI = process.env.MONGODB_URI;
  if (!mongoURI) {
    throw new Error('MONGODB_URI environment variable is not set');
  }

  try {
    connectionAttempts++;
    console.log(`📦 MongoDB: Connecting to Atlas... (attempt ${connectionAttempts})`);

    await mongoose.connect(mongoURI, connectionOptions);

    isConnected = true;
    connectionAttempts = 0;
    console.log('✅ MongoDB: Connected successfully to', mongoose.connection.host);

    // ── Event Handlers ───────────────────────────────────────────────────────
    mongoose.connection.off('error', onError);
    mongoose.connection.off('disconnected', onDisconnected);
    mongoose.connection.off('reconnected', onReconnected);

    mongoose.connection.on('error', onError);
    mongoose.connection.on('disconnected', onDisconnected);
    mongoose.connection.on('reconnected', onReconnected);

    return mongoose;
  } catch (error) {
    isConnected = false;
    console.error('❌ MongoDB connection failed:', error.message);

    // Auto-retry with backoff (up to MAX_RECONNECT_ATTEMPTS)
    if (connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
      const delay = Math.min(1000 * Math.pow(2, connectionAttempts), 30000);
      console.log(`🔄 MongoDB: Retrying in ${delay / 1000}s...`);
      await new Promise(r => setTimeout(r, delay));
      return connectDB();
    }

    throw error;
  }
}

function onError(err) {
  console.error('❌ MongoDB error:', err.message);
  isConnected = false;
}

function onDisconnected() {
  console.warn('⚠️  MongoDB: Disconnected — will auto-reconnect');
  isConnected = false;
  // Mongoose auto-reconnects when bufferCommands is true
}

function onReconnected() {
  console.log('🔄 MongoDB: Reconnected');
  isConnected = true;
  connectionAttempts = 0;
}

// ─── Disconnect ───────────────────────────────────────────────────────────────
async function disconnectDB() {
  if (!isConnected && mongoose.connection.readyState === 0) {
    return;
  }
  try {
    await mongoose.disconnect();
    isConnected = false;
    console.log('📦 MongoDB: Disconnected gracefully');
  } catch (error) {
    console.error('❌ MongoDB disconnect error:', error.message);
  }
}

// ─── Status ───────────────────────────────────────────────────────────────────
function getConnectionStatus() {
  const stateNames = ['disconnected', 'connected', 'connecting', 'disconnecting'];
  return {
    isConnected,
    readyState: mongoose.connection.readyState,
    readyStateText: stateNames[mongoose.connection.readyState] || 'unknown',
    host: mongoose.connection.host || null,
    name: mongoose.connection.name || null,
  };
}

/**
 * Check if the DB is usable right now.
 * Returns false if not connected — callers can return 503 gracefully.
 */
function isDbReady() {
  return mongoose.connection.readyState === 1;
}

// ─── Health ───────────────────────────────────────────────────────────────────
async function healthCheck() {
  try {
    if (mongoose.connection.readyState !== 1) {
      return { healthy: false, message: 'Not connected', readyState: mongoose.connection.readyState };
    }
    await mongoose.connection.db.admin().ping();
    return { healthy: true, message: 'Connected and responsive', host: mongoose.connection.host };
  } catch (error) {
    return { healthy: false, message: error.message };
  }
}

// ─── Graceful shutdown ────────────────────────────────────────────────────────
process.on('SIGINT', async () => { await disconnectDB(); process.exit(0); });
process.on('SIGTERM', async () => { await disconnectDB(); process.exit(0); });

module.exports = {
  connectDB,
  disconnectDB,
  getConnectionStatus,
  isDbReady,
  healthCheck,
  mongoose,
};
