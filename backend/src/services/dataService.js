/**
 * MAESTRO Data Service
 * 
 * Service layer for operational data operations.
 * Handles business logic for daily sales, warehouse snapshots, and supplier deliveries.
 */

const { DailySales, WarehouseSnapshot, SupplierDelivery } = require('../models');

/**
 * Data Service
 */
class DataService {
  
  // ========================================
  // DAILY SALES
  // ========================================

  /**
   * Create a new daily sales record
   * @param {Object} data - Sales data
   * @returns {Promise<Object>} Created sales record
   */
  async createDailySales(data) {
    const { business_id, date, product_id, units_sold, revenue, closing_stock } = data;
    
    const salesRecord = new DailySales({
      business_id,
      date: new Date(date),
      product_id,
      units_sold,
      revenue: revenue ?? null,
      closing_stock: closing_stock ?? null,
    });
    
    await salesRecord.save();
    return salesRecord;
  }

  /**
   * Get daily sales for a business (last 30 days)
   * @param {string} businessId - Business ID
   * @returns {Promise<Array>} Array of sales records sorted by date descending
   */
  async getDailySales(businessId) {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    const sales = await DailySales.find({
      business_id: businessId,
      date: { $gte: thirtyDaysAgo }
    })
      .sort({ date: -1 })
      .lean();
    
    return sales;
  }

  // ========================================
  // WAREHOUSE SNAPSHOTS
  // ========================================

  /**
   * Create a new warehouse snapshot
   * @param {Object} data - Warehouse snapshot data
   * @returns {Promise<Object>} Created snapshot record
   */
  async createWarehouseSnapshot(data) {
    const { business_id, date, current_stock, max_capacity, storage_type, notes } = data;
    
    const snapshot = new WarehouseSnapshot({
      business_id,
      date: new Date(date),
      current_stock,
      max_capacity,
      storage_type: storage_type || 'dry',
      notes: notes || null,
    });
    
    await snapshot.save();
    
    // Return with virtuals
    return this.enrichWarehouseSnapshot(snapshot);
  }

  /**
   * Get latest warehouse snapshot for a business
   * @param {string} businessId - Business ID
   * @returns {Promise<Object|null>} Latest snapshot or null
   */
  async getLatestWarehouseSnapshot(businessId) {
    const snapshot = await WarehouseSnapshot.findOne({ business_id: businessId })
      .sort({ date: -1 });
    
    if (!snapshot) return null;
    
    return this.enrichWarehouseSnapshot(snapshot);
  }

  /**
   * Enrich warehouse snapshot with computed virtuals
   * @param {Object} snapshot - Mongoose document
   * @returns {Object} Enriched snapshot object
   */
  enrichWarehouseSnapshot(snapshot) {
    const obj = snapshot.toObject();
    obj.utilization = snapshot.utilization;
    obj.available_capacity = snapshot.available_capacity;
    obj.capacity_stress = snapshot.capacity_stress;
    return obj;
  }

  // ========================================
  // SUPPLIER DELIVERIES
  // ========================================

  /**
   * Create a new supplier delivery record
   * Automatically computes lead_time_days from order_date and delivery_date
   * @param {Object} data - Delivery data
   * @returns {Promise<Object>} Created delivery record
   */
  async createSupplierDelivery(data) {
    const { business_id, supplier_id, product_id, order_date, delivery_date, quantity_received } = data;
    
    const orderDateObj = new Date(order_date);
    const deliveryDateObj = new Date(delivery_date);
    
    // Validate delivery_date >= order_date
    if (deliveryDateObj < orderDateObj) {
      throw new Error('Delivery date cannot be before order date');
    }
    
    // Calculate lead time in days
    const timeDiff = deliveryDateObj.getTime() - orderDateObj.getTime();
    const leadTimeDays = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
    
    const delivery = new SupplierDelivery({
      business_id,
      supplier_id,
      product_id: product_id || null,
      order_date: orderDateObj,
      delivery_date: deliveryDateObj,
      lead_time_days: leadTimeDays,
      quantity_received: quantity_received ?? null,
    });
    
    await delivery.save();
    return delivery;
  }

