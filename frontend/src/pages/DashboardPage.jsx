import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import { runInventoryDecision, apiService } from '../services/api';
import { aggregateContext, deriveDecisionPayload } from '../utils/contextAggregator';

/**
 * MAESTRO Production Dashboard
 * 
 * Loads MSME onboarding answers → Builds operational context → 
 * Derives personalized decision payload → Displays inventory recommendation
 */
const DashboardPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [businessName, setBusinessName] = useState('Your Business');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const [sessionId, setSessionId] = useState(null);
  
  // Onboarding answers from session (kept in state for context display)
  // eslint-disable-next-line no-unused-vars
  const [sessionAnswers, setSessionAnswers] = useState(null);
  
  // Aggregated context
  // eslint-disable-next-line no-unused-vars
  const [msmeContext, setMsmeContext] = useState(null);
  
  // Derived decision payload
  const [decisionPayload, setDecisionPayload] = useState(null);
  
  // API response
  const [decisionResult, setDecisionResult] = useState(null);

  // ========================================
  // DATA ENTRY FORM STATES
  // ========================================
  
  // Collapsible section states
  const [expandedSection, setExpandedSection] = useState(null);
  
  // Daily Sales Form
  const [dailySalesForm, setDailySalesForm] = useState({
    date: new Date().toISOString().split('T')[0],
    product_id: '',
    units_sold: '',
    revenue: '',
    closing_stock: '',
  });
  const [dailySalesLoading, setDailySalesLoading] = useState(false);
  const [dailySalesMessage, setDailySalesMessage] = useState(null);
  
  // Warehouse Snapshot Form
  const [warehouseForm, setWarehouseForm] = useState({
    date: new Date().toISOString().split('T')[0],
    current_stock: '',
    max_capacity: '',
    storage_type: 'dry',
    notes: '',
  });
  const [warehouseLoading, setWarehouseLoading] = useState(false);
  const [warehouseMessage, setWarehouseMessage] = useState(null);
  
  // Supplier Delivery Form
  const [supplierForm, setSupplierForm] = useState({
    supplier_id: '',
    product_id: '',
    order_date: '',
    delivery_date: new Date().toISOString().split('T')[0],
    quantity_received: '',
  });
  const [supplierLoading, setSupplierLoading] = useState(false);
  const [supplierMessage, setSupplierMessage] = useState(null);

  // ========================================
  // LIVE BUSINESS SNAPSHOT STATE
  // ========================================
  const [businessState, setBusinessState] = useState(null);
  const [businessStateLoading, setBusinessStateLoading] = useState(true);
  const [businessStateError, setBusinessStateError] = useState(null);

  // ========================================
  // DECISION HISTORY STATE
  // ========================================
  const [decisionHistory, setDecisionHistory] = useState([]);
  const [decisionHistoryLoading, setDecisionHistoryLoading] = useState(false);
  const [expandedHistoryItem, setExpandedHistoryItem] = useState(null);
  
  // Get results from navigation state or localStorage
  // eslint-disable-next-line no-unused-vars
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

  // ========================================
  // FETCH LIVE BUSINESS SNAPSHOT
  // ========================================
  useEffect(() => {
    const fetchBusinessState = async () => {
      try {
        setBusinessStateLoading(true);
        setBusinessStateError(null);
        
        const businessId = localStorage.getItem('maestro_business_id') || 'demo-business';
        const response = await apiService.getBusinessState(businessId);
        
        if (response.success) {
          setBusinessState(response);
        } else {
          setBusinessStateError(response.error || 'Failed to fetch business state');
        }
      } catch (err) {
        console.error('Error fetching business state:', err);
        setBusinessStateError(err.message || 'Failed to load business snapshot');
      } finally {
        setBusinessStateLoading(false);
      }
    };

    fetchBusinessState();
  }, []);

  // ========================================
  // FETCH DECISION HISTORY
  // ========================================
  useEffect(() => {
    const fetchDecisionHistory = async () => {
      try {
        setDecisionHistoryLoading(true);
        const businessId = localStorage.getItem('maestro_business_id') || 'demo-business';
        const response = await apiService.getDecisionHistory(businessId, 5);
        
        if (response.success && response.decisions) {
          setDecisionHistory(response.decisions);
        }
      } catch (err) {
        // Silent fail - decision history is non-critical
        console.error('Error fetching decision history:', err);
      } finally {
        setDecisionHistoryLoading(false);
      }
    };

    fetchDecisionHistory();
  }, [decisionResult]); // Refetch when new decision is made

  // ========================================
  // OUTCOME UPDATE HANDLER
  // ========================================
  const handleOutcomeUpdate = async (decisionId, outcome, idx) => {
    // Optimistic UI update
    setDecisionHistory(prev => prev.map((item, i) => 
      i === idx ? { ...item, outcome } : item
    ));

    try {
      await apiService.updateDecisionOutcome(decisionId, outcome);
    } catch (err) {
      // Revert on failure (silent)
      console.error('Error updating outcome:', err);
      // Refetch to get actual state
      const businessId = localStorage.getItem('maestro_business_id') || 'demo-business';
      const response = await apiService.getDecisionHistory(businessId, 5);
      if (response.success && response.decisions) {
        setDecisionHistory(response.decisions);
      }
    }
  };

  /**
   * Extract onboarding answers from session response
   * Handles different response formats and provides safe defaults
   * 
   * Expected session response format:
   * {
   *   answers: { q1: "...", q2: "...", ..., q10: "..." }
   *   or directly: { q1: "...", q2: "...", ..., q10: "..." }
   *   or nested: { data: { answers: { q1: "...", ... } } }
   * }
   * 
   * Returns: { q1, q2, ..., q10 } with safe defaults for missing values
   */
  const extractAnswersFromSession = (sessionResponse) => {
    const defaultAnswers = {
      q1: '',
      q2: '',
      q3: '',
      q4: '',
      q5: '',
      q6: '',
      q7: '',
      q8: '',
      q9: '',
      q10: ''
    };

    if (!sessionResponse) {
      console.warn('No session response provided, using defaults');
      return defaultAnswers;
    }

    let answers = null;

    // Try extracting answers from different possible structures
    // Format 1: sessionResponse.answers = { q1, q2, ... }
    if (sessionResponse.answers && typeof sessionResponse.answers === 'object') {
      answers = sessionResponse.answers;
    }
    // Format 2: sessionResponse = { q1, q2, ... } (flat)
    else if (sessionResponse.q1 || sessionResponse.q2) {
      answers = sessionResponse;
    }
    // Format 3: sessionResponse.data.answers = { q1, q2, ... }
    else if (sessionResponse.data?.answers && typeof sessionResponse.data.answers === 'object') {
      answers = sessionResponse.data.answers;
    }
    // Format 4: sessionResponse.result = { q1, q2, ... }
    else if (sessionResponse.result && typeof sessionResponse.result === 'object') {
      answers = sessionResponse.result;
    }

    if (!answers) {
      console.warn('Could not extract answers from session, using defaults');
      return defaultAnswers;
    }

    // Ensure all required question fields exist with safe defaults
    return {
      q1: String(answers.q1 || answers.question1 || '').trim(),
      q2: String(answers.q2 || answers.question2 || '').trim(),
      q3: String(answers.q3 || answers.question3 || '').trim(),
      q4: String(answers.q4 || answers.question4 || '').trim(),
      q5: String(answers.q5 || answers.question5 || '').trim(),
      q6: String(answers.q6 || answers.question6 || '').trim(),
      q7: String(answers.q7 || answers.question7 || '').trim(),
      q8: String(answers.q8 || answers.question8 || '').trim(),
      q9: String(answers.q9 || answers.question9 || '').trim(),
      q10: String(answers.q10 || answers.question10 || '').trim()
    };
  };

  /**
   * Load session on mount
   * 1. Get sessionId from localStorage
   * 2. Fetch onboarding answers (Priority 1)
   * 3. If backend fails, recover from localStorage backup (Priority 2)
   * 4. If no data exists, redirect to onboarding (Priority 3)
   * 5. Build aggregated context
   * 6. Derive decision payload
   * 7. Auto-call inventory decision API (ONLY if data is valid)
   */
  useEffect(() => {
    const loadSession = async () => {
      try {
        setIsLoading(true);
        setError(null);
        let answers = null;
        let context = null;
        let payload = null;
        let usedRecoveryMode = false;

        // ============================================================
        // PRIORITY 1: Try to fetch session from backend
        // ============================================================
        const stored = localStorage.getItem('sessionId');
        if (stored) {
          try {
            console.log('🔍 Priority 1: Attempting backend session fetch...');
            setSessionId(stored);

            const sessionData = await apiService.getSession(stored);
            console.log('✅ Backend session found:', sessionData);

            // Validate session data exists
            if (sessionData && (typeof sessionData !== 'object' || Object.keys(sessionData).length > 0)) {
              const extracted = extractAnswersFromSession(sessionData);
              
              // Validate answers were extracted
              if (extracted && Object.values(extracted).some(v => v && String(v).trim())) {
                console.log('✅ Valid answers extracted from backend session');
                answers = extracted;
              }
            }
          } catch (backendErr) {
            console.warn('⚠️ Backend session fetch failed:', backendErr.message);
            // Will attempt recovery in Priority 2
          }
        } else {
          console.log('ℹ️ No sessionId in localStorage');
        }

        // ============================================================
        // PRIORITY 2: If backend failed, recover from localStorage backup
        // ============================================================
        if (!answers) {
          console.log('🔄 Priority 2: Attempting recovery from localStorage backup...');
          try {
            const backup = localStorage.getItem('maestro_session_backup');
            if (backup) {
              const parsedBackup = JSON.parse(backup);
              console.log('✅ Session backup found, recovering...', parsedBackup);
              
              // Use pre-aggregated context and payload from backup
              answers = parsedBackup.answers;
              context = parsedBackup.context;
              payload = parsedBackup.payload;
              usedRecoveryMode = true;
              
              console.log('✅ Recovery mode: Using cached context and payload');
            }
          } catch (backupErr) {
            console.warn('⚠️ Session backup recovery failed:', backupErr.message);
          }
        }

        // ============================================================
        // PRIORITY 3: If neither backend nor backup, redirect to onboarding
        // ============================================================
        if (!answers) {
          console.log('❌ Priority 3: No session data anywhere, redirecting to onboarding');
          setIsLoading(false);
          // Auto-redirect without showing error UI
          setTimeout(() => {
            navigate('/onboarding', { replace: true });
          }, 300);
          return;
        }

        // ============================================================
        // REBUILD CONTEXT & PAYLOAD (only if not from backup)
        // ============================================================
        if (!usedRecoveryMode) {
          console.log('🔨 Rebuilding context from fresh answers...');
          context = aggregateContext(answers);
          console.log('Aggregated context:', context);
          payload = deriveDecisionPayload(context);
          console.log('Decision payload:', payload);
        }

        // ============================================================
        // UPDATE STATE WITH RESOLVED DATA
        // ============================================================
        setSessionAnswers(answers);
        setMsmeContext(context);
        setDecisionPayload(payload);
        
        // Extract business name from answers for display
        if (answers.q1) {
          setBusinessName(answers.q1.substring(0, 50)); // Use Q1 as business context
        }

        // ============================================================
        // DECISION PIPELINE GATE: Only run if all data is valid
        // ============================================================
        if (answers && context && payload) {
          console.log('✅ All data valid, proceeding to inventory decision API...');
          try {
            const result = await runInventoryDecision(payload);
            console.log('Inventory decision result:', result);
            setDecisionResult(result);
          } catch (apiErr) {
            console.error('Error calling inventory decision API:', apiErr);
            // Show API error to user, but don't block dashboard
            setError('Unable to generate recommendation at this moment. Please refresh.');
          }
        } else {
          console.error('❌ Decision pipeline gate: Missing required data');
          setError('Unable to process your data. Please complete onboarding.');
        }

        setIsLoading(false);
      } catch (err) {
        console.error('Fatal error in session loading:', err);
        setIsLoading(false);
        // Auto-redirect on fatal error instead of showing error UI
        setTimeout(() => {
          navigate('/onboarding', { replace: true });
        }, 300);
      }
    };

    loadSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Handle running the inventory decision API manually
   * (for re-running with same or updated context)
   */
  // eslint-disable-next-line no-unused-vars
  const handleRunDecision = async () => {
    if (!decisionPayload) {
      setError('No decision payload available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await runInventoryDecision(decisionPayload);
      setDecisionResult(result);
    } catch (err) {
      setError(err.message || 'Failed to run inventory decision');
    } finally {
      setIsLoading(false);
    }
  };

  // ========================================
  // DATA ENTRY FORM HANDLERS
  // ========================================

  const getBusinessId = () => {
    return localStorage.getItem('maestro_business_id') || 'demo-business';
  };

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  // Daily Sales Form Handler
  const handleDailySalesSubmit = async (e) => {
    e.preventDefault();
    setDailySalesLoading(true);
    setDailySalesMessage(null);

    try {
      const payload = {
        business_id: getBusinessId(),
        date: dailySalesForm.date,
        product_id: dailySalesForm.product_id,
        units_sold: Number(dailySalesForm.units_sold),
        revenue: dailySalesForm.revenue ? Number(dailySalesForm.revenue) : undefined,
        closing_stock: dailySalesForm.closing_stock ? Number(dailySalesForm.closing_stock) : undefined,
      };

      const response = await fetch('/api/data/daily-sales', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (result.success) {
        setDailySalesMessage({ type: 'success', text: '✅ Sales record saved successfully!' });
        setDailySalesForm({
          date: new Date().toISOString().split('T')[0],
          product_id: '',
          units_sold: '',
          revenue: '',
          closing_stock: '',
        });
      } else {
        setDailySalesMessage({ type: 'error', text: `❌ ${result.error}` });
      }
    } catch (err) {
      setDailySalesMessage({ type: 'error', text: `❌ Failed to save: ${err.message}` });
    } finally {
      setDailySalesLoading(false);
    }
  };

  // Warehouse Snapshot Form Handler
  const handleWarehouseSubmit = async (e) => {
    e.preventDefault();
    setWarehouseLoading(true);
    setWarehouseMessage(null);

    try {
      const payload = {
        business_id: getBusinessId(),
        date: warehouseForm.date,
        current_stock: Number(warehouseForm.current_stock),
        max_capacity: Number(warehouseForm.max_capacity),
        storage_type: warehouseForm.storage_type,
        notes: warehouseForm.notes || undefined,
      };

      const response = await fetch('/api/data/warehouse-snapshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (result.success) {
        const utilization = result.data?.utilization || 0;
        setWarehouseMessage({ 
          type: 'success', 
          text: `✅ Warehouse snapshot saved! Current utilization: ${utilization}%` 
        });
        setWarehouseForm({
          date: new Date().toISOString().split('T')[0],
          current_stock: '',
          max_capacity: '',
          storage_type: 'dry',
          notes: '',
        });
      } else {
        setWarehouseMessage({ type: 'error', text: `❌ ${result.error}` });
      }
    } catch (err) {
      setWarehouseMessage({ type: 'error', text: `❌ Failed to save: ${err.message}` });
    } finally {
      setWarehouseLoading(false);
    }
  };

  // Supplier Delivery Form Handler
  const handleSupplierSubmit = async (e) => {
    e.preventDefault();
    setSupplierLoading(true);
    setSupplierMessage(null);

    try {
      const payload = {
        business_id: getBusinessId(),
        supplier_id: supplierForm.supplier_id,
        product_id: supplierForm.product_id || undefined,
        order_date: supplierForm.order_date,
        delivery_date: supplierForm.delivery_date,
        quantity_received: Number(supplierForm.quantity_received),
      };

      const response = await fetch('/api/data/supplier-delivery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (result.success) {
        const leadTime = result.data?.lead_time_days || 0;
        setSupplierMessage({ 
          type: 'success', 
          text: `✅ Delivery recorded! Lead time: ${leadTime} days` 
        });
        setSupplierForm({
          supplier_id: '',
          product_id: '',
          order_date: '',
          delivery_date: new Date().toISOString().split('T')[0],
          quantity_received: '',
        });
      } else {
        setSupplierMessage({ type: 'error', text: `❌ ${result.error}` });
      }
    } catch (err) {
      setSupplierMessage({ type: 'error', text: `❌ Failed to save: ${err.message}` });
    } finally {
      setSupplierLoading(false);
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
      case 'CRITICAL':
        return 'bg-red-500';
      case 'HIGH':
        return 'bg-orange-500';
      case 'MODERATE':
        return 'bg-amber-500';
      case 'LOW':
        return 'bg-emerald-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getRiskBgColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-500/10 border-red-500/30';
      case 'HIGH':
        return 'bg-orange-500/10 border-orange-500/30';
      case 'MODERATE':
        return 'bg-amber-500/10 border-amber-500/30';
      case 'LOW':
        return 'bg-emerald-500/10 border-emerald-500/30';
      default:
        return 'bg-gray-500/10 border-gray-500/30';
    }
  };

  const getTimingIcon = (timing) => {
    switch (timing?.toUpperCase()) {
      case 'EARLY':
        return '⚡';
      case 'NORMAL':
        return '📅';
      case 'DELAYED':
        return '⏰';
      default:
        return '📋';
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
        {/* LIVE BUSINESS SNAPSHOT (READ-ONLY) */}
        {/* ========================================= */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="text-xl">📊</div>
            <h2 className="text-lg font-semibold text-white">Live Business Snapshot</h2>
            <div className="flex-1 h-px bg-cyan-500/20"></div>
            {businessState?.generated_at && (
              <span className="text-xs text-gray-500">
                Updated: {new Date(businessState.generated_at).toLocaleTimeString()}
              </span>
            )}
          </div>

          {businessStateLoading && (
            <div className="p-6 bg-[#12121a] rounded-xl border border-cyan-500/20 text-center">
              <div className="text-cyan-400 text-sm">⏳ Loading business snapshot...</div>
            </div>
          )}

          {businessStateError && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
              <div className="text-red-400 text-sm">⚠️ {businessStateError}</div>
            </div>
          )}

          {!businessStateLoading && !businessStateError && businessState && (
            <div className="space-y-4">
              {/* Warnings Banner */}
              {businessState.warnings && businessState.warnings.length > 0 && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-400">⚠️</span>
                    <div className="space-y-1">
                      {businessState.warnings.map((warning, idx) => (
                        <div key={idx} className="text-amber-300 text-sm">{warning}</div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Snapshot Cards Grid */}
              <div className="grid grid-cols-3 gap-4">
                
                {/* Demand Snapshot */}
                <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">📈</span>
                    <h3 className="font-medium text-white">Demand</h3>
                  </div>
                  
                  {businessState.demand_snapshot?.record_count > 0 ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Avg Daily Sales</span>
                        <span className="text-white font-medium">
                          {businessState.demand_snapshot.avg_daily_sales ?? '—'} units
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Last 7 Days</span>
                        <span className="text-white font-medium">
                          {businessState.demand_snapshot.last_7_days_total ?? '—'} units
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Trend</span>
                        <span className={`font-medium flex items-center gap-1 ${
                          businessState.demand_snapshot.sales_trend === 'increasing' ? 'text-emerald-400' :
                          businessState.demand_snapshot.sales_trend === 'decreasing' ? 'text-red-400' :
                          'text-gray-300'
                        }`}>
                          {businessState.demand_snapshot.sales_trend === 'increasing' && '📈'}
                          {businessState.demand_snapshot.sales_trend === 'decreasing' && '📉'}
                          {businessState.demand_snapshot.sales_trend === 'stable' && '➡️'}
                          {businessState.demand_snapshot.sales_trend || '—'}
                        </span>
                      </div>
                      <div className="pt-2 border-t border-gray-700">
                        <span className="text-xs text-gray-500">
                          Based on {businessState.demand_snapshot.record_count} records
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <div className="text-gray-500 text-sm">Not enough data yet</div>
                      <div className="text-gray-600 text-xs mt-1">Add daily sales to see insights</div>
                    </div>
                  )}
                </div>

                {/* Warehouse Snapshot */}
                <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">🏭</span>
                    <h3 className="font-medium text-white">Warehouse</h3>
                  </div>
                  
                  {businessState.warehouse_snapshot?.current_stock !== null ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Current Stock</span>
                        <span className="text-white font-medium">
                          {businessState.warehouse_snapshot.current_stock?.toLocaleString() ?? '—'} units
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Max Capacity</span>
                        <span className="text-white font-medium">
                          {businessState.warehouse_snapshot.max_capacity?.toLocaleString() ?? '—'} units
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Utilization</span>
                        <span className={`font-medium ${
                          (businessState.warehouse_snapshot.utilization_ratio ?? 0) > 0.85 ? 'text-red-400' :
                          (businessState.warehouse_snapshot.utilization_ratio ?? 0) > 0.7 ? 'text-amber-400' :
                          'text-emerald-400'
                        }`}>
                          {businessState.warehouse_snapshot.utilization_ratio !== null 
                            ? `${Math.round(businessState.warehouse_snapshot.utilization_ratio * 100)}%`
                            : '—'}
                        </span>
                      </div>
                      {/* Utilization Bar */}
                      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all ${
                            (businessState.warehouse_snapshot.utilization_ratio ?? 0) > 0.85 ? 'bg-red-500' :
                            (businessState.warehouse_snapshot.utilization_ratio ?? 0) > 0.7 ? 'bg-amber-500' :
                            'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min((businessState.warehouse_snapshot.utilization_ratio ?? 0) * 100, 100)}%` }}
                        />
                      </div>
                      <div className="pt-2 border-t border-gray-700">
                        <span className="text-xs text-gray-500">
                          Type: {businessState.warehouse_snapshot.storage_type || '—'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <div className="text-gray-500 text-sm">Not enough data yet</div>
                      <div className="text-gray-600 text-xs mt-1">Add warehouse snapshot</div>
                    </div>
                  )}
                </div>

                {/* Supplier Snapshot */}
                <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">🚚</span>
                    <h3 className="font-medium text-white">Suppliers</h3>
                  </div>
                  
                  {businessState.supplier_snapshot?.record_count > 0 ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Avg Lead Time</span>
                        <span className="text-white font-medium">
                          {businessState.supplier_snapshot.avg_lead_time_days ?? '—'} days
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-400">Variability</span>
                        <span className={`font-medium ${
                          businessState.supplier_snapshot.variability_level === 'HIGH' ? 'text-red-400' :
                          businessState.supplier_snapshot.variability_level === 'MEDIUM' ? 'text-amber-400' :
                          'text-emerald-400'
                        }`}>
                          {businessState.supplier_snapshot.variability_level === 'HIGH' && '⚠️ '}
                          {businessState.supplier_snapshot.variability_level || '—'}
                        </span>
                      </div>
                      <div className="pt-2 border-t border-gray-700">
                        <span className="text-xs text-gray-500">
                          Based on {businessState.supplier_snapshot.record_count} deliveries
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <div className="text-gray-500 text-sm">Not enough data yet</div>
                      <div className="text-gray-600 text-xs mt-1">Record supplier deliveries</div>
                    </div>
                  )}
                </div>

              </div>

              {/* Data Freshness Footer */}
              {businessState.data_freshness && (
                <div className="flex items-center justify-center gap-6 text-xs text-gray-500 pt-2">
                  {businessState.data_freshness.sales_days_ago !== null && (
                    <span className={businessState.data_freshness.sales_days_ago > 7 ? 'text-amber-500' : ''}>
                      Sales: {businessState.data_freshness.sales_days_ago === 0 ? 'Today' : `${businessState.data_freshness.sales_days_ago}d ago`}
                    </span>
                  )}
                  {businessState.data_freshness.warehouse_days_ago !== null && (
                    <span className={businessState.data_freshness.warehouse_days_ago > 3 ? 'text-amber-500' : ''}>
                      Warehouse: {businessState.data_freshness.warehouse_days_ago === 0 ? 'Today' : `${businessState.data_freshness.warehouse_days_ago}d ago`}
                    </span>
                  )}
                  {businessState.data_freshness.supplier_days_ago !== null && (
                    <span className={businessState.data_freshness.supplier_days_ago > 14 ? 'text-amber-500' : ''}>
                      Supplier: {businessState.data_freshness.supplier_days_ago === 0 ? 'Today' : `${businessState.data_freshness.supplier_days_ago}d ago`}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </motion.div>
        
        {/* ========================================= */}
        {/* PERSONALIZED INVENTORY DECISION */}
        {/* ========================================= */}
        
        {isLoading && (
          <div className="mb-6 p-6 bg-[#12121a] rounded-xl border border-cyan-500/20 text-center">
            <div className="text-cyan-400 text-lg font-medium">🔄 Loading your personalized inventory decision...</div>
            <div className="text-gray-400 text-sm mt-2">Analyzing your business context and constraints</div>
          </div>
        )}

        {error && (
          <div className="mb-6 p-6 bg-red-500/10 border border-red-500/30 rounded-xl">
            <div className="text-red-400 font-semibold">⚠️ Error</div>
            <div className="text-red-300 text-sm mt-2">{error}</div>
          </div>
        )}

        {/* ========================================= */}
        {/* INVENTORY HEALTH STATUS CARD */}
        {/* ========================================= */}
        {!isLoading && decisionResult?.final_decision?.reorder_point && (
          <div 
            className={`mb-6 p-6 bg-[#12121a] rounded-xl border-2 transition-all ${
              decisionResult.final_decision.reorder_point.alert_level === 'CRITICAL'
                ? 'border-red-500/60 animate-pulse-subtle'
                : decisionResult.final_decision.reorder_point.alert_level === 'WARNING'
                ? 'border-amber-500/60'
                : 'border-green-500/60'
            }`}
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">📦</span>
              <span className="text-lg font-semibold text-white">Inventory Health Status</span>
              {decisionResult.final_decision.reorder_point.alert_level === 'CRITICAL' && (
                <span className="ml-auto px-2 py-1 text-xs font-bold bg-red-500/20 text-red-400 rounded-full">
                  CRITICAL
                </span>
              )}
              {decisionResult.final_decision.reorder_point.alert_level === 'WARNING' && (
                <span className="ml-auto px-2 py-1 text-xs font-bold bg-amber-500/20 text-amber-400 rounded-full">
                  WARNING
                </span>
              )}
              {decisionResult.final_decision.reorder_point.alert_level === 'OK' && (
                <span className="ml-auto px-2 py-1 text-xs font-bold bg-green-500/20 text-green-400 rounded-full">
                  OK
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Current Stock */}
              <div className="p-3 bg-[#1a1a2e] rounded-lg">
                <div className="text-xs text-gray-500 uppercase mb-1">Current Stock</div>
                <div className="text-xl font-bold text-white">
                  {decisionResult.reorder_point_context?.current_stock?.toLocaleString() ?? '—'}
                </div>
                <div className="text-xs text-gray-500">units</div>
              </div>

              {/* Reorder Point */}
              <div className="p-3 bg-[#1a1a2e] rounded-lg">
                <div className="text-xs text-gray-500 uppercase mb-1">Reorder Point</div>
                <div className="text-xl font-bold text-white">
                  {decisionResult.final_decision.reorder_point.units?.toLocaleString() ?? '—'}
                </div>
                <div className="text-xs text-gray-500">units threshold</div>
              </div>

              {/* Status */}
              <div className="p-3 bg-[#1a1a2e] rounded-lg">
                <div className="text-xs text-gray-500 uppercase mb-1">Status</div>
                <div className={`text-xl font-bold ${
                  decisionResult.final_decision.reorder_point.status === 'BELOW'
                    ? 'text-red-400'
                    : decisionResult.final_decision.reorder_point.status === 'NEAR'
                    ? 'text-amber-400'
                    : 'text-green-400'
                }`}>
                  {decisionResult.final_decision.reorder_point.status ?? '—'}
                </div>
                <div className="text-xs text-gray-500">stock level</div>
              </div>

              {/* Days of Cover */}
              <div className="p-3 bg-[#1a1a2e] rounded-lg">
                <div className="text-xs text-gray-500 uppercase mb-1">Days of Cover</div>
                <div className="text-xl font-bold text-white">
                  {decisionResult.final_decision.reorder_point.days_of_cover_left ?? '—'}
                </div>
                <div className="text-xs text-gray-500">days left</div>
              </div>
            </div>

            {/* Action Message */}
            <div className={`mt-4 p-3 rounded-lg ${
              decisionResult.final_decision.reorder_point.alert_level === 'CRITICAL'
                ? 'bg-red-500/10 border border-red-500/30'
                : decisionResult.final_decision.reorder_point.alert_level === 'WARNING'
                ? 'bg-amber-500/10 border border-amber-500/30'
                : 'bg-green-500/10 border border-green-500/30'
            }`}>
              <div className={`text-sm font-medium ${
                decisionResult.final_decision.reorder_point.alert_level === 'CRITICAL'
                  ? 'text-red-300'
                  : decisionResult.final_decision.reorder_point.alert_level === 'WARNING'
                  ? 'text-amber-300'
                  : 'text-green-300'
              }`}>
                {decisionResult.final_decision.reorder_point.action === 'REORDER_NOW'
                  ? '⚠️ Stock is below reorder point. Place an order immediately to avoid stockouts.'
                  : decisionResult.final_decision.reorder_point.action === 'PREPARE'
                  ? '📋 Stock is approaching reorder point. Prepare to place an order soon.'
                  : '✅ Stock levels are healthy. No immediate action required.'}
              </div>
            </div>
          </div>
        )}

        {!isLoading && decisionResult && (
          <div className="mb-6 p-6 bg-[#12121a] rounded-xl border border-cyan-500/20 space-y-4">
            <div className="text-sm text-gray-400 font-medium">📊 Your Personalized Decision:</div>
            
            {/* Final Decision Box */}
            <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10 space-y-3">
              <div className="text-cyan-400 font-semibold">Final Decision</div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500 uppercase">Reorder Timing</div>
                  <div className="text-lg text-white font-bold mt-1">
                    {decisionResult.final_decision?.reorder_timing || 'N/A'}
                  </div>
                </div>
                
                <div>
                  <div className="text-xs text-gray-500 uppercase">Risk Level</div>
                  <div className="text-lg text-white font-bold mt-1">
                    {decisionResult.final_decision?.risk_level || 'N/A'}
                  </div>
                </div>
              </div>
              
              <div>
                <div className="text-xs text-gray-500 uppercase">Order Strategy</div>
                <div className="text-white mt-1">
                  {decisionResult.final_decision?.order_strategy || 'N/A'}
                </div>
              </div>
              
              <div className="flex items-center justify-between pt-2 border-t border-gray-700">
                <div className="text-xs text-gray-500 uppercase">Confidence</div>
                <div className="text-xl text-cyan-400 font-bold">
                  {Math.round((decisionResult.final_decision?.confidence || 0) * 100)}%
                </div>
              </div>
            </div>
            
            {/* Why This Decision */}
            {decisionResult.why_this_decision && (
              <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                <div className="text-cyan-400 font-semibold mb-2">💡 Why This Decision</div>
                <div className="text-gray-200 text-sm leading-relaxed">
                  {decisionResult.why_this_decision}
                </div>
              </div>
            )}
            
            {/* Immediate Actions */}
            {decisionResult.immediate_actions && decisionResult.immediate_actions.length > 0 && (
              <div className="p-4 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                <div className="text-cyan-400 font-semibold mb-3">🎯 Immediate Actions</div>
                <ul className="space-y-2">
                  {decisionResult.immediate_actions.map((action, idx) => (
                    <li key={idx} className="text-gray-200 text-sm flex items-start gap-2">
                      <span className="text-cyan-400 font-bold mt-0.5">{idx + 1}.</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Debug Info (optional) */}
            {decisionPayload && (
              <div className="mt-4 p-3 bg-gray-900 rounded-lg border border-gray-700 text-xs text-gray-400">
                <div className="font-mono">
                  <div>Decision Payload:</div>
                  <div className="text-gray-500 mt-1">{JSON.stringify(decisionPayload, null, 2)}</div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* ========================================= */}
        {/* END PERSONALIZED DECISION */}
        {/* ========================================= */}

        {/* ========================================= */}
        {/* DECISION HISTORY SECTION */}
        {/* ========================================= */}
        <div className="mb-6 p-6 bg-[#12121a] rounded-xl border border-gray-700/50">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl">📜</span>
            <span className="text-lg font-semibold text-white">Decision History</span>
            <span className="ml-auto text-xs text-gray-500">Last 5 decisions</span>
          </div>

          {decisionHistoryLoading ? (
            <div className="text-center py-8 text-gray-500">
              <div className="animate-spin w-6 h-6 border-2 border-gray-600 border-t-cyan-400 rounded-full mx-auto mb-2"></div>
              Loading history...
            </div>
          ) : decisionHistory.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-3xl mb-2">📭</div>
              <div>No past decisions yet</div>
              <div className="text-xs mt-1">Your decision history will appear here</div>
            </div>
          ) : (
            <div className="space-y-3">
              {decisionHistory.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-[#1a1a2e] rounded-lg border border-gray-700/50 overflow-hidden"
                >
                  {/* Collapsed Header */}
                  <button
                    onClick={() => setExpandedHistoryItem(expandedHistoryItem === idx ? null : idx)}
                    className="w-full p-3 flex items-center gap-3 hover:bg-[#22223a] transition-colors text-left"
                  >
                    {/* Date */}
                    <div className="text-xs text-gray-500 w-24 flex-shrink-0">
                      {new Date(item.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>

                    {/* Reorder Timing */}
                    <div className="text-sm text-white font-medium w-20">
                      {item.decision?.reorder_timing || '—'}
                    </div>

                    {/* Quantity Range */}
                    <div className="text-xs text-gray-400 flex-1">
                      {item.decision?.recommended_quantity_range
                        ? `${item.decision.recommended_quantity_range.lower}-${item.decision.recommended_quantity_range.upper} units`
                        : '—'}
                    </div>

                    {/* Risk Level Badge */}
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      item.decision?.risk_level === 'HIGH'
                        ? 'bg-red-500/20 text-red-400'
                        : item.decision?.risk_level === 'MODERATE'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-green-500/20 text-green-400'
                    }`}>
                      {item.decision?.risk_level || '—'}
                    </span>

                    {/* Alert Status */}
                    {item.reorder_point?.alert_level && (
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        item.reorder_point.alert_level === 'CRITICAL'
                          ? 'bg-red-500'
                          : item.reorder_point.alert_level === 'WARNING'
                          ? 'bg-amber-500'
                          : 'bg-green-500'
                      }`}></span>
                    )}

                    {/* Expand Icon */}
                    <svg
                      className={`w-4 h-4 text-gray-500 transition-transform ${
                        expandedHistoryItem === idx ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {expandedHistoryItem === idx && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="border-t border-gray-700/50"
                      >
                        <div className="p-3 space-y-3 text-sm">
                          {/* Reorder Point Details */}
                          {item.reorder_point && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                              <div className="bg-[#12121a] p-2 rounded">
                                <div className="text-xs text-gray-500">ROP Units</div>
                                <div className="text-white font-medium">{item.reorder_point.units ?? '—'}</div>
                              </div>
                              <div className="bg-[#12121a] p-2 rounded">
                                <div className="text-xs text-gray-500">Status</div>
                                <div className={`font-medium ${
                                  item.reorder_point.status === 'BELOW' ? 'text-red-400'
                                    : item.reorder_point.status === 'NEAR' ? 'text-amber-400'
                                    : 'text-green-400'
                                }`}>{item.reorder_point.status ?? '—'}</div>
                              </div>
                              <div className="bg-[#12121a] p-2 rounded">
                                <div className="text-xs text-gray-500">Days Cover</div>
                                <div className="text-white font-medium">{item.reorder_point.days_of_cover_left ?? '—'}</div>
                              </div>
                              <div className="bg-[#12121a] p-2 rounded">
                                <div className="text-xs text-gray-500">Confidence</div>
                                <div className="text-cyan-400 font-medium">
                                  {item.confidence ? `${(item.confidence * 100).toFixed(0)}%` : '—'}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Order Strategy */}
                          <div className="flex items-center gap-2 text-gray-400">
                            <span className="text-xs">Strategy:</span>
                            <span className="text-white">{item.decision?.order_strategy || '—'}</span>
                          </div>

                          {/* Outcome Feedback */}
                          <div className="flex items-center gap-2 pt-2 border-t border-gray-700/30">
                            <span className="text-xs text-gray-500">Did this work?</span>
                            <div className="flex gap-1 ml-auto">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOutcomeUpdate(item.id, 'GOOD', idx);
                                }}
                                className={`px-2 py-1 text-xs rounded transition-all ${
                                  item.outcome === 'GOOD'
                                    ? 'bg-green-500/30 text-green-300 ring-1 ring-green-500/50'
                                    : 'bg-gray-700/50 text-gray-400 hover:bg-green-500/20 hover:text-green-300'
                                }`}
                              >
                                👍 Worked
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOutcomeUpdate(item.id, 'BAD', idx);
                                }}
                                className={`px-2 py-1 text-xs rounded transition-all ${
                                  item.outcome === 'BAD'
                                    ? 'bg-red-500/30 text-red-300 ring-1 ring-red-500/50'
                                    : 'bg-gray-700/50 text-gray-400 hover:bg-red-500/20 hover:text-red-300'
                                }`}
                              >
                                👎 Didn&apos;t
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOutcomeUpdate(item.id, 'UNKNOWN', idx);
                                }}
                                className={`px-2 py-1 text-xs rounded transition-all ${
                                  item.outcome === 'UNKNOWN'
                                    ? 'bg-gray-500/30 text-gray-300 ring-1 ring-gray-500/50'
                                    : 'bg-gray-700/50 text-gray-400 hover:bg-gray-500/20 hover:text-gray-300'
                                }`}
                              >
                                🤷 Too early
                              </button>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          )}
        </div>
        
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

        {/* ========================================= */}
        {/* UPDATE BUSINESS DATA SECTION */}
        {/* ========================================= */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-12"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="text-2xl">📥</div>
            <h2 className="text-xl font-bold text-white">Update Business Data</h2>
            <div className="flex-1 h-px bg-cyan-500/20"></div>
          </div>

          <div className="space-y-4">
            
            {/* ---------------------------------------- */}
            {/* DAILY SALES ENTRY FORM */}
            {/* ---------------------------------------- */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 overflow-hidden">
              <button
                onClick={() => toggleSection('dailySales')}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#1a1a2e] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">📊</span>
                  <span className="font-medium text-white">Daily Sales Entry</span>
                  <span className="text-xs text-gray-500">Record your daily sales</span>
                </div>
                <motion.span
                  animate={{ rotate: expandedSection === 'dailySales' ? 180 : 0 }}
                  className="text-cyan-400"
                >
                  ▼
                </motion.span>
              </button>
              
              <AnimatePresence>
                {expandedSection === 'dailySales' && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <form onSubmit={handleDailySalesSubmit} className="px-6 pb-6 space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Date *</label>
                          <input
                            type="date"
                            value={dailySalesForm.date}
                            onChange={(e) => setDailySalesForm({ ...dailySalesForm, date: e.target.value })}
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Product ID *</label>
                          <input
                            type="text"
                            value={dailySalesForm.product_id}
                            onChange={(e) => setDailySalesForm({ ...dailySalesForm, product_id: e.target.value })}
                            placeholder="e.g., SKU-001"
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Units Sold *</label>
                          <input
                            type="number"
                            value={dailySalesForm.units_sold}
                            onChange={(e) => setDailySalesForm({ ...dailySalesForm, units_sold: e.target.value })}
                            placeholder="0"
                            min="0"
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Revenue (₹)</label>
                          <input
                            type="number"
                            value={dailySalesForm.revenue}
                            onChange={(e) => setDailySalesForm({ ...dailySalesForm, revenue: e.target.value })}
                            placeholder="Optional"
                            min="0"
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Closing Stock</label>
                          <input
                            type="number"
                            value={dailySalesForm.closing_stock}
                            onChange={(e) => setDailySalesForm({ ...dailySalesForm, closing_stock: e.target.value })}
                            placeholder="Optional"
                            min="0"
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                      
                      {dailySalesMessage && (
                        <div className={`p-3 rounded-lg text-sm ${dailySalesMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/10 text-red-400 border border-red-500/30'}`}>
                          {dailySalesMessage.text}
                        </div>
                      )}
                      
                      <button
                        type="submit"
                        disabled={dailySalesLoading}
                        className="w-full py-3 bg-cyan-500 hover:bg-cyan-600 disabled:bg-cyan-500/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                      >
                        {dailySalesLoading ? (
                          <>
                            <span className="animate-spin">⏳</span> Saving...
                          </>
                        ) : (
                          <>
                            <span>💾</span> Save Sales Record
                          </>
                        )}
                      </button>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* ---------------------------------------- */}
            {/* WAREHOUSE SNAPSHOT FORM */}
            {/* ---------------------------------------- */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 overflow-hidden">
              <button
                onClick={() => toggleSection('warehouse')}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#1a1a2e] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">🏭</span>
                  <span className="font-medium text-white">Warehouse Snapshot</span>
                  <span className="text-xs text-gray-500">Update storage capacity</span>
                </div>
                <motion.span
                  animate={{ rotate: expandedSection === 'warehouse' ? 180 : 0 }}
                  className="text-cyan-400"
                >
                  ▼
                </motion.span>
              </button>
              
              <AnimatePresence>
                {expandedSection === 'warehouse' && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <form onSubmit={handleWarehouseSubmit} className="px-6 pb-6 space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Date *</label>
                          <input
                            type="date"
                            value={warehouseForm.date}
                            onChange={(e) => setWarehouseForm({ ...warehouseForm, date: e.target.value })}
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Storage Type *</label>
                          <select
                            value={warehouseForm.storage_type}
                            onChange={(e) => setWarehouseForm({ ...warehouseForm, storage_type: e.target.value })}
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                          >
                            <option value="dry">Dry Storage</option>
                            <option value="cold">Cold Storage</option>
                            <option value="mixed">Mixed Storage</option>
                          </select>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Current Stock (units) *</label>
                          <input
                            type="number"
                            value={warehouseForm.current_stock}
                            onChange={(e) => setWarehouseForm({ ...warehouseForm, current_stock: e.target.value })}
                            placeholder="e.g., 500"
                            min="0"
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Max Capacity (units) *</label>
                          <input
                            type="number"
                            value={warehouseForm.max_capacity}
                            onChange={(e) => setWarehouseForm({ ...warehouseForm, max_capacity: e.target.value })}
                            placeholder="e.g., 1000"
                            min="1"
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Notes (optional)</label>
                        <input
                          type="text"
                          value={warehouseForm.notes}
                          onChange={(e) => setWarehouseForm({ ...warehouseForm, notes: e.target.value })}
                          placeholder="e.g., Post-festival restocking"
                          maxLength={500}
                          className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      
                      {warehouseMessage && (
                        <div className={`p-3 rounded-lg text-sm ${warehouseMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/10 text-red-400 border border-red-500/30'}`}>
                          {warehouseMessage.text}
                        </div>
                      )}
                      
                      <button
                        type="submit"
                        disabled={warehouseLoading}
                        className="w-full py-3 bg-cyan-500 hover:bg-cyan-600 disabled:bg-cyan-500/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                      >
                        {warehouseLoading ? (
                          <>
                            <span className="animate-spin">⏳</span> Saving...
                          </>
                        ) : (
                          <>
                            <span>💾</span> Save Warehouse Snapshot
                          </>
                        )}
                      </button>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* ---------------------------------------- */}
            {/* SUPPLIER DELIVERY FORM */}
            {/* ---------------------------------------- */}
            <div className="bg-[#12121a] rounded-xl border border-cyan-500/20 overflow-hidden">
              <button
                onClick={() => toggleSection('supplier')}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#1a1a2e] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">🚚</span>
                  <span className="font-medium text-white">Supplier Delivery</span>
                  <span className="text-xs text-gray-500">Track deliveries & lead times</span>
                </div>
                <motion.span
                  animate={{ rotate: expandedSection === 'supplier' ? 180 : 0 }}
                  className="text-cyan-400"
                >
                  ▼
                </motion.span>
              </button>
              
              <AnimatePresence>
                {expandedSection === 'supplier' && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <form onSubmit={handleSupplierSubmit} className="px-6 pb-6 space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Supplier ID *</label>
                          <input
                            type="text"
                            value={supplierForm.supplier_id}
                            onChange={(e) => setSupplierForm({ ...supplierForm, supplier_id: e.target.value })}
                            placeholder="e.g., SUP-001"
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Product ID</label>
                          <input
                            type="text"
                            value={supplierForm.product_id}
                            onChange={(e) => setSupplierForm({ ...supplierForm, product_id: e.target.value })}
                            placeholder="Optional"
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Order Date *</label>
                          <input
                            type="date"
                            value={supplierForm.order_date}
                            onChange={(e) => setSupplierForm({ ...supplierForm, order_date: e.target.value })}
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-400 mb-1">Delivery Date *</label>
                          <input
                            type="date"
                            value={supplierForm.delivery_date}
                            onChange={(e) => setSupplierForm({ ...supplierForm, delivery_date: e.target.value })}
                            required
                            className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Quantity Received (units) *</label>
                        <input
                          type="number"
                          value={supplierForm.quantity_received}
                          onChange={(e) => setSupplierForm({ ...supplierForm, quantity_received: e.target.value })}
                          placeholder="e.g., 100"
                          min="0"
                          required
                          className="w-full px-4 py-2 bg-[#1a1a2e] border border-cyan-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      
                      <div className="p-3 bg-[#1a1a2e] rounded-lg border border-cyan-500/10">
                        <div className="text-xs text-gray-400">💡 Lead time will be calculated automatically from order and delivery dates</div>
                      </div>
                      
                      {supplierMessage && (
                        <div className={`p-3 rounded-lg text-sm ${supplierMessage.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-red-500/10 text-red-400 border border-red-500/30'}`}>
                          {supplierMessage.text}
                        </div>
                      )}
                      
                      <button
                        type="submit"
                        disabled={supplierLoading}
                        className="w-full py-3 bg-cyan-500 hover:bg-cyan-600 disabled:bg-cyan-500/50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                      >
                        {supplierLoading ? (
                          <>
                            <span className="animate-spin">⏳</span> Saving...
                          </>
                        ) : (
                          <>
                            <span>💾</span> Save Delivery Record
                          </>
                        )}
                      </button>
                    </form>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

          </div>
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
