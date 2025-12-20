const express = require('express');
const router = express.Router();
const agentService = require('../services/agentService');

/**
 * @route   GET /api/health
 * @desc    Health check for the backend and agent service
 */
router.get('/health', async (req, res) => {
  try {
    const agentHealth = await agentService.healthCheck();
    res.json({
      backend: 'healthy',
      agentService: agentHealth,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.json({
      backend: 'healthy',
      agentService: 'unavailable',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

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

module.exports = router;
