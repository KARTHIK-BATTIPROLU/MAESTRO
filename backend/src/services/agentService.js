const axios = require('axios');
const config = require('../config');
const dataService = require('./dataService');
const { retryWithBackoff, agentServiceCircuit } = require('./resilience');

/**
 * Agent Service Client
 * Handles communication with the CrewAI Python service
 */
class AgentServiceClient {
  constructor() {
    this.baseUrl = config.agentServiceUrl;
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 300000, // 5 minutes for agent processing
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  /**
   * Health check for agent service (with circuit breaker awareness)
   */
  async healthCheck() {
    try {
      const response = await retryWithBackoff(
        () => this.client.get('/health'),
        { maxAttempts: 2, baseDelayMs: 500, circuit: agentServiceCircuit }
      );
      return {
        ...response.data,
        circuit: agentServiceCircuit.toHealth(),
      };
    } catch (error) {
      return {
        status: 'unavailable',
        error: error.message,
        circuit: agentServiceCircuit.toHealth(),
      };
    }
  }

  /**
   * Get all onboarding questions
   */
  async getQuestions() {
    try {
      const response = await this.client.get('/questions');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get questions: ${error.message}`);
    }
  }

  /**
   * Start a new onboarding session
   */
  async startSession(userId = null) {
    try {
      const response = await this.client.post('/start-session', {
        user_id: userId
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to start session: ${error.message}`);
    }
  }

  /**
   * Submit a user response
   */
  async submitResponse(sessionId, answer) {
    try {
      const response = await this.client.post('/respond', {
        session_id: sessionId,
        answer: answer
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to submit response: ${error.message}`);
    }
  }

  /**
   * Process user data through agents
   */
  async processWithAgents(sessionId) {
    try {
      const response = await this.client.post('/process', {
        session_id: sessionId
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to process with agents: ${error.message}`);
    }
  }

  /**
   * Get session details
   */
  async getSession(sessionId) {
    try {
      const response = await this.client.get(`/session/${sessionId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get session: ${error.message}`);
    }
  }

  /**
   * Get processing results
   */
  async getResults(sessionId) {
    try {
      const response = await this.client.get(`/session/${sessionId}/results`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get results: ${error.message}`);
    }
  }

  /**
   * Call the deterministic inventory decision agent
   * 
   * Sends business inputs to the FastAPI service and receives
   * a structured inventory decision without LLM calls.
   * 
   * NOW ENHANCED: Fetches live business state from MongoDB and 
   * attaches it to the agent payload for data-driven decisions.
   * 
   * @param {Object} payload - Inventory decision request
   * @param {string} payload.demand_type - "steady" | "seasonal" | "volatile"
   * @param {boolean} payload.seasonal_event - Whether seasonal event is expected
   * @param {string} payload.supplier_delay - "none" | "minor" | "frequent" | "major"
   * @param {boolean} payload.external_disruption - Whether external disruption exists
   * @param {number} payload.current_stock - Current inventory level (units) - OPTIONAL if business_state available
   * @param {number} payload.max_capacity - Maximum warehouse capacity (units) - OPTIONAL if business_state available
   * @param {string} payload.cash_flow - "healthy" | "tight" | "critical"
   * @param {string} payload.business_id - Business ID for fetching live data (optional)
   * @returns {Promise<Object>} Decision response with final_decision, explanation, confidence
   * @throws {Error} Descriptive error if request fails
   */
  async callInventoryDecisionAgent(payload) {
    try {
      // ========================================
      // FETCH LIVE BUSINESS STATE
      // ========================================
      let businessState = null;
      const businessId = payload.business_id || 'demo-business';
      
      try {
        console.log(`📊 Fetching live business state for: ${businessId}`);
        businessState = await dataService.getBusinessState(businessId);
        console.log('✅ Business state retrieved:', {
          hasDemandData: businessState.demand_snapshot?.record_count > 0,
          hasWarehouseData: businessState.warehouse_snapshot?.current_stock !== null,
          hasSupplierData: businessState.supplier_snapshot?.record_count > 0,
        });
      } catch (stateError) {
        console.warn('⚠️ Could not fetch business state, using payload defaults:', stateError.message);
      }
      
      // ========================================
      // BUILD ENHANCED PAYLOAD
      // ========================================
      const enhancedPayload = {
        ...payload,
        business_state: businessState,
      };
      
      // POST to the deterministic decision endpoint (with retry + circuit breaker)
      const response = await retryWithBackoff(
        () => this.client.post('/process-inventory-decision', enhancedPayload),
        { maxAttempts: 3, baseDelayMs: 1000, circuit: agentServiceCircuit }
      );
      
      // Return the response data directly (no transformation)
      return response.data;
    } catch (error) {
      // Extract meaningful error message
      const errorMessage = error.response?.data?.detail 
        || error.response?.data?.message 
        || error.message 
        || 'Unknown error calling inventory decision agent';
      
      throw new Error(`Inventory decision agent failed: ${errorMessage}`);
    }
  }
}

module.exports = new AgentServiceClient();
