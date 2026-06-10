/**
 * MAESTRO SupplierDelivery Model
 * 
 * Tracks supplier delivery history and lead times.
 * Used to calculate supplier reliability and adjust reorder timing.
 * 
 * Example:
 *   const { SupplierDelivery } = require('./models/SupplierDelivery');
 *   
 *   await SupplierDelivery.create({
 *     business_id: 'biz_123',
 *     supplier_id: 'sup_456',
 *     product_id: 'prod_789',
 *     order_date: new Date('2024-01-10'),
 *     delivery_date: new Date('2024-01-15'),
 *     lead_time_days: 5,
 *     quantity_received: 100
 *   });
 */

const mongoose = require('mongoose');
const { Schema } = mongoose;

/**
 * SupplierDelivery Schema
 * 
 * Fields:
 * - business_id: Unique identifier for the MSME business
 * - supplier_id: Unique identifier for the supplier
 * - product_id: Product delivered (optional - for multi-product orders)
 * - order_date: Date when the order was placed
 * - delivery_date: Date when the delivery was received
 * - lead_time_days: Number of days between order and delivery
 * - quantity_received: Units received in this delivery
 * - createdAt: Timestamp when record was created
 */
const supplierDeliverySchema = new Schema({
  business_id: {
    type: String,
    required: [true, 'Business ID is required'],
    trim: true,
    index: true,
  },
  
  supplier_id: {
    type: String,
    required: [true, 'Supplier ID is required'],
    trim: true,
    index: true,
  },
  
  product_id: {
    type: String,
    trim: true,
    index: true,
    default: null,
  },
  
  order_date: {
    type: Date,
    required: [true, 'Order date is required'],
    index: true,
  },
  
  delivery_date: {
    type: Date,
    required: [true, 'Delivery date is required'],
    index: true,
  },
  
  lead_time_days: {
    type: Number,
    required: [true, 'Lead time in days is required'],
    min: [0, 'Lead time cannot be negative'],
  },
  
  quantity_received: {
    type: Number,
    min: [0, 'Quantity received cannot be negative'],
    default: null,
  },
  
  createdAt: {
    type: Date,
    default: Date.now,
  },
}, {
  // Schema options
  collection: 'supplier_deliveries',
  timestamps: false, // We manage createdAt manually
});

// Compound indexes for efficient queries
supplierDeliverySchema.index({ business_id: 1, supplier_id: 1, order_date: -1 });
supplierDeliverySchema.index({ business_id: 1, delivery_date: -1 });
supplierDeliverySchema.index({ supplier_id: 1, order_date: -1 });

/**
 * Pre-save hook: Validate delivery_date >= order_date
 */
supplierDeliverySchema.pre('save', function() {
  if (this.delivery_date < this.order_date) {
    throw new Error('Delivery date cannot be before order date');
  }
});

/**
 * Static method: Get deliveries for a supplier
 */
supplierDeliverySchema.statics.getBySupplier = function(businessId, supplierId, limit = 50) {
  return this.find({
    business_id: businessId,
    supplier_id: supplierId
  })
    .sort({ delivery_date: -1 })
    .limit(limit);
};

/**
 * Static method: Get deliveries within date range
 */
supplierDeliverySchema.statics.getByDateRange = function(businessId, startDate, endDate) {
  return this.find({
    business_id: businessId,
    delivery_date: { $gte: startDate, $lte: endDate }
  }).sort({ delivery_date: -1 });
};

/**
 * Static method: Calculate average lead time for a supplier
 */
supplierDeliverySchema.statics.getAverageLeadTime = async function(businessId, supplierId, days = 90) {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  const result = await this.aggregate([
    {
      $match: {
        business_id: businessId,
        supplier_id: supplierId,
        order_date: { $gte: startDate }
      }
    },
    {
      $group: {
        _id: null,
        avgLeadTime: { $avg: '$lead_time_days' },
        minLeadTime: { $min: '$lead_time_days' },
        maxLeadTime: { $max: '$lead_time_days' },
        stdDevLeadTime: { $stdDevPop: '$lead_time_days' },
        deliveryCount: { $sum: 1 }
      }
    }
  ]);
  
  return result[0] || {
    avgLeadTime: 0,
    minLeadTime: 0,
    maxLeadTime: 0,
    stdDevLeadTime: 0,
    deliveryCount: 0
  };
};

/**
 * Static method: Calculate supplier reliability score
 * Based on lead time consistency (lower variance = higher reliability)
 */
supplierDeliverySchema.statics.getSupplierReliability = async function(businessId, supplierId, days = 90) {
  const stats = await this.getAverageLeadTime(businessId, supplierId, days);
  
  if (stats.deliveryCount < 3) {
    return {
      reliability_score: null,
      message: 'Insufficient data (need at least 3 deliveries)',
      ...stats
    };
  }
  
  // Calculate coefficient of variation (CV)
  // Lower CV = more consistent = higher reliability
  const cv = stats.avgLeadTime > 0 
    ? (stats.stdDevLeadTime / stats.avgLeadTime) 
    : 0;
  
  // Convert CV to reliability score (0-100)
  // CV of 0 = 100% reliable, CV >= 1 = 0% reliable
  const reliability_score = Math.max(0, Math.min(100, Math.round((1 - cv) * 100)));
  
  // Classify reliability
  let reliability_class;
  if (reliability_score >= 80) reliability_class = 'HIGH';
  else if (reliability_score >= 50) reliability_class = 'MEDIUM';
  else reliability_class = 'LOW';
  
  return {
    reliability_score,
    reliability_class,
    coefficient_of_variation: Math.round(cv * 100) / 100,
    ...stats
  };
};

/**
 * Static method: Get all suppliers for a business with their stats
 */
supplierDeliverySchema.statics.getSuppliersSummary = async function(businessId, days = 90) {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  const result = await this.aggregate([
    {
      $match: {
        business_id: businessId,
        order_date: { $gte: startDate }
      }
    },
    {
      $group: {
        _id: '$supplier_id',
        avgLeadTime: { $avg: '$lead_time_days' },
        minLeadTime: { $min: '$lead_time_days' },
        maxLeadTime: { $max: '$lead_time_days' },
        totalDeliveries: { $sum: 1 },
        totalQuantity: { $sum: '$quantity_received' },
        lastDelivery: { $max: '$delivery_date' }
      }
    },
    {
      $project: {
        supplier_id: '$_id',
        _id: 0,
        avgLeadTime: { $round: ['$avgLeadTime', 1] },
        minLeadTime: 1,
        maxLeadTime: 1,
        leadTimeVariance: { $subtract: ['$maxLeadTime', '$minLeadTime'] },
        totalDeliveries: 1,
        totalQuantity: 1,
        lastDelivery: 1
      }
    },
    {
      $sort: { totalDeliveries: -1 }
    }
  ]);
  
  return result;
};

const SupplierDelivery = mongoose.model('SupplierDelivery', supplierDeliverySchema);

module.exports = { SupplierDelivery, supplierDeliverySchema };
