/**
 * MAESTRO WarehouseSnapshot Model
 * 
 * Tracks point-in-time warehouse capacity and utilization.
 * Used to enforce storage constraints and prevent overstocking.
 * 
 * Example:
 *   const { WarehouseSnapshot } = require('./models/WarehouseSnapshot');
 *   
 *   await WarehouseSnapshot.create({
 *     business_id: 'biz_123',
 *     date: new Date(),
 *     current_stock: 750,
 *     max_capacity: 1000,
 *     storage_type: 'cold',
 *     notes: 'Post-festival restocking'
 *   });
 */

const mongoose = require('mongoose');
const { Schema } = mongoose;

/**
 * Valid storage types for warehouse
 */
const STORAGE_TYPES = ['cold', 'dry', 'mixed'];

/**
 * WarehouseSnapshot Schema
 * 
 * Fields:
 * - business_id: Unique identifier for the MSME business
 * - date: The date of the snapshot
 * - current_stock: Current inventory level (units)
 * - max_capacity: Maximum storage capacity (units)
 * - storage_type: Type of storage (cold/dry/mixed)
 * - notes: Optional notes about the snapshot
 * - createdAt: Timestamp when record was created
 */
const warehouseSnapshotSchema = new Schema({
  business_id: {
    type: String,
    required: [true, 'Business ID is required'],
    trim: true,
    index: true,
  },
  
  date: {
    type: Date,
    required: [true, 'Date is required'],
    index: true,
  },
  
  current_stock: {
    type: Number,
    required: [true, 'Current stock is required'],
    min: [0, 'Current stock cannot be negative'],
  },
  
  max_capacity: {
    type: Number,
    required: [true, 'Max capacity is required'],
    min: [1, 'Max capacity must be at least 1'],
  },
  
  storage_type: {
    type: String,
    enum: {
      values: STORAGE_TYPES,
      message: 'Storage type must be one of: cold, dry, mixed'
    },
    default: 'dry',
    lowercase: true,
    trim: true,
  },
  
  notes: {
    type: String,
    trim: true,
    maxlength: [500, 'Notes cannot exceed 500 characters'],
    default: null,
  },
  
  createdAt: {
    type: Date,
    default: Date.now,
  },
}, {
  // Schema options
  collection: 'warehouse_snapshots',
  timestamps: false, // We manage createdAt manually
});

// Compound index for efficient queries
warehouseSnapshotSchema.index({ business_id: 1, date: -1 });

/**
 * Virtual: Calculate utilization percentage
 */
warehouseSnapshotSchema.virtual('utilization').get(function() {
  if (!this.max_capacity || this.max_capacity === 0) return 0;
  return Math.round((this.current_stock / this.max_capacity) * 100);
});

/**
 * Virtual: Calculate available capacity
 */
warehouseSnapshotSchema.virtual('available_capacity').get(function() {
  return Math.max(0, this.max_capacity - this.current_stock);
});

/**
 * Virtual: Determine capacity stress level
 */
warehouseSnapshotSchema.virtual('capacity_stress').get(function() {
  const utilization = this.utilization;
  if (utilization >= 75) return 'HIGH';
  if (utilization >= 50) return 'MEDIUM';
  return 'LOW';
});

// Enable virtuals in JSON output
warehouseSnapshotSchema.set('toJSON', { virtuals: true });
warehouseSnapshotSchema.set('toObject', { virtuals: true });

/**
 * Static method: Get latest snapshot for a business
 */
warehouseSnapshotSchema.statics.getLatest = function(businessId) {
  return this.findOne({ business_id: businessId })
    .sort({ date: -1 })
    .exec();
};

/**
 * Static method: Get snapshots for date range
 */
warehouseSnapshotSchema.statics.getByDateRange = function(businessId, startDate, endDate) {
  return this.find({
    business_id: businessId,
    date: { $gte: startDate, $lte: endDate }
  }).sort({ date: -1 });
};

/**
 * Static method: Calculate average utilization over period
 */
warehouseSnapshotSchema.statics.getAverageUtilization = async function(businessId, days = 30) {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  const result = await this.aggregate([
    {
      $match: {
        business_id: businessId,
        date: { $gte: startDate }
      }
    },
    {
      $project: {
        utilization: {
          $multiply: [
            { $divide: ['$current_stock', '$max_capacity'] },
            100
          ]
        }
      }
    },
    {
      $group: {
        _id: null,
        avgUtilization: { $avg: '$utilization' },
        minUtilization: { $min: '$utilization' },
        maxUtilization: { $max: '$utilization' },
        snapshotCount: { $sum: 1 }
      }
    }
  ]);
  
  return result[0] || { avgUtilization: 0, minUtilization: 0, maxUtilization: 0, snapshotCount: 0 };
};

/**
 * Static method: Check if business is near capacity
 */
warehouseSnapshotSchema.statics.isNearCapacity = async function(businessId, threshold = 75) {
  const latest = await this.getLatest(businessId);
  if (!latest) return { nearCapacity: false, message: 'No warehouse data available' };
  
  const utilization = latest.utilization;
  return {
    nearCapacity: utilization >= threshold,
    utilization,
    threshold,
    available_capacity: latest.available_capacity
  };
};

const WarehouseSnapshot = mongoose.model('WarehouseSnapshot', warehouseSnapshotSchema);

module.exports = { WarehouseSnapshot, warehouseSnapshotSchema, STORAGE_TYPES };
