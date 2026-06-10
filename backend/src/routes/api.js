const express = require('express');
const router = express.Router();
const agentService = require('../services/agentService');
const { agentServiceCircuit } = require('../services/resilience');
const dataRoutes = require('./dataRoutes');
const { DecisionSnapshot } = require('../models');

// Note: /api/health is handled in server.js directly for lightweight uptime monitoring

/**
 * @route   GET /api/questions
 * @desc    Get all onboarding questions
 */
router.get('/questions', async (req, res) => {
  try {
    const questions = await agentService.getQuestions();
    res.json(questions);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @route   POST /api/start-onboarding
 * @desc    Start a new onboarding session
 */
router.post('/start-onboarding', async (req, res) => {
  try {
    const { userId } = req.body;
    const session = await agentService.startSession(userId);
    res.json({
      success: true,
      ...session
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

/**
 * @route   POST /api/send-user-response
 * @desc    Submit user response to current question
 */
router.post('/send-user-response', async (req, res) => {
  try {
    const { sessionId, answer } = req.body;
    
    if (!sessionId || !answer) {
      return res.status(400).json({
        success: false,
        error: 'sessionId and answer are required'
      });
    }
    
    const response = await agentService.submitResponse(sessionId, answer);
    res.json({
      success: true,
      ...response
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

/**
 * @route   POST /api/process
 * @desc    Process user data through agent pipeline
 */
router.post('/process', async (req, res) => {
  try {
    const { sessionId } = req.body;
    
    if (!sessionId) {
      return res.status(400).json({
        success: false,
        error: 'sessionId is required'
      });
    }
    
    const results = await agentService.processWithAgents(sessionId);
    res.json({
      success: true,
      ...results
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

/**
 * @route   GET /api/get-agent-output/:sessionId
 * @desc    Get the agent processing results
 */
router.get('/get-agent-output/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const results = await agentService.getResults(sessionId);
    res.json({
      success: true,
      ...results
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

/**
 * @route   GET /api/session/:sessionId
 * @desc    Get session details
 */
router.get('/session/:sessionId', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const session = await agentService.getSession(sessionId);
    res.json({
      success: true,
      ...session
    });
  } catch (error) {
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
});

/**
 * @route   POST /api/inventory-decision
 * @desc    Process inventory decision using deterministic rule-based pipeline
 * 
 * This endpoint forwards the request to the FastAPI agent service
 * which runs the MAESTRO decision engine WITHOUT LLM calls.
 * 
 * Request Body:
 *   - demand_type: "steady" | "seasonal" | "volatile"
 *   - seasonal_event: boolean
 *   - supplier_delay: "none" | "minor" | "frequent" | "major"
 *   - external_disruption: boolean
 *   - current_stock: number (units)
 *   - max_capacity: number (units)
 *   - cash_flow: "healthy" | "tight" | "critical"
 * 
 * Response:
 *   - success: boolean
 *   - final_decision: { reorder_timing, order_strategy, risk_level }
 *   - explanation: string
 *   - confidence: number (0.0-1.0)
 *   - risk_profile: object
 */
router.post('/inventory-decision', async (req, res) => {
  try {
    // Forward request body directly to agent service (no transformation)
    const result = await agentService.callInventoryDecisionAgent(req.body);
    
    // Save decision snapshot asynchronously (non-blocking)
    // Fire-and-forget: errors are logged but do not affect response
    saveDecisionSnapshot(req.body, result).catch(() => {});
    
    // Return response directly from agent service
    res.json(result);
  } catch (error) {
    // Return safe error message on failure
    res.status(500).json({
      success: false,
      error: 'Failed to process inventory decision. Please try again.'
    });
  }
});

/**
 * Save decision snapshot to MongoDB (non-blocking)
 * 
 * @param {Object} requestBody - Original request payload
 * @param {Object} agentResult - Response from agent service
 */
async function saveDecisionSnapshot(requestBody, agentResult) {
  try {
    // Extract business_id from request (fallback to 'unknown')
    const business_id = requestBody.business_id || 
                        requestBody.businessId || 
                        'unknown';
    
    // Extract final_decision
    const decision = agentResult.final_decision || null;
    
    // Extract reorder_point (from final_decision or top-level)
    const reorder_point = decision?.reorder_point || 
                          agentResult.reorder_point || 
                          null;
    
    // Determine which data sources were used
    const context_used = {
      has_daily_sales: Boolean(requestBody.avg_daily_sales || requestBody.dailySales),
      has_warehouse_snapshot: Boolean(requestBody.current_stock || requestBody.max_capacity),
      has_supplier_data: Boolean(requestBody.effective_lead_time_days || requestBody.supplier_delay),
      has_business_state: Boolean(requestBody.business_state),
    };
    
    // Extract explanation fields
    const explanation = {
      what_we_understood: agentResult.what_we_understood || null,
      why_this_decision: agentResult.why_this_decision || 
                         agentResult.explanation || 
                         null,
    };
    
    // Save using static method (handles errors internally)
    await DecisionSnapshot.saveSnapshot({
      business_id,
      decision,
      reorder_point,
      context_used,
      explanation,
    });
  } catch (error) {
    // Silent log - never throw
    console.error(`⚠️ DecisionSnapshot save error (non-blocking): ${error.message}`);
  }
}

// ========================================
// DECISION HISTORY (Read-Only)
// ========================================

/**
 * @route   GET /api/decisions/:business_id
 * @desc    Fetch past inventory decision snapshots for a business
 * 
 * Query Params:
 *   - limit: Number of records (default 10, max 50)
 * 
 * Response:
 *   - success: boolean
 *   - count: number
 *   - decisions: Array of { created_at, decision, reorder_point, confidence }
 */
router.get('/decisions/:business_id', async (req, res) => {
  try {
    const { business_id } = req.params;
    
    // Parse and clamp limit
    let limit = parseInt(req.query.limit, 10) || 10;
    limit = Math.min(Math.max(limit, 1), 50); // Clamp to 1-50
    
    // Fetch snapshots sorted by created_at DESC
    const snapshots = await DecisionSnapshot.find({ business_id })
      .sort({ created_at: -1 })
      .limit(limit)
      .select('created_at decision reorder_point outcome')
      .lean();
    
    // Map to safe response fields
    const decisions = snapshots.map(snap => ({
      id: snap._id,
      created_at: snap.created_at,
      decision: snap.decision || null,
      reorder_point: snap.reorder_point || null,
      confidence: snap.decision?.confidence || null,
      outcome: snap.outcome || 'UNKNOWN',
    }));
    
    res.json({
      success: true,
      count: decisions.length,
      decisions,
    });
  } catch (error) {
    console.error(`❌ Error fetching decisions for ${req.params.business_id}: ${error.message}`);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch decision history.',
    });
  }
});

/**
 * @route   PATCH /api/decisions/:id/outcome
 * @desc    Update the outcome of a past decision
 * 
 * Idempotent: Safe for repeated calls with same outcome
 * No side effects: Only updates outcome field
 * No agent calls: Pure database operation
 * 
 * Body:
 *   - outcome: "GOOD" | "BAD" | "UNKNOWN"
 * 
 * Response:
 *   - success: boolean
 *   - outcome: string (updated value)
 * 
 * Errors:
 *   - 400: Invalid outcome or malformed ID
 *   - 404: Decision not found
 *   - 500: Database error
 */
router.patch('/decisions/:id/outcome', async (req, res) => {
  try {
    const { id } = req.params;
    const { outcome } = req.body;

    // Validate MongoDB ObjectId format
    if (!id || !id.match(/^[0-9a-fA-F]{24}$/)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid decision ID format.',
      });
    }

    // Validate outcome enum strictly
    const validOutcomes = ['GOOD', 'BAD', 'UNKNOWN'];
    if (!outcome || typeof outcome !== 'string' || !validOutcomes.includes(outcome)) {
      return res.status(400).json({
        success: false,
        error: `Invalid outcome. Must be one of: ${validOutcomes.join(', ')}`,
      });
    }

    // Update ONLY the outcome field (no other fields modified)
    const updated = await DecisionSnapshot.findByIdAndUpdate(
      id,
      { $set: { outcome } },  // Explicit $set for clarity
      { new: true, select: 'outcome', runValidators: true }
    );

    // 404 if decision not found
    if (!updated) {
      return res.status(404).json({
        success: false,
        error: 'Decision not found.',
      });
    }

    res.json({
      success: true,
      outcome: updated.outcome,
    });
  } catch (error) {
    console.error(`❌ Error updating decision outcome: ${error.message}`);
    res.status(500).json({
      success: false,
      error: 'Failed to update decision outcome.',
    });
  }
});

// ========================================
// DATA ROUTES (Operational Data APIs)
// ========================================

/**
 * Mount data routes at /data prefix
 * Full paths will be /api/data/...
 * 
 * Available endpoints:
 *   POST /api/data/daily-sales
 *   GET  /api/data/daily-sales/:business_id
 *   POST /api/data/warehouse-snapshot
 *   GET  /api/data/warehouse/:business_id
 *   POST /api/data/supplier-delivery
 *   GET  /api/data/supplier-leadtime/:business_id
 */
router.use('/data', dataRoutes);

module.exports = router;
