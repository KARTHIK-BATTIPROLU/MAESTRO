import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  Package,
  ArrowLeft,
  Download,
  Share2,
  AlertTriangle,
  Clock,
  Box,
  Truck,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Home,
  Building2,
  BarChart3,
  Shield,
  Warehouse,
  Calculator
} from 'lucide-react';

const ResultsPage = ({ results, sessionData }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('recommendation');
  const [expandedSections, setExpandedSections] = useState({});

  useEffect(() => {
    // If no results, redirect to home
    if (!results) {
      navigate('/');
    }
  }, [results, navigate]);

  if (!results) {
    return null;
  }

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const tabs = [
    { id: 'recommendation', label: 'Recommendation', icon: <Package className="w-4 h-4" /> },
    { id: 'risk', label: 'Risk Analysis', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'policy', label: 'Inventory Policy', icon: <Calculator className="w-4 h-4" /> },
    { id: 'details', label: 'Full Analysis', icon: <BarChart3 className="w-4 h-4" /> },
  ];

  const summary = results.summary || {};
  const userResponses = results.user_responses || {};

  return (
    <div className="min-h-screen">
      {/* Background orbs */}
      <div className="orb orb-1 opacity-20"></div>
      <div className="orb orb-2 opacity-20"></div>

      {/* Header */}
      <header className="bg-glass border-b border-dark-700/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-dark-300 hover:text-white transition-colors"
          >
            <Home className="w-5 h-5" />
            <span>Home</span>
          </button>
          
          <div className="flex items-center gap-2">
            <Package className="w-6 h-6 text-primary-400" />
            <span className="font-display font-bold text-gradient">MAESTRO Recommendation</span>
          </div>

          <div className="flex items-center gap-2">
            <button className="p-2 rounded-lg hover:bg-dark-700 transition-colors">
              <Share2 className="w-5 h-5 text-dark-300" />
            </button>
            <button className="p-2 rounded-lg hover:bg-dark-700 transition-colors">
              <Download className="w-5 h-5 text-dark-300" />
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Success Banner */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card mb-8 p-6 text-center bg-gradient-to-r from-primary-500/10 to-accent-500/10 border-primary-500/30"
        >
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl md:text-3xl font-display font-bold mb-2">
            Your Inventory Recommendation is Ready! 📦
          </h1>
          <p className="text-dark-300">
            Our 5 AI agents have analyzed your situation and created a personalized reorder plan
          </p>
        </motion.div>

        {/* Business Context Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card mb-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <Building2 className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-semibold">Business Context</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Business', value: userResponses.business_context?.slice(0, 50) + '...', icon: <Building2 className="w-4 h-4" /> },
              { label: 'Decision Method', value: userResponses.inventory_decision_method, icon: <Calculator className="w-4 h-4" /> },
              { label: 'Stock Issues', value: userResponses.stock_issues?.slice(0, 30) + '...', icon: <AlertTriangle className="w-4 h-4" /> },
              { label: 'Supplier Status', value: userResponses.supplier_reliability?.slice(0, 30) + '...', icon: <Truck className="w-4 h-4" /> },
            ].map((item) => (
              <div key={item.label} className="bg-dark-800/50 rounded-xl p-3">
                <div className="flex items-center gap-2 text-dark-400 text-xs mb-1">
                  {item.icon}
                  {item.label}
                </div>
                <div className="font-medium text-sm">{item.value || 'N/A'}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Key Problems Detected */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="card mb-8 border-yellow-500/30"
        >
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            <h2 className="text-lg font-semibold">Key Problems Detected</h2>
          </div>
          <div className="space-y-2">
            {(summary.key_problems || ['Inventory timing and quantity decisions need optimization']).map((problem, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-1" />
                <span className="text-dark-200">{problem}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-primary-500 to-accent-500 text-white'
                  : 'bg-dark-800 hover:bg-dark-700 text-dark-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content based on active tab */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === 'recommendation' && (
            <div className="space-y-6">
              {/* Main Recommendation Cards */}
              <div className="grid md:grid-cols-3 gap-4">
                <div className="card border-blue-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-5 h-5 text-blue-400" />
                    <h3 className="font-semibold">⏰ Reorder Timing</h3>
                  </div>
                  <p className="text-dark-200 text-sm">
                    {summary.recommendation?.timing || 'See full recommendation below'}
                  </p>
                </div>
                <div className="card border-green-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Box className="w-5 h-5 text-green-400" />
                    <h3 className="font-semibold">📦 Order Quantity</h3>
                  </div>
                  <p className="text-dark-200 text-sm">
                    {summary.recommendation?.quantity || 'See full recommendation below'}
                  </p>
                </div>
                <div className="card border-purple-500/30">
                  <div className="flex items-center gap-2 mb-3">
                    <Truck className="w-5 h-5 text-purple-400" />
                    <h3 className="font-semibold">🚚 Delivery Schedule</h3>
                  </div>
                  <p className="text-dark-200 text-sm">
                    {summary.recommendation?.delivery || 'See full recommendation below'}
                  </p>
                </div>
              </div>

              {/* Full Recommendation */}
              {results.final_recommendation && (
                <div className="card">
                  <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <span className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
                      🎯
                    </span>
                    Full MAESTRO Recommendation
                  </h3>
                  <div className="prose prose-invert max-w-none">
                    <ReactMarkdown>
                      {results.final_recommendation}
                    </ReactMarkdown>
                  </div>
                </div>
              )}

              {/* Next Actions */}
              <div className="card">
                <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                  <span className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                    🚀
                  </span>
                  Immediate Next Actions
                </h3>
                <div className="space-y-2">
                  {(summary.next_actions || [
                    'Review the full recommendation above',
                    'Check your current stock levels',
                    'Contact your suppliers about order timing',
                    'Set up inventory alerts based on reorder point',
                    'Schedule a follow-up review in 2-4 weeks'
                  ]).map((action, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 rounded-xl bg-dark-800/50 hover:bg-dark-700/50 transition-colors">
                      <span className="w-6 h-6 rounded-full bg-gradient-to-r from-primary-500 to-accent-500 flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </span>
                      <span className="text-dark-200">{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'risk' && (
            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Shield className="w-6 h-6 text-yellow-400" />
                Risk Assessment
              </h3>
              <div className="prose prose-invert max-w-none">
                {results.risk_assessment ? (
                  <ReactMarkdown>{results.risk_assessment}</ReactMarkdown>
                ) : (
                  <p className="text-dark-400">Risk assessment details will appear here after processing.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'policy' && (
            <div className="card">
              <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Calculator className="w-6 h-6 text-primary-400" />
                Inventory Policy Recommendation
              </h3>
              <div className="prose prose-invert max-w-none">
                {results.policy_recommendation ? (
                  <ReactMarkdown>{results.policy_recommendation}</ReactMarkdown>
                ) : (
                  <p className="text-dark-400">Policy recommendation details will appear here after processing.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-6">
              {/* Intake Analysis */}
              <div className="card">
                <button
                  onClick={() => toggleSection('intake')}
                  className="w-full flex items-center justify-between"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-blue-400" />
                    Stage 1: Business Intake Analysis
                  </h3>
                  {expandedSections.intake ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {expandedSections.intake && results.intake_analysis && (
                  <div className="mt-4 prose prose-invert max-w-none">
                    <ReactMarkdown>{results.intake_analysis}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Risk Assessment */}
              <div className="card">
                <button
                  onClick={() => toggleSection('risk')}
                  className="w-full flex items-center justify-between"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                    Stage 2: Risk Assessment
                  </h3>
                  {expandedSections.risk ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {expandedSections.risk && results.risk_assessment && (
                  <div className="mt-4 prose prose-invert max-w-none">
                    <ReactMarkdown>{results.risk_assessment}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Policy Recommendation */}
              <div className="card">
                <button
                  onClick={() => toggleSection('policy')}
                  className="w-full flex items-center justify-between"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Calculator className="w-5 h-5 text-green-400" />
                    Stage 3: Policy & Safety Stock
                  </h3>
                  {expandedSections.policy ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {expandedSections.policy && results.policy_recommendation && (
                  <div className="mt-4 prose prose-invert max-w-none">
                    <ReactMarkdown>{results.policy_recommendation}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Feasibility Check */}
              <div className="card">
                <button
                  onClick={() => toggleSection('feasibility')}
                  className="w-full flex items-center justify-between"
                >
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Warehouse className="w-5 h-5 text-purple-400" />
                    Stage 4: Warehouse & Feasibility Check
                  </h3>
                  {expandedSections.feasibility ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {expandedSections.feasibility && results.feasibility_check && (
                  <div className="mt-4 prose prose-invert max-w-none">
                    <ReactMarkdown>{results.feasibility_check}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          )}
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-12 text-center"
        >
          <div className="card p-8 bg-gradient-to-r from-primary-500/10 to-accent-500/10 border-primary-500/30">
            <h3 className="text-xl font-semibold mb-4">Ready to Optimize Your Inventory?</h3>
            <p className="text-dark-300 mb-6">
              Implement these recommendations to reduce stockouts and improve cash flow. 
              Come back anytime for a fresh analysis.
            </p>
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => navigate('/onboarding')}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                New Assessment
              </button>
              <button
                onClick={() => navigate('/')}
                className="btn-primary flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                Back to Home
              </button>
            </div>
          </div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-800 py-8 mt-10">
        <div className="container mx-auto px-6 text-center text-dark-400 text-sm">
          <p>Built with MAESTRO 📦 MSME Inventory Intelligence System</p>
        </div>
      </footer>
    </div>
  );
};

export default ResultsPage;