  /**
   * Get supplier deliveries with average lead time
   * Returns last 20 deliveries and calculates average lead time
   * @param {string} businessId - Business ID
   * @returns {Promise<Object>} Deliveries and average lead time
   */
  async getSupplierLeadTimes(businessId) {
    const deliveries = await SupplierDelivery.find({ business_id: businessId })
      .sort({ delivery_date: -1 })
      .limit(20)
      .lean();
    
    // Calculate average lead time
    let averageLeadTimeDays = null;
    if (deliveries.length > 0) {
      const totalLeadTime = deliveries.reduce((sum, d) => sum + d.lead_time_days, 0);
      averageLeadTimeDays = Math.round((totalLeadTime / deliveries.length) * 10) / 10; // 1 decimal place
    }
    
    return {
      deliveries,
      average_lead_time_days: averageLeadTimeDays,
      count: deliveries.length,
    };
  }

  // ========================================
  // BUSINESS STATE AGGREGATION
  // ========================================

  /**
   * Get aggregated business state (READ-ONLY)
   * Computes live snapshots from all operational data sources
   * 
   * @param {string} businessId - Business ID
   * @returns {Promise<Object>} Aggregated business state
   */
  async getBusinessState(businessId) {
    const warnings = [];
    const now = new Date();

    // ----------------------------------------
    // 1. DEMAND SNAPSHOT (from DailySales)
    // ----------------------------------------
    let demandSnapshot = null;
    let salesFreshness = null;

    try {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const salesRecords = await DailySales.find({
        business_id: businessId,
        date: { $gte: thirtyDaysAgo }
      })
        .sort({ date: -1 })
        .limit(30)
        .lean();

      if (salesRecords.length === 0) {
        warnings.push('No sales data found for the last 30 days');
        demandSnapshot = {
          avg_daily_sales: null,
          last_7_days_total: null,
          sales_trend: null,
          record_count: 0,
        };
      } else {
        // Calculate average daily sales
        const totalUnitsSold = salesRecords.reduce((sum, r) => sum + (r.units_sold || 0), 0);
        const avgDailySales = Math.round((totalUnitsSold / salesRecords.length) * 10) / 10;

        // Calculate last 7 days total
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const last7DaysSales = salesRecords.filter(r => new Date(r.date) >= sevenDaysAgo);
        const last7DaysTotal = last7DaysSales.reduce((sum, r) => sum + (r.units_sold || 0), 0);

        // Calculate sales trend (compare last 7 days vs previous 7 days)
        const fourteenDaysAgo = new Date();
        fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);
        const prev7DaysSales = salesRecords.filter(r => {
          const d = new Date(r.date);
          return d >= fourteenDaysAgo && d < sevenDaysAgo;
        });
        const prev7DaysTotal = prev7DaysSales.reduce((sum, r) => sum + (r.units_sold || 0), 0);

        let salesTrend = 'stable';
        if (prev7DaysTotal > 0) {
          const changePercent = ((last7DaysTotal - prev7DaysTotal) / prev7DaysTotal) * 100;
          if (changePercent > 10) {
            salesTrend = 'increasing';
          } else if (changePercent < -10) {
            salesTrend = 'decreasing';
          }
        } else if (last7DaysTotal > 0) {
          salesTrend = 'increasing';
        }

        // Data freshness
        const latestSale = salesRecords[0];
        const daysSinceLastSale = Math.floor((now - new Date(latestSale.date)) / (1000 * 60 * 60 * 24));
        salesFreshness = daysSinceLastSale;

        if (daysSinceLastSale > 7) {
          warnings.push(`Sales data is ${daysSinceLastSale} days old`);
        }

        demandSnapshot = {
          avg_daily_sales: avgDailySales,
          last_7_days_total: last7DaysTotal,
          sales_trend: salesTrend,
          record_count: salesRecords.length,
        };
      }
    } catch (err) {
      console.error('Error fetching sales data:', err);
      warnings.push('Failed to fetch sales data');
      demandSnapshot = {
        avg_daily_sales: null,
        last_7_days_total: null,
        sales_trend: null,
        record_count: 0,
      };
    }

    // ----------------------------------------
    // 2. WAREHOUSE SNAPSHOT
    // ----------------------------------------
    let warehouseSnapshot = null;
    let warehouseFreshness = null;

