/**
 * MAESTRO Context Aggregator
 * 
 * Converts 10 onboarding question answers into a structured,
 * personalized MSME operational context.
 * 
 * This context preserves the MSME's actual pain points and constraints,
 * derived ONLY from their answers (no generic assumptions).
 * 
 * It serves as the SINGLE SOURCE OF TRUTH for all downstream agents.
 */

/**
 * Aggregate onboarding answers into operational context
 * 
 * @param {Object} answers - Raw answers from 10-question onboarding
 * @returns {Object} Aggregated MSME operational context
 */
export function aggregateContext(answers) {
  if (!answers || typeof answers !== 'object') {
    return buildDefaultContext();
  }

  return {
    business_identity: extractBusinessIdentity(answers),
    inventory_behavior: extractInventoryBehavior(answers),
    demand_characteristics: extractDemandCharacteristics(answers),
    supplier_realities: extractSupplierRealities(answers),
    warehouse_constraints: extractWarehouseConstraints(answers),
    financial_pressure: extractFinancialPressure(answers),
    system_gaps: extractSystemGaps(answers),
    owner_priority: extractOwnerPriority(answers),
  };
}

/**
 * Extract business identity from Q1 answer
 * Q1: Business description (industry, products, scale)
 */
function extractBusinessIdentity(answers) {
  const q1 = answers.q1 || answers.question_1 || '';
  
  return {
    raw_answer: q1,
    description: q1,
    inferred: {
      is_seasonal_industry: detectSeasonalIndustry(q1),
      is_perishable_goods: detectPerishableGoods(q1),
      is_high_velocity: detectHighVelocity(q1),
    },
  };
}

/**
 * Extract inventory behavior from Q2 and Q3 answers
 * Q2: Current reorder method
 * Q3: Stockouts vs overstock history
 */
function extractInventoryBehavior(answers) {
  const q2 = answers.q2 || answers.question_2 || '';
  const q3 = answers.q3 || answers.question_3 || '';
  
  return {
    current_method: q2,
    health_history: q3,
    inferred: {
      maturity_level: assessMaturity(q2),
      has_stockout_pain: hasStockoutPain(q3),
      has_overstock_pain: hasOverstockPain(q3),
      historical_issues: q3,
    },
  };
}

/**
 * Extract demand characteristics from Q4 and Q5 answers
 * Q4: Demand variability (steady/seasonal/volatile)
 * Q5: Seasonal events expected
 */
function extractDemandCharacteristics(answers) {
  const q4 = answers.q4 || answers.question_4 || 'steady';
  const q5 = answers.q5 || answers.question_5 || 'false';
  
  const demandType = normalizeDemandType(q4);
  const hasSeasonalEvent = parseBooleanAnswer(q5);
  
  return {
    demand_type: demandType,
    seasonal_event: hasSeasonalEvent,
    raw_answer: q4,
    inferred: {
      risk_level: demandToRisk(demandType),
      requires_buffer_stock: demandType === 'volatile' || hasSeasonalEvent,
      planning_horizon: demandType === 'volatile' ? 'short' : 'medium',
    },
  };
}

/**
 * Extract supplier realities from Q4 answer
 * Q4: Supplier reliability & delays
 */
function extractSupplierRealities(answers) {
  const q4_supplier = answers.q4_supplier || answers.question_4 || 'reliable';
  
  const delayLevel = normalizeSupplierDelay(q4_supplier);
  
  return {
    delay_category: delayLevel,
    raw_answer: q4_supplier,
    inferred: {
      lead_time_risk: delayToRisk(delayLevel),
      needs_early_ordering: delayLevel !== 'none',
      buffer_days: delayToBufferDays(delayLevel),
    },
  };
}

/**
 * Extract warehouse constraints from Q7 answer
 * Q7: Warehouse constraints and capacity stress
 */
function extractWarehouseConstraints(answers) {
  const q7 = answers.q7 || answers.question_7 || '';
  
  return {
    constraints: q7,
    inferred: {
      is_constrained: detectWareouseConstraint(q7),
      limits_bulk_ordering: detectWareouseConstraint(q7),
      requires_frequent_orders: detectWareouseConstraint(q7),
      stress_level: assessWarehouseStress(q7),
    },
  };
}

