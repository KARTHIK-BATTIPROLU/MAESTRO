/**
 * MAESTRO DecisionSnapshot Model
 * 
 * Persists point-in-time inventory decision snapshots for audit and analytics.
 * Insert-only - no updates allowed.
 * 
 * Example:
 *   const { DecisionSnapshot } = require('./models/DecisionSnapshot');
 *   
 *   await DecisionSnapshot.create({
 *     business_id: 'biz_123',
 *     decision: { reorder_timing: 'EARLY', order_strategy: 'SPLIT_ORDERS', risk_level: 'HIGH' },
 *     reorder_point: { units: 575, status: 'BELOW', action: 'REORDER_NOW', days_of_cover_left: 4.0, alert_level: 'CRITICAL' },
 *     context_used: { has_daily_sales: true, has_warehouse_snapshot: true, has_supplier_data: false },
 *     explanation: { what_we_understood: {...}, why_this_decision: '...' }
 *   });
 */

const mongoose = require('mongoose');
const { Schema } = mongoose;

/**
 * DecisionSnapshot Schema
 * 
 * Fields:
 * - business_id: Unique identifier for the MSME business
 * - created_at: Timestamp when decision was made (auto)
 * - decision: The final_decision object (timing, strategy, risk_level)
 * - reorder_point: Full reorder point object (units, status, action, days_of_cover, alert_level)
 * - context_used: Flags indicating which data sources were available
 * - explanation: What was understood and why this decision was made
 */
const decisionSnapshotSchema = new Schema({
  business_id: {
    type: String,
    required: [true, 'Business ID is required'],
    trim: true,
    index: true,
  },
  
  // Auto-generated timestamp
  created_at: {
    type: Date,
    default: Date.now,
    index: true,
  },
  
  // Final decision output (subset of agent response)
  decision: {
    reorder_timing: {
      type: String,
      enum: ['EARLY', 'NORMAL', 'DELAYED'],
    },
    order_strategy: {
      type: String,
      enum: ['BULK', 'SPLIT_ORDERS', 'FREQUENT_SMALL'],
    },
    risk_level: {
      type: String,
      enum: ['HIGH', 'MODERATE', 'LOW'],
    },
    confidence: {
      type: Number,
      min: 0,
      max: 1,
    },
    recommended_quantity_range: {
      lower: Number,
      upper: Number,
    },
  },
  
  // Full reorder point object
  reorder_point: {
    units: Number,
    status: {
      type: String,
      enum: ['BELOW', 'NEAR', 'ABOVE'],
    },
    action: {
      type: String,
      enum: ['REORDER_NOW', 'PREPARE', 'SAFE'],
    },
    days_of_cover_left: Number,
    alert_level: {
      type: String,
      enum: ['CRITICAL', 'WARNING', 'OK'],
    },
  },
  
  // Flags indicating which data sources were used
  context_used: {
    has_daily_sales: { type: Boolean, default: false },
    has_warehouse_snapshot: { type: Boolean, default: false },
    has_supplier_data: { type: Boolean, default: false },
    has_business_state: { type: Boolean, default: false },
  },
  
  // Explanation fields for audit
  explanation: {
    what_we_understood: Schema.Types.Mixed,
    why_this_decision: String,
  },

  // User feedback on decision quality (optional, mutable)
  outcome: {
    type: String,
    enum: ['GOOD', 'BAD', 'UNKNOWN'],
    default: 'UNKNOWN',
  },
});

// Compound index for efficient queries by business + time
decisionSnapshotSchema.index({ business_id: 1, created_at: -1 });

/**
 * Static method to save a decision snapshot safely.
 * Catches and logs errors without throwing.
 * 
 * @param {Object} snapshotData - The snapshot data to save
 * @returns {Promise<Object|null>} - The saved document or null on error
 */
decisionSnapshotSchema.statics.saveSnapshot = async function(snapshotData) {
  try {
    const snapshot = await this.create(snapshotData);
    console.log(`📸 DecisionSnapshot saved: ${snapshot._id} for business ${snapshot.business_id}`);
    return snapshot;
  } catch (error) {
    // Log silently - do not throw or block
    console.error(`⚠️ DecisionSnapshot save failed (non-blocking): ${error.message}`);
    return null;
  }
};

// Create model
const DecisionSnapshot = mongoose.model('DecisionSnapshot', decisionSnapshotSchema);

module.exports = {
  DecisionSnapshot,
  decisionSnapshotSchema,
};