    try {
      const latestWarehouse = await WarehouseSnapshot.findOne({ business_id: businessId })
        .sort({ date: -1 })
        .lean();

      if (!latestWarehouse) {
        warnings.push('No warehouse snapshot found');
        warehouseSnapshot = {
          current_stock: null,
          max_capacity: null,
          utilization_ratio: null,
          storage_type: null,
        };
      } else {
        const utilizationRatio = latestWarehouse.max_capacity > 0
          ? Math.round((latestWarehouse.current_stock / latestWarehouse.max_capacity) * 100) / 100
          : null;

        // Data freshness
        const daysSinceSnapshot = Math.floor((now - new Date(latestWarehouse.date)) / (1000 * 60 * 60 * 24));
        warehouseFreshness = daysSinceSnapshot;

        if (daysSinceSnapshot > 3) {
          warnings.push(`Warehouse snapshot is ${daysSinceSnapshot} days old`);
        }

        warehouseSnapshot = {
          current_stock: latestWarehouse.current_stock,
          max_capacity: latestWarehouse.max_capacity,
          utilization_ratio: utilizationRatio,
          storage_type: latestWarehouse.storage_type,
        };
      }
    } catch (err) {
      console.error('Error fetching warehouse data:', err);
      warnings.push('Failed to fetch warehouse data');
      warehouseSnapshot = {
        current_stock: null,
        max_capacity: null,
        utilization_ratio: null,
        storage_type: null,
      };
    }

    // ----------------------------------------
    // 3. SUPPLIER SNAPSHOT (from SupplierDelivery)
    // ----------------------------------------
    let supplierSnapshot = null;
    let supplierFreshness = null;

    try {
      const deliveries = await SupplierDelivery.find({ business_id: businessId })
        .sort({ delivery_date: -1 })
        .limit(20)
        .lean();

      if (deliveries.length === 0) {
        warnings.push('No supplier delivery records found');
        supplierSnapshot = {
          avg_lead_time_days: null,
          variability_level: null,
          record_count: 0,
        };
      } else {
        // Calculate average lead time
        const leadTimes = deliveries.map(d => d.lead_time_days);
        const avgLeadTime = Math.round((leadTimes.reduce((a, b) => a + b, 0) / leadTimes.length) * 10) / 10;

        // Calculate variance (standard deviation)
        const mean = avgLeadTime;
        const squaredDiffs = leadTimes.map(lt => Math.pow(lt - mean, 2));
        const variance = squaredDiffs.reduce((a, b) => a + b, 0) / leadTimes.length;
        const stdDev = Math.sqrt(variance);

        // Determine variability level
        let variabilityLevel = 'LOW';
        if (stdDev > 5) {
          variabilityLevel = 'HIGH';
        } else if (stdDev >= 2) {
          variabilityLevel = 'MEDIUM';
        }

        // Data freshness
        const latestDelivery = deliveries[0];
        const daysSinceDelivery = Math.floor((now - new Date(latestDelivery.delivery_date)) / (1000 * 60 * 60 * 24));
        supplierFreshness = daysSinceDelivery;

        if (daysSinceDelivery > 14) {
          warnings.push(`No supplier deliveries in the last ${daysSinceDelivery} days`);
        }

        supplierSnapshot = {
          avg_lead_time_days: avgLeadTime,
          variability_level: variabilityLevel,
          record_count: deliveries.length,
        };
      }
    } catch (err) {
      console.error('Error fetching supplier data:', err);
      warnings.push('Failed to fetch supplier data');
      supplierSnapshot = {
        avg_lead_time_days: null,
        variability_level: null,
        record_count: 0,
      };
    }

    // ----------------------------------------
    // 4. ASSEMBLE RESPONSE
    // ----------------------------------------
    return {
      business_id: businessId,
      demand_snapshot: demandSnapshot,
      warehouse_snapshot: warehouseSnapshot,
      supplier_snapshot: supplierSnapshot,
      data_freshness: {
        sales_days_ago: salesFreshness,
        warehouse_days_ago: warehouseFreshness,
        supplier_days_ago: supplierFreshness,
      },
      warnings: warnings.length > 0 ? warnings : null,
      generated_at: now.toISOString(),
    };
  }
}

module.exports = new DataService();
