import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import { runInventoryDecision } from '../services/api';

/**
 * MAESTRO Production Dashboard
 * 
 * Displays the output from the 5-agent pipeline:
 * - What We Understood
 * - Detected Risks
 * - Recommendation
 * - Why This Decision
 * - Immediate Actions
 */
const DashboardPage = () => {
  const location = useLocation();
  const [businessName, setBusinessName] = useState('Your Business');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // State for deterministic decision API response
  const [decisionResult, setDecisionResult] = useState(null);
  
  // Get results from navigation state or localStorage
  const [results, setResults] = useState(() => {
    // Try to get from navigation state first
    if (location.state?.results) {
      return location.state.results;
    }
    // Try localStorage
    const stored = localStorage.getItem('maestro_results');
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        console.error('Failed to parse stored results');
      }
    }
    // Return mock data for demo
    return getMockResults();
  });

  useEffect(() => {
    const stored = localStorage.getItem('maestro_business');
    if (stored) setBusinessName(stored);
  }, []);

  /**
   * Handle running the inventory decision API
   * Uses a sample payload for testing
   */
  const handleRunDecision = async () => {
    setIsLoading(true);
    setError(null);
    
    // Sample payload for testing
    const samplePayload = {
      demand_type: 'seasonal',
      seasonal_event: true,
      supplier_delay: 'frequent',
      external_disruption: false,
      current_stock: 60,
      max_capacity: 100,
      cash_flow: 'tight'
    };
    
    try {
      const result = await runInventoryDecision(samplePayload);
      setDecisionResult(result);
    } catch (err) {
      setError(err.message || 'Failed to run inventory decision');
    } finally {
      setIsLoading(false);
    }
  };

  // Extract data from results
  const data = results?.result || results || getMockResults().result;
  const finalDecision = data.final_decision || {};
  const whatWeUnderstood = data.what_we_understood || {};
  const detectedRisks = data.detected_risks || [];
  const recommendation = data.recommendation || {};
  const whyThisDecision = data.why_this_decision || '';
  const immediateActions = data.immediate_actions || [];
  const warnings = data.warnings || [];

  const getRiskColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-500';
      case 'HIGH': return 'bg-orange-500';
      case 'MODERATE': return 'bg-amber-500';
      case 'LOW': return 'bg-emerald-500';
      default: return 'bg-gray-500';
    }
  };

  const getRiskBgColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-500/10 border-red-500/30';
      case 'HIGH': return 'bg-orange-500/10 border-orange-500/30';
      case 'MODERATE': return 'bg-amber-500/10 border-amber-500/30';
      case 'LOW': return 'bg-emerald-500/10 border-emerald-500/30';
      default: return 'bg-gray-500/10 border-gray-500/30';
    }
  };

  const getTimingIcon = (timing) => {
    switch (timing?.toUpperCase()) {
      case 'EARLY': return '⚡';
      case 'NORMAL': return '📅';
      case 'DELAYED': return '⏰';
      default: return '📋';
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <header className="bg-[#12121a] border-b border-cyan-500/20 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-cyan-600 rounded-lg flex items-center justify-center">
              <span className="text-xl">🎯</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-cyan-400">MAESTRO</h1>
              <p className="text-xs text-gray-400">Inventory Intelligence System</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-400">Analysis Complete</span>
            </div>
            <div className="px-4 py-2 bg-[#1a1a2e] rounded-lg border border-cyan-500/20">
              <span className="text-sm text-gray-300">{businessName}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="p-6 max-w-7xl mx-auto">
        
        {/* ========================================= */}
        {/* DETERMINISTIC DECISION TEST SECTION */}
        {/* ========================================= */}
        <div className="mb-6 p-6 bg-[#12121a] rounded-xl border border-cyan-500/20">
          <h3 className="text-lg font-semibold text-white mb-4">🧪 Test Inventory Decision API</h3>
          
          {/* Run Button */}
          <button
            onClick={handleRunDecision}
            disabled={isLoading}
            className="px-6 py-3 bg-cyan-500 hover:bg-cyan-600 disabled:bg-gray-600 text-white rounded-lg font-medium transition-colors"
          >
            {isLoading ? 'Running...' : 'Run Inventory Decision'}
          </button>
          
          {/* Loading State */}
          {isLoading && (
            <div className="mt-4 text-gray-400">Processing decision...</div>
          )}
          
          {/* Error State */}
          {error && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              Error: {error}
            </div>
          )}
          
          {/* Result Display */}
          {decisionResult && !isLoading && (
            <div className="mt-4 space-y-4">
              <div className="text-sm text-gray-400">API Response:</div>
              
              {/* Final Decision */}
              <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                <div className="text-cyan-400 font-medium mb-2">Final Decision</div>
                <div className="space-y-2 text-white">
                  <div><span className="text-gray-400">Reorder Timing:</span> {decisionResult.final_decision?.reorder_timing}</div>
                  <div><span className="text-gray-400">Order Strategy:</span> {decisionResult.final_decision?.order_strategy}</div>
                  <div><span className="text-gray-400">Risk Level:</span> {decisionResult.final_decision?.risk_level}</div>
                </div>
              </div>
              
              {/* Explanation */}
              <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                <div className="text-cyan-400 font-medium mb-2">Explanation</div>
                <div className="text-white">{decisionResult.explanation}</div>
              </div>
              
              {/* Confidence */}
              <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                <div className="text-cyan-400 font-medium mb-2">Confidence</div>
                <div className="text-white text-2xl font-bold">
                  {Math.round((decisionResult.confidence || 0) * 100)}%
                </div>
              </div>
              
              {/* Risk Profile (if available) */}
              {decisionResult.risk_profile && (
                <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                  <div className="text-cyan-400 font-medium mb-2">Risk Profile</div>
                  <div className="grid grid-cols-2 gap-2 text-white">
                    <div><span className="text-gray-400">Demand Risk:</span> {(decisionResult.risk_profile.demand_risk * 100).toFixed(0)}%</div>
                    <div><span className="text-gray-400">Supplier Risk:</span> {(decisionResult.risk_profile.supplier_risk * 100).toFixed(0)}%</div>
                    <div><span className="text-gray-400">Warehouse Stress:</span> {(decisionResult.risk_profile.warehouse_stress * 100).toFixed(0)}%</div>
                    <div><span className="text-gray-400">Cash Risk:</span> {(decisionResult.risk_profile.cash_risk * 100).toFixed(0)}%</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        {/* ========================================= */}
        {/* END DETERMINISTIC DECISION TEST SECTION */}
        {/* ========================================= */}
        
        {/* Top Section: Final Decision Banner */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-6 p-6 rounded-xl border ${getRiskBgColor(finalDecision.risk_level)}`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-4xl">{getTimingIcon(finalDecision.reorder_timing)}</div>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-white">
                    Reorder {finalDecision.reorder_timing || 'EARLY'}
                  </h2>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(finalDecision.risk_level)} text-white`}>
                    {finalDecision.risk_level || 'MODERATE'} RISK
                  </span>
                </div>
                <p className="text-gray-300 mt-1">{finalDecision.order_strategy}</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">Confidence</div>
              <div className="text-2xl font-bold text-cyan-400">
                {Math.round((finalDecision.confidence || 0.82) * 100)}%
              </div>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-12 gap-6">
          
          {/* Left Column: What We Understood */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="col-span-4"
          >
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5 h-full">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-cyan-400">📋</span> What We Understood
              </h3>
              
              <div className="space-y-4">
                <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                  <div className="text-sm text-gray-400 mb-1">Demand Situation</div>
                  <div className="text-white">{whatWeUnderstood.demand_situation}</div>
                </div>
                
                <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                  <div className="text-sm text-gray-400 mb-1">Supplier Situation</div>
                  <div className="text-white">{whatWeUnderstood.supplier_situation}</div>
                </div>
                
                <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                  <div className="text-sm text-gray-400 mb-1">Warehouse Situation</div>
                  <div className="text-white">{whatWeUnderstood.warehouse_situation}</div>
                </div>
                
                <div className="p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
                  <div className="text-sm text-amber-400 mb-1">Key Constraint</div>
                  <div className="text-white font-medium">{whatWeUnderstood.key_constraint}</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Center Column: Detected Risks & Recommendation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="col-span-5 space-y-6"
          >
            {/* Detected Risks */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-cyan-400">⚠️</span> Detected Risks
              </h3>
              
              <div className="space-y-3">
                {detectedRisks.map((risk, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + index * 0.1 }}
                    className={`p-4 rounded-lg border ${getRiskBgColor(risk.level)}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="font-medium text-white">{risk.risk}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskColor(risk.level)} text-white`}>
                        {risk.level}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300">{risk.explanation}</p>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Recommendation */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-cyan-400">✅</span> Recommendation
              </h3>
              
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 rounded-lg border border-cyan-500/20">
                  <div className="text-2xl mb-2">📅</div>
                  <div className="text-sm text-gray-400 mb-1">When to Reorder</div>
                  <div className="text-white font-medium">{recommendation.timing}</div>
                </div>
                
                <div className="p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 rounded-lg border border-cyan-500/20">
                  <div className="text-2xl mb-2">📦</div>
                  <div className="text-sm text-gray-400 mb-1">How Much</div>
                  <div className="text-white font-medium">{recommendation.quantity}</div>
                </div>
                
                <div className="p-4 bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 rounded-lg border border-cyan-500/20">
                  <div className="text-2xl mb-2">🚚</div>
                  <div className="text-sm text-gray-400 mb-1">How to Manage</div>
                  <div className="text-white font-medium">{recommendation.method}</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right Column: Why & Actions */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="col-span-3 space-y-6"
          >
            {/* Why This Decision */}
            <div className="bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 rounded-xl border border-cyan-500/30 p-5">
              <h3 className="text-lg font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                <span>💡</span> Why This Decision
              </h3>
              <p className="text-gray-200 leading-relaxed">{whyThisDecision}</p>
            </div>

            {/* Immediate Actions */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-cyan-400">🎯</span> Immediate Actions
              </h3>
              
              <div className="space-y-3">
                {immediateActions.map((action, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + index * 0.1 }}
                    className="flex items-start gap-3 p-3 bg-[#1a1a2e] rounded-lg border border-cyan-500/10"
                  >
                    <div className="w-6 h-6 bg-cyan-500 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold">
                      {index + 1}
                    </div>
                    <span className="text-gray-200">{action}</span>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Warnings */}
            {warnings.length > 0 && (
              <div className="bg-red-500/10 rounded-xl border border-red-500/30 p-5">
                <h3 className="text-lg font-semibold text-red-400 mb-3 flex items-center gap-2">
                  <span>⚠️</span> Warnings
                </h3>
                <ul className="space-y-2">
                  {warnings.map((warning, index) => (
                    <li key={index} className="text-red-200 text-sm flex items-start gap-2">
                      <span>•</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        </div>

        {/* Footer Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-8 flex justify-center gap-4"
        >
          <button className="px-8 py-3 bg-cyan-500 hover:bg-cyan-600 text-white rounded-xl font-medium transition-colors flex items-center gap-2">
            <span>✓</span> Accept Recommendation
          </button>
          <button className="px-8 py-3 bg-[#1a1a2e] border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 rounded-xl font-medium transition-colors flex items-center gap-2">
            <span>🔄</span> Run New Analysis
          </button>
          <button className="px-8 py-3 bg-[#1a1a2e] border border-gray-600 text-gray-400 hover:bg-gray-800 rounded-xl font-medium transition-colors flex items-center gap-2">
            <span>📊</span> Export Report
          </button>
        </motion.div>
      </div>
    </div>
  );
};

// Mock results for demo/testing
function getMockResults() {
  return {
    result: {
      final_decision: {
        reorder_timing: "EARLY",
        order_strategy: "Split orders into weekly deliveries to manage limited storage",
        risk_level: "MODERATE",
        confidence: 0.82
      },
      what_we_understood: {
        demand_situation: "Your demand shows moderate seasonal variation with festival-driven spikes",
        supplier_situation: "Suppliers have occasional delays of 2-5 days, requiring buffer time",
        warehouse_situation: "Storage space is limited, preventing bulk order strategies",
        key_constraint: "Warehouse capacity limits bulk ordering potential"
      },
      detected_risks: [
        {
          risk: "Seasonal Demand Spike",
          level: "MODERATE",
          explanation: "Upcoming festival season may increase demand by 30-40%, requiring preparation"
        },
        {
          risk: "Supplier Lead Time Variability",
          level: "MODERATE",
          explanation: "Variable delivery times of 2-5 days require safety buffer in ordering"
        },
        {
          risk: "Storage Capacity Constraint",
          level: "HIGH",
          explanation: "Limited warehouse space prevents bulk ordering and requires frequent smaller orders"
        }
      ],
      recommendation: {
        timing: "Reorder 7-10 days earlier than usual",
        quantity: "Order 20% less per order, but order twice as frequently",
        method: "Set up weekly delivery schedule with your supplier"
      },
      why_this_decision: "Your storage constraints limit bulk ordering, while supplier delays and seasonal demand require earlier reordering. Splitting orders into smaller, weekly deliveries balances these factors while maintaining stock availability and managing cash flow.",
      immediate_actions: [
        "Calculate your weekly consumption for top 5 products today",
        "Contact your supplier to arrange a weekly delivery schedule",
        "Set up reorder alerts for 7 days before your usual timing",
        "Clear slow-moving stock to free up 15-20% more storage space"
      ],
      warnings: [
        "Watch for transport disruptions during upcoming festival season"
      ]
    }
  };
}

export default DashboardPage;
