/**
 * MAESTRO MongoDB Connection Module
 * 
 * Provides a reusable, singleton database connection using Mongoose.
 * Supports connection pooling, retry logic, and graceful shutdown.
 * 
 * Usage:
 *   const { connectDB, disconnectDB } = require('./db/connection');
 *   await connectDB();
 * 
 * Environment Variables:
 *   - MONGODB_URI: MongoDB Atlas connection string (required)
 *   - NODE_ENV: Environment mode (development/production)
 */

const mongoose = require('mongoose');

// Connection state tracking
let isConnected = false;

/**
 * MongoDB connection options
 * Optimized for MongoDB Atlas and production workloads
 */
const connectionOptions = {
  // Connection pool settings
  maxPoolSize: 10,
  minPoolSize: 2,
  
  // Timeout settings
  serverSelectionTimeoutMS: 5000,
  socketTimeoutMS: 45000,
  
  // Retry settings
  retryWrites: true,
  retryReads: true,
  
  // Buffer settings (disable command buffering when disconnected)
  bufferCommands: false,
};

/**
 * Connect to MongoDB Atlas
 * 
 * @returns {Promise<typeof mongoose>} Mongoose connection instance
 * @throws {Error} If MONGODB_URI is not set or connection fails
 */
async function connectDB() {
  // Return existing connection if already connected
  if (isConnected && mongoose.connection.readyState === 1) {
    console.log('📦 MongoDB: Using existing connection');
    return mongoose;
  }

  // Validate environment variable
  const mongoURI = process.env.MONGODB_URI;
  if (!mongoURI) {
    throw new Error('MONGODB_URI environment variable is not set');
  }

  try {
    console.log('📦 MongoDB: Connecting to Atlas...');
    
    // Connect with options
    await mongoose.connect(mongoURI, connectionOptions);
    
    isConnected = true;
    console.log('✅ MongoDB: Connected successfully');
    
    // Connection event handlers
    mongoose.connection.on('error', (err) => {
      console.error('❌ MongoDB connection error:', err.message);
      isConnected = false;
    });

    mongoose.connection.on('disconnected', () => {
      console.warn('⚠️ MongoDB: Disconnected');
      isConnected = false;
    });

    mongoose.connection.on('reconnected', () => {
      console.log('🔄 MongoDB: Reconnected');
      isConnected = true;
    });

    return mongoose;
  } catch (error) {
    isConnected = false;
    console.error('❌ MongoDB connection failed:', error.message);
    throw error;
  }
}

/**
 * Disconnect from MongoDB
 * Use during graceful shutdown
 * 
 * @returns {Promise<void>}
 */
async function disconnectDB() {
  if (!isConnected) {
    console.log('📦 MongoDB: Already disconnected');
    return;
  }

  try {
    await mongoose.disconnect();
    isConnected = false;
    console.log('📦 MongoDB: Disconnected gracefully');
  } catch (error) {
    console.error('❌ MongoDB disconnect error:', error.message);
    throw error;
  }
}

/**
 * Get current connection status
 * 
 * @returns {Object} Connection status object
 */
function getConnectionStatus() {
  return {
    isConnected,
    readyState: mongoose.connection.readyState,
    readyStateText: ['disconnected', 'connected', 'connecting', 'disconnecting'][mongoose.connection.readyState] || 'unknown',
    host: mongoose.connection.host || null,
    name: mongoose.connection.name || null,
  };
}

/**
 * Health check for MongoDB connection
 * 
 * @returns {Promise<Object>} Health status
 */
async function healthCheck() {
  try {
    if (mongoose.connection.readyState !== 1) {
      return { healthy: false, message: 'Not connected' };
    }
    
    // Ping the database
    await mongoose.connection.db.admin().ping();
    return { healthy: true, message: 'Connected and responsive' };
  } catch (error) {
    return { healthy: false, message: error.message };
  }
}

// Handle process termination gracefully
process.on('SIGINT', async () => {
  await disconnectDB();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await disconnectDB();
  process.exit(0);
});

module.exports = {
  connectDB,
  disconnectDB,
  getConnectionStatus,
  healthCheck,
  mongoose,
};