/**
 * Extract financial pressure from Q8 answer
 * Q8: Cash flow impact and financial sensitivity
 */
function extractFinancialPressure(answers) {
  const q8 = answers.q8 || answers.question_8 || 'healthy';
  
  const flowStatus = normalizeCashFlow(q8);
  
  return {
    cash_flow_status: flowStatus,
    raw_answer: q8,
    inferred: {
      has_cash_constraints: flowStatus !== 'healthy',
      prefers_frequent_small_orders: flowStatus === 'tight' || flowStatus === 'critical',
      risk_level: cashFlowToRisk(flowStatus),
    },
  };
}

/**
 * Extract system gaps from Q9 answer
 * Q9: Tool/system limitations and readiness
 */
function extractSystemGaps(answers) {
  const q9 = answers.q9 || answers.question_9 || '';
  
  return {
    current_limitations: q9,
    inferred: {
      needs_automation: q9.length > 0,
      is_manual_process: detectManualProcess(q9),
      data_quality_concern: detectDataQualityConcern(q9),
    },
  };
}

/**
 * Extract owner priority from Q10 answer
 * Q10: Desired outcome and priority
 */
function extractOwnerPriority(answers) {
  const q10 = answers.q10 || answers.question_10 || '';
  
  return {
    priority: q10,
    inferred: {
      focus_area: detectPriorityFocus(q10),
      urgency: assessUrgency(q10),
    },
  };
}

/**
 * Derive inventory decision payload from context
 * 
 * Maps aggregated context to the inventory-decision API payload
 * 
 * @param {Object} context - Aggregated MSME context
 * @returns {Object} Payload for /api/inventory-decision
 */
export function deriveDecisionPayload(context) {
  if (!context) {
    return buildDefaultPayload();
  }

  return {
    demand_type: context.demand_characteristics?.demand_type || 'steady',
    seasonal_event: context.demand_characteristics?.seasonal_event || false,
    supplier_delay: context.supplier_realities?.delay_category || 'none',
    external_disruption: context.owner_priority?.inferred?.urgency === 'high' || false,
    current_stock: 50, // Safe default: mid-range
    max_capacity: 100, // Safe default: normalized
    cash_flow: context.financial_pressure?.cash_flow_status || 'healthy',
  };
}

// ============================================================================
// HELPER FUNCTIONS — Detection & Classification
// ============================================================================

