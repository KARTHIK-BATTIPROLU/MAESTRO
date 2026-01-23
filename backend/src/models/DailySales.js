/**
 * MAESTRO DailySales Model
 * 
 * Tracks daily sales data for inventory analysis.
 * Used to understand demand patterns and calculate reorder points.
 * 
 * Example:
 *   const { DailySales } = require('./models/DailySales');
 *   
 *   await DailySales.create({
 *     business_id: 'biz_123',
 *     date: new Date('2024-01-15'),
 *     product_id: 'prod_456',
 *     units_sold: 50,
 *     revenue: 5000,
 *     closing_stock: 120
 *   });
 */

const mongoose = require('mongoose');
const { Schema } = mongoose;

/**
 * DailySales Schema
 * 
 * Fields:
 * - business_id: Unique identifier for the MSME business
 * - date: The date of the sales record
 * - product_id: Unique identifier for the product sold
 * - units_sold: Number of units sold on this date
 * - revenue: Total revenue from sales (optional)
 * - closing_stock: Stock level at end of day (optional)
 * - createdAt: Timestamp when record was created
 */
const dailySalesSchema = new Schema({
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
  
  product_id: {
    type: String,
    required: [true, 'Product ID is required'],
    trim: true,
    index: true,
  },
  
  units_sold: {
    type: Number,
    required: [true, 'Units sold is required'],
    min: [0, 'Units sold cannot be negative'],
  },
  
  revenue: {
    type: Number,
    min: [0, 'Revenue cannot be negative'],
    default: null,
  },
  
  closing_stock: {
    type: Number,
    min: [0, 'Closing stock cannot be negative'],
    default: null,
  },
  
  createdAt: {
    type: Date,
    default: Date.now,
  },
}, {
  // Schema options
  collection: 'daily_sales',
  timestamps: false, // We manage createdAt manually
});

// Compound index for efficient queries
dailySalesSchema.index({ business_id: 1, date: -1, product_id: 1 });

// Index for date range queries
dailySalesSchema.index({ business_id: 1, date: -1 });

/**
 * Static method: Get sales for a business within a date range
 */
dailySalesSchema.statics.getByDateRange = function(businessId, startDate, endDate) {
  return this.find({
    business_id: businessId,
    date: { $gte: startDate, $lte: endDate }
  }).sort({ date: -1 });
};

/**
 * Static method: Get total units sold for a product
 */
dailySalesSchema.statics.getTotalUnitsSold = async function(businessId, productId, startDate, endDate) {
  const result = await this.aggregate([
    {
      $match: {
        business_id: businessId,
        product_id: productId,
        date: { $gte: startDate, $lte: endDate }
      }
    },
    {
      $group: {
        _id: null,
        totalUnits: { $sum: '$units_sold' },
        totalRevenue: { $sum: '$revenue' }
      }
    }
  ]);
  
  return result[0] || { totalUnits: 0, totalRevenue: 0 };
};

/**
 * Static method: Calculate average daily sales
 */
dailySalesSchema.statics.getAverageDailySales = async function(businessId, productId, days = 30) {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  const result = await this.aggregate([
    {
      $match: {
        business_id: businessId,
        product_id: productId,
        date: { $gte: startDate }
      }
    },
    {
      $group: {
        _id: null,
        avgUnits: { $avg: '$units_sold' },
        totalDays: { $sum: 1 }
      }
    }
  ]);
  
  return result[0] || { avgUnits: 0, totalDays: 0 };
};

const DailySales = mongoose.model('DailySales', dailySalesSchema);

module.exports = { DailySales, dailySalesSchema };
