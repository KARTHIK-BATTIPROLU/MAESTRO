import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Package, 
  Bot, 
  User, 
  ArrowLeft,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import apiService from '../services/api';
import { aggregateContext, deriveDecisionPayload } from '../utils/contextAggregator';

const OnboardingPage = ({ sessionData, setSessionData, setResults }) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [userInput, setUserInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const messagesEndRef = useRef(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    setIsLoading(true);
    try {
      const response = await apiService.startOnboarding();
      setSessionId(response.session_id);
      setCurrentQuestion(response.first_question);
      setSessionData({ sessionId: response.session_id });
      
      // Add welcome message
      addMessage('bot', response.message);
      
      // Add first question
      setTimeout(() => {
        addMessage('bot', response.first_question.question, response.first_question.options);
      }, 500);
    } catch (error) {
      console.error('Failed to start session:', error);
      addMessage('bot', "Oops! I'm having trouble connecting. Please refresh and try again.");
    }
    setIsLoading(false);
  };

  const addMessage = (type, content, options = null) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      type,
      content,
      options,
      timestamp: new Date()
    }]);
  };

  const handleSendMessage = async () => {
    if (!userInput.trim() || isLoading) return;

    const answer = userInput.trim();
    setUserInput('');
    
    // Add user message
    addMessage('user', answer);
    setIsLoading(true);

    // Store the answer locally
    if (currentQuestion?.key) {
      setUserAnswers(prev => ({ ...prev, [currentQuestion.key]: answer }));
    }

    // Store first answer as business name
    if (currentQuestion?.id === 1) {
      localStorage.setItem('maestro_business', answer);
    }

    try {
      const response = await apiService.sendUserResponse(sessionId, answer);
      setProgress(response.progress);

      if (response.is_complete) {
        setIsComplete(true);
        
        // Store answers for dashboard
        const allAnswers = { ...userAnswers, [currentQuestion.key]: answer };
        localStorage.setItem('maestro_answers', JSON.stringify(allAnswers));
        
        // STEP 1: Create and store aggregated session backup in localStorage
        // This enables recovery if backend session is lost (e.g., after backend restart)
        try {
          const aggregatedContext = aggregateContext(allAnswers);
          const decisionPayload = deriveDecisionPayload(aggregatedContext);
          
          const sessionBackup = {
            timestamp: new Date().toISOString(),
            answers: allAnswers,
            context: aggregatedContext,
            payload: decisionPayload,
            businessName: allAnswers.q1 || 'Your Business'
          };
          
          localStorage.setItem('maestro_session_backup', JSON.stringify(sessionBackup));
          console.log('✅ Session backup created for recovery mode');
        } catch (err) {
          console.error('⚠️ Failed to create session backup:', err);
          // Non-critical failure - continue anyway
        }
        
        // Option 1: Go directly to dashboard with mock data (fast)
        addMessage('bot', "✨ Perfect! Taking you to your personalized dashboard...");
        setTimeout(() => {
          navigate('/dashboard');
        }, 1000);
        
        // Option 2: Process with agents first (uncomment for full AI analysis)
        // addMessage('bot', "🚀 Analyzing your data through our AI agents...");
        // try {
        //   const result = await apiService.processWithAgents(sessionId);
        //   localStorage.setItem('maestro_results', JSON.stringify(result));
        //   navigate('/dashboard', { state: { results: result } });
        // } catch (err) {
        //   console.error('Agent processing failed:', err);
        //   navigate('/dashboard'); // Fall back to mock data
        // }
      } else {
        setCurrentQuestion(response.next_question);
        addMessage('bot', response.message);
        
        setTimeout(() => {
          addMessage('bot', response.next_question.question, response.next_question.options);
        }, 400);
      }
    } catch (error) {
      console.error('Failed to send response:', error);
      addMessage('bot', "I didn't catch that. Could you try again?");
    }
    
    setIsLoading(false);
  };

  const handleOptionClick = (option) => {
    setUserInput(option);
  };

  const processWithAgents = async () => {
    setIsProcessing(true);
    addMessage('bot', "🚀 Now running your data through our AI inventory agent. This may take a minute...");

    try {
      const result = await apiService.processWithAgents(sessionId);
      setResults(result);
      
      addMessage('bot', "✨ Analysis complete! Redirecting to your personalized dashboard...");
      
      setTimeout(() => {
        navigate('/dashboard', { 
          state: { 
            results: result,
            businessName: sessions?.answers?.business_context || 'Your Business'
          } 
        });
      }, 2000);
    } catch (error) {
      console.error('Processing failed:', error);
      addMessage('bot', "I encountered an issue while processing. Please try again or contact support.");
      setIsProcessing(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-glass border-b border-dark-700/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-dark-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back</span>
          </button>
          
          <div className="flex items-center gap-2">
            <Package className="w-6 h-6 text-primary-400" />
            <span className="font-display font-bold text-gradient">MAESTRO</span>
          </div>

          <div className="text-sm text-dark-400">
            {Math.round(progress)}% Complete
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-1 bg-dark-800">
          <motion.div
            className="h-full progress-bar"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </header>

      {/* Chat container */}
      <main className="flex-1 container mx-auto max-w-3xl px-4 py-6 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex gap-3 ${message.type === 'user' ? 'flex-row-reverse' : ''}`}
              >
                {/* Avatar */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                  message.type === 'bot' 
                    ? 'bg-gradient-to-br from-primary-500 to-accent-500' 
                    : 'bg-dark-700'
                }`}>
                  {message.type === 'bot' ? (
                    <Bot className="w-5 h-5 text-white" />
                  ) : (
                    <User className="w-5 h-5 text-dark-300" />
                  )}
                </div>

                {/* Message bubble */}
                <div className={`max-w-[80%] ${message.type === 'user' ? 'text-right' : ''}`}>
                  <div className={`inline-block px-4 py-3 rounded-2xl ${
                    message.type === 'bot'
                      ? 'bg-dark-800/80 border border-dark-700 text-white'
                      : 'bg-gradient-to-r from-primary-500 to-accent-500 text-white'
                  }`}>
                    <p className="text-sm md:text-base">{message.content}</p>
                  </div>

                  {/* Options */}
                  {message.options && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.options.map((option, idx) => (
                        <motion.button
                          key={idx}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: idx * 0.1 }}
                          onClick={() => handleOptionClick(option)}
                          className="px-4 py-2 rounded-full bg-dark-800/50 border border-dark-600 
                                   hover:border-primary-500 hover:bg-dark-700 text-sm
                                   transition-all duration-200"
                        >
                          {option}
                        </motion.button>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-dark-800/80 border border-dark-700 rounded-2xl px-4 py-3">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Processing indicator */}
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card text-center py-8"
            >
              <Loader2 className="w-12 h-12 text-primary-400 animate-spin mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">AI Agents Analyzing Your Inventory...</h3>
              <p className="text-dark-400 text-sm">
                Assessing risks and computing optimal reorder recommendations
              </p>
              <div className="mt-4 flex justify-center gap-2 flex-wrap">
                {['Router & Intake Agent'].map((agent, idx) => (
                  <motion.span
                    key={agent}
                    initial={{ opacity: 0.5 }}
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: idx * 0.3 }}
                    className="px-3 py-1 rounded-full bg-dark-700 text-xs"
                  >
                    {agent}
                  </motion.span>
                ))}
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        {!isComplete && !isProcessing && (
          <div className="sticky bottom-0 bg-gradient-to-t from-dark-900 to-transparent pt-4">
            <div className="bg-dark-800/90 border border-dark-700 rounded-2xl p-2 flex items-center gap-2">
              <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your answer..."
                disabled={isLoading}
                className="flex-1 bg-transparent px-4 py-3 outline-none text-white placeholder:text-dark-400"
              />
              <button
                onClick={handleSendMessage}
                disabled={!userInput.trim() || isLoading}
                className="p-3 rounded-xl bg-gradient-to-r from-primary-500 to-accent-500 
                         hover:from-primary-400 hover:to-accent-400 
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-200"
              >
                <Send className="w-5 h-5 text-white" />
              </button>
            </div>
            <p className="text-center text-dark-500 text-xs mt-2">
              Press Enter to send • Click options to auto-fill
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default OnboardingPage;
