/**
 * MAESTRO Data Routes
 * 
 * REST API routes for operational data input and retrieval.
 * Prefix: /api/data
 * 
 * Routes:
 *   POST /api/data/daily-sales           - Create daily sales record
 *   GET  /api/data/daily-sales/:business_id - Get last 30 days sales
 *   POST /api/data/warehouse-snapshot    - Create warehouse snapshot
 *   GET  /api/data/warehouse/:business_id - Get latest warehouse snapshot
 *   POST /api/data/supplier-delivery     - Create supplier delivery
 *   GET  /api/data/supplier-leadtime/:business_id - Get deliveries with avg lead time
 *   GET  /api/data/business-state/:business_id - Get aggregated business state (READ-ONLY)
 */

const express = require('express');
const router = express.Router();
const dataController = require('../controllers/dataController');

// ========================================
// DAILY SALES ROUTES
// ========================================

/**
 * @route   POST /api/data/daily-sales
 * @desc    Create a new daily sales record
 * @body    { business_id, date, product_id, units_sold, revenue?, closing_stock? }
 * @returns { success, data }
 */
router.post('/daily-sales', dataController.createDailySales);

/**
 * @route   GET /api/data/daily-sales/:business_id
 * @desc    Get daily sales for a business (last 30 days)
 * @params  business_id - Business ID
 * @returns { success, data, count }
 */
router.get('/daily-sales/:business_id', dataController.getDailySales);

// ========================================
// WAREHOUSE SNAPSHOT ROUTES
// ========================================

/**
 * @route   POST /api/data/warehouse-snapshot
 * @desc    Create a new warehouse snapshot
 * @body    { business_id, date, current_stock, max_capacity, storage_type?, notes? }
 * @returns { success, data }
 */
router.post('/warehouse-snapshot', dataController.createWarehouseSnapshot);

/**
 * @route   GET /api/data/warehouse/:business_id
 * @desc    Get latest warehouse snapshot for a business
 * @params  business_id - Business ID
 * @returns { success, data }
 */
router.get('/warehouse/:business_id', dataController.getWarehouseSnapshot);

// ========================================
// SUPPLIER DELIVERY ROUTES
// ========================================

/**
 * @route   POST /api/data/supplier-delivery
 * @desc    Create a new supplier delivery record (auto-computes lead_time_days)
 * @body    { business_id, supplier_id, product_id?, order_date, delivery_date, quantity_received }
 * @returns { success, data }
 */
router.post('/supplier-delivery', dataController.createSupplierDelivery);

/**
 * @route   GET /api/data/supplier-leadtime/:business_id
 * @desc    Get last 20 supplier deliveries with average lead time
 * @params  business_id - Business ID
 * @returns { success, data, average_lead_time_days, count }
 */
router.get('/supplier-leadtime/:business_id', dataController.getSupplierLeadTimes);

// ========================================
// BUSINESS STATE AGGREGATION (READ-ONLY)
// ========================================

/**
 * @route   GET /api/data/business-state/:business_id
 * @desc    Get aggregated business state computed from all data sources
 * @params  business_id - Business ID
 * @returns {
 *   success,
 *   business_id,
 *   demand_snapshot: { avg_daily_sales, last_7_days_total, sales_trend },
 *   warehouse_snapshot: { current_stock, max_capacity, utilization_ratio },
 *   supplier_snapshot: { avg_lead_time_days, variability_level },
 *   data_freshness: { sales_days_ago, warehouse_days_ago, supplier_days_ago },
 *   warnings
 * }
 */
router.get('/business-state/:business_id', dataController.getBusinessState);

module.exports = router;
