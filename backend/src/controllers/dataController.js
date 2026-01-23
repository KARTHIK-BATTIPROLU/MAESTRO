/**
 * MAESTRO Data Controller
 * 
 * Handles HTTP requests for operational data endpoints.
 * Validates input and delegates to dataService.
 */

const dataService = require('../services/dataService');

/**
 * Validate required fields in request body
 * @param {Object} body - Request body
 * @param {Array<string>} requiredFields - Array of required field names
 * @returns {string|null} Error message or null if valid
 */
function validateRequired(body, requiredFields) {
  const missing = requiredFields.filter(field => {
    const value = body[field];
    return value === undefined || value === null || value === '';
  });
  
  if (missing.length > 0) {
    return `Missing required fields: ${missing.join(', ')}`;
  }
  return null;
}

/**
 * Data Controller
 */
const dataController = {
  
  // ========================================
  // DAILY SALES
  // ========================================

  /**
   * POST /api/data/daily-sales
   * Create a new daily sales record
   */
  async createDailySales(req, res) {
    try {
      const validationError = validateRequired(req.body, [
        'business_id',
        'date',
        'product_id',
        'units_sold'
      ]);
      
      if (validationError) {
        return res.status(400).json({
          success: false,
          error: validationError,
        });
      }
      
      const { units_sold, revenue, closing_stock } = req.body;
      
      // Validate numeric fields
      if (typeof units_sold !== 'number' || units_sold < 0) {
        return res.status(400).json({
          success: false,
          error: 'units_sold must be a non-negative number',
        });
      }
      
      if (revenue !== undefined && revenue !== null && (typeof revenue !== 'number' || revenue < 0)) {
        return res.status(400).json({
          success: false,
          error: 'revenue must be a non-negative number',
        });
      }
      
      if (closing_stock !== undefined && closing_stock !== null && (typeof closing_stock !== 'number' || closing_stock < 0)) {
        return res.status(400).json({
          success: false,
          error: 'closing_stock must be a non-negative number',
        });
      }
      
      const salesRecord = await dataService.createDailySales(req.body);
      
      res.status(201).json({
        success: true,
        data: salesRecord,
      });
    } catch (error) {
      console.error('Error creating daily sales:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to create daily sales record',
      });
    }
  },

  /**
   * GET /api/data/daily-sales/:business_id
   * Get daily sales for a business (last 30 days)
   */
  async getDailySales(req, res) {
    try {
      const { business_id } = req.params;
      
      if (!business_id) {
        return res.status(400).json({
          success: false,
          error: 'business_id is required',
        });
      }
      
      const sales = await dataService.getDailySales(business_id);
      
      res.json({
        success: true,
        data: sales,
        count: sales.length,
      });
    } catch (error) {
      console.error('Error fetching daily sales:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to fetch daily sales',
      });
    }
  },

  // ========================================
  // WAREHOUSE SNAPSHOTS
  // ========================================

  /**
   * POST /api/data/warehouse-snapshot
   * Create a new warehouse snapshot
   */
  async createWarehouseSnapshot(req, res) {
    try {
      const validationError = validateRequired(req.body, [
        'business_id',
        'date',
        'current_stock',
        'max_capacity'
      ]);
      
      if (validationError) {
        return res.status(400).json({
          success: false,
          error: validationError,
        });
      }
      
      const { current_stock, max_capacity, storage_type } = req.body;
      
      // Validate numeric fields
      if (typeof current_stock !== 'number' || current_stock < 0) {
        return res.status(400).json({
          success: false,
          error: 'current_stock must be a non-negative number',
        });
      }
      
      if (typeof max_capacity !== 'number' || max_capacity < 1) {
        return res.status(400).json({
          success: false,
          error: 'max_capacity must be a positive number',
        });
      }
      
      // Validate storage_type if provided
      const validStorageTypes = ['cold', 'dry', 'mixed'];
      if (storage_type && !validStorageTypes.includes(storage_type.toLowerCase())) {
        return res.status(400).json({
          success: false,
          error: `storage_type must be one of: ${validStorageTypes.join(', ')}`,
        });
      }
      
      const snapshot = await dataService.createWarehouseSnapshot(req.body);
      
      res.status(201).json({
        success: true,
        data: snapshot,
      });
    } catch (error) {
      console.error('Error creating warehouse snapshot:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to create warehouse snapshot',
      });
    }
  },

  /**
   * GET /api/data/warehouse/:business_id
   * Get latest warehouse snapshot for a business
   */
  async getWarehouseSnapshot(req, res) {
    try {
      const { business_id } = req.params;
      
      if (!business_id) {
        return res.status(400).json({
          success: false,
          error: 'business_id is required',
        });
      }
      
      const snapshot = await dataService.getLatestWarehouseSnapshot(business_id);
      
      if (!snapshot) {
        return res.status(404).json({
          success: false,
          error: 'No warehouse snapshot found for this business',
        });
      }
      
      res.json({
        success: true,
        data: snapshot,
      });
    } catch (error) {
      console.error('Error fetching warehouse snapshot:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to fetch warehouse snapshot',
      });
    }
  },

  // ========================================
  // SUPPLIER DELIVERIES
  // ========================================

  /**
   * POST /api/data/supplier-delivery
   * Create a new supplier delivery record
   */
  async createSupplierDelivery(req, res) {
    try {
      const validationError = validateRequired(req.body, [
        'business_id',
        'supplier_id',
        'order_date',
        'delivery_date',
        'quantity_received'
      ]);
      
      if (validationError) {
        return res.status(400).json({
          success: false,
          error: validationError,
        });
      }
      
      const { quantity_received } = req.body;
      
      // Validate numeric fields
      if (typeof quantity_received !== 'number' || quantity_received < 0) {
        return res.status(400).json({
          success: false,
          error: 'quantity_received must be a non-negative number',
        });
      }
      
      const delivery = await dataService.createSupplierDelivery(req.body);
      
      res.status(201).json({
        success: true,
        data: delivery,
      });
    } catch (error) {
      console.error('Error creating supplier delivery:', error);
      
      // Handle specific validation errors
      if (error.message.includes('Delivery date cannot be before order date')) {
        return res.status(400).json({
          success: false,
          error: error.message,
        });
      }
      
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to create supplier delivery',
      });
    }
  },

  /**
   * GET /api/data/supplier-leadtime/:business_id
   * Get supplier deliveries with average lead time
   */
  async getSupplierLeadTimes(req, res) {
    try {
      const { business_id } = req.params;
      
      if (!business_id) {
        return res.status(400).json({
          success: false,
          error: 'business_id is required',
        });
      }
      
      const result = await dataService.getSupplierLeadTimes(business_id);
      
      res.json({
        success: true,
        data: result.deliveries,
        average_lead_time_days: result.average_lead_time_days,
        count: result.count,
      });
    } catch (error) {
      console.error('Error fetching supplier lead times:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to fetch supplier lead times',
      });
    }
  },

  // ========================================
  // BUSINESS STATE AGGREGATION
  // ========================================

  /**
   * GET /api/data/business-state/:business_id
   * Get aggregated business state (READ-ONLY)
   * 
   * Returns computed snapshots:
   * - demand_snapshot: avg_daily_sales, last_7_days_total, sales_trend
   * - warehouse_snapshot: current_stock, max_capacity, utilization_ratio
   * - supplier_snapshot: avg_lead_time_days, variability_level
   * - data_freshness: days since last update for each source
   */
  async getBusinessState(req, res) {
    try {
      const { business_id } = req.params;
      
      if (!business_id) {
        return res.status(400).json({
          success: false,
          error: 'business_id is required',
        });
      }
      
      const businessState = await dataService.getBusinessState(business_id);
      
      res.json({
        success: true,
        ...businessState,
      });
    } catch (error) {
      console.error('Error fetching business state:', error);
      res.status(500).json({
        success: false,
        error: error.message || 'Failed to fetch business state',
      });
    }
  },
};

module.exports = dataController;
