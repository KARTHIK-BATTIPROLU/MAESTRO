import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for agent processing
});

// API service functions
export const apiService = {
  // Health check
  async healthCheck() {
    const response = await api.get('/api/health');
    return response.data;
  },

  // Get all onboarding questions
  async getQuestions() {
    const response = await api.get('/api/questions');
    return response.data;
  },

  // Start a new onboarding session
  async startOnboarding(userId = null) {
    const response = await api.post('/api/start-onboarding', { userId });
    return response.data;
  },

  // Submit user response to current question
  async sendUserResponse(sessionId, answer) {
    const response = await api.post('/api/send-user-response', {
      sessionId,
      answer,
    });
    return response.data;
  },

  // Process user data through agent pipeline
  async processWithAgents(sessionId) {
    const response = await api.post('/api/process', { sessionId });
    return response.data;
  },

  // Get agent output/results
  async getAgentOutput(sessionId) {
    const response = await api.get(`/api/get-agent-output/${sessionId}`);
    return response.data;
  },

  // Get session details
  async getSession(sessionId) {
    const response = await api.get(`/api/session/${sessionId}`);
    return response.data;
  },
};

/**
 * Run inventory decision using deterministic pipeline
 * 
 * Calls the backend which forwards to FastAPI agent service.
 * No LLM calls - pure rule-based decision engine.
 * 
 * @param {Object} payload - Inventory decision request
 * @param {string} payload.demand_type - "steady" | "seasonal" | "volatile"
 * @param {boolean} payload.seasonal_event - Whether seasonal event is expected
 * @param {string} payload.supplier_delay - "none" | "minor" | "frequent" | "major"
 * @param {boolean} payload.external_disruption - Whether external disruption exists
 * @param {number} payload.current_stock - Current inventory level (units)
 * @param {number} payload.max_capacity - Maximum warehouse capacity (units)
 * @param {string} payload.cash_flow - "healthy" | "tight" | "critical"
 * @returns {Promise<Object>} Decision response with final_decision, explanation, confidence
 * @throws {Error} If request fails
 */
export async function runInventoryDecision(payload) {
  try {
    const response = await api.post('/api/inventory-decision', payload);
    return response.data;
  } catch (error) {
    // Extract meaningful error message
    const errorMessage = error.response?.data?.error 
      || error.response?.data?.message 
      || error.message 
      || 'Failed to run inventory decision';
    throw new Error(errorMessage);
  }
}

export default apiService;
