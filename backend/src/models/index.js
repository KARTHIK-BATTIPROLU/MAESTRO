/**
 * MAESTRO Models Index
 * 
 * Central export point for all Mongoose models.
 * 
 * Usage:
 *   const { DailySales, WarehouseSnapshot, SupplierDelivery, DecisionSnapshot } = require('./models');
 */

const { DailySales, dailySalesSchema } = require('./DailySales');
const { WarehouseSnapshot, warehouseSnapshotSchema, STORAGE_TYPES } = require('./WarehouseSnapshot');
const { SupplierDelivery, supplierDeliverySchema } = require('./SupplierDelivery');
const { DecisionSnapshot, decisionSnapshotSchema } = require('./DecisionSnapshot');

module.exports = {
  // Models
  DailySales,
  WarehouseSnapshot,
  SupplierDelivery,
  DecisionSnapshot,
  
  // Schemas (for embedding or extending)
  dailySalesSchema,
  warehouseSnapshotSchema,
  supplierDeliverySchema,
  decisionSnapshotSchema,
  
  // Constants
  STORAGE_TYPES,
};