function detectSeasonalIndustry(text) {
  const keywords = ['seasonal', 'festival', 'holiday', 'weather', 'climate'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectPerishableGoods(text) {
  const keywords = ['perishable', 'fresh', 'dairy', 'grocery', 'food', 'vegetable', 'fruit'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectHighVelocity(text) {
  const keywords = ['fast-moving', 'fast moving', 'high turnover', 'daily', 'hourly'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function hasStockoutPain(text) {
  const keywords = ['stockout', 'stock out', 'ran out', 'out of stock', 'unavailable'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function hasOverstockPain(text) {
  const keywords = ['overstock', 'over stock', 'excess', 'too much', 'waste', 'expired'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectWareouseConstraint(text) {
  const keywords = ['limited', 'constraint', 'tight', 'small', 'constrained', 'space'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectManualProcess(text) {
  const keywords = ['manual', 'spreadsheet', 'pen', 'paper', 'notebook'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectDataQualityConcern(text) {
  const keywords = ['accurate', 'reliable', 'track', 'visibility', 'data', 'records'];
  return keywords.some(k => text.toLowerCase().includes(k));
}

function detectPriorityFocus(text) {
  if (text.toLowerCase().includes('reduce stockout') || text.toLowerCase().includes('avoid runout')) {
    return 'availability';
  }
  if (text.toLowerCase().includes('reduce waste') || text.toLowerCase().includes('reduce overstock')) {
    return 'efficiency';
  }
  if (text.toLowerCase().includes('cash') || text.toLowerCase().includes('money')) {
    return 'cash_flow';
  }
  return 'balance';
}

function assessUrgency(text) {
  return text.length > 30 ? 'high' : 'normal';
}

function assessMaturity(text) {
  if (text.toLowerCase().includes('system') || text.toLowerCase().includes('software')) {
    return 'advanced';
  }
  if (text.toLowerCase().includes('manual') || text.toLowerCase().includes('spreadsheet')) {
    return 'basic';
  }
  return 'developing';
}

function assessWarehouseStress(text) {
  if (text.toLowerCase().includes('very limited') || text.toLowerCase().includes('severely')) {
    return 'high';
  }
  if (text.toLowerCase().includes('limited') || text.toLowerCase().includes('constraint')) {
    return 'moderate';
  }
  return 'low';
}

// ============================================================================
// NORMALIZATION FUNCTIONS
// ============================================================================

function normalizeDemandType(text) {
  const lower = text.toLowerCase();
  if (lower.includes('volatile') || lower.includes('unpredictable')) return 'volatile';
  if (lower.includes('seasonal')) return 'seasonal';
  return 'steady';
}

function normalizeSupplierDelay(text) {
  const lower = text.toLowerCase();
  if (lower.includes('major') || lower.includes('significant') || lower.includes('very delayed')) {
    return 'major';
  }
  if (lower.includes('frequent') || lower.includes('often')) {
    return 'frequent';
  }
  if (lower.includes('minor') || lower.includes('sometimes')) {
    return 'minor';
  }
  return 'none';
}

function normalizeCashFlow(text) {
  const lower = text.toLowerCase();
  if (lower.includes('critical') || lower.includes('blocked') || lower.includes('no cash')) {
    return 'critical';
  }
  if (lower.includes('tight') || lower.includes('limited') || lower.includes('constrained')) {
    return 'tight';
  }
  return 'healthy';
}

function parseBooleanAnswer(text) {
  if (typeof text === 'boolean') return text;
  const lower = String(text).toLowerCase();
  return lower === 'yes' || lower === 'true' || lower === '1';
}

// ============================================================================
// RISK MAPPING FUNCTIONS
// ============================================================================

function demandToRisk(demandType) {
  switch (demandType) {
    case 'volatile':
      return 0.8;
    case 'seasonal':
      return 0.6;
    default:
      return 0.2;
  }
}

function delayToRisk(delayLevel) {
  switch (delayLevel) {
    case 'major':
      return 0.8;
    case 'frequent':
      return 0.6;
    case 'minor':
      return 0.3;
    default:
      return 0.1;
  }
}

function delayToBufferDays(delayLevel) {
  switch (delayLevel) {
    case 'major':
      return 14;
    case 'frequent':
      return 7;
    case 'minor':
      return 3;
    default:
      return 0;
  }
}

function cashFlowToRisk(flowStatus) {
  switch (flowStatus) {
    case 'critical':
      return 0.9;
    case 'tight':
      return 0.7;
    default:
      return 0.2;
  }
}

// ============================================================================
// DEFAULT BUILDERS
// ============================================================================

function buildDefaultContext() {
  return {
    business_identity: { raw_answer: '', description: '', inferred: {} },
    inventory_behavior: { current_method: '', health_history: '', inferred: {} },
    demand_characteristics: { demand_type: 'steady', seasonal_event: false, inferred: {} },
    supplier_realities: { delay_category: 'none', inferred: {} },
    warehouse_constraints: { constraints: '', inferred: {} },
    financial_pressure: { cash_flow_status: 'healthy', inferred: {} },
    system_gaps: { current_limitations: '', inferred: {} },
    owner_priority: { priority: '', inferred: {} },
  };
}

function buildDefaultPayload() {
  return {
    demand_type: 'steady',
    seasonal_event: false,
    supplier_delay: 'none',
    external_disruption: false,
    current_stock: 50,
    max_capacity: 100,
    cash_flow: 'healthy',
  };
}

export default {
  aggregateContext,
  deriveDecisionPayload,
};
