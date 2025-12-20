import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Package, 
  TrendingUp, 
  AlertTriangle, 
  Clock,
  ArrowRight,
  Building2,
  Truck,
  Warehouse,
  Calculator,
  Shield,
  BarChart3,
  CheckCircle2
} from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Clock className="w-8 h-8" />,
      title: "Reorder Timing",
      description: "Know exactly WHEN to place orders to avoid stockouts and excess inventory"
    },
    {
      icon: <Calculator className="w-8 h-8" />,
      title: "Optimal Quantity",
      description: "Calculate HOW MUCH to order based on your unique business constraints"
    },
    {
      icon: <AlertTriangle className="w-8 h-8" />,
      title: "Risk Assessment",
      description: "Quantify supplier delays, demand volatility, and external risks"
    },
    {
      icon: <Warehouse className="w-8 h-8" />,
      title: "Constraint Aware",
      description: "Recommendations that respect your storage, cash flow, and handling limits"
    }
  ];

  const painPoints = [
    { icon: <Package className="w-6 h-6" />, text: "Frequent stockouts" },
    { icon: <Truck className="w-6 h-6" />, text: "Supplier delays" },
    { icon: <TrendingUp className="w-6 h-6" />, text: "Demand uncertainty" }
  ];

  const benefits = [
    "Reduce stockouts by up to 40%",
    "Lower excess inventory costs",
    "Improve cash flow timing",
    "Make confident reorder decisions"
  ];

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background orbs */}
      <div className="orb orb-1"></div>
      <div className="orb orb-2"></div>
      <div className="orb orb-3"></div>

      {/* Header */}
      <header className="relative z-10 container mx-auto px-6 py-6">
        <nav className="flex items-center justify-between">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2"
          >
            <Package className="w-8 h-8 text-primary-400" />
            <span className="text-2xl font-display font-bold text-gradient">MAESTRO</span>
          </motion.div>
          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            onClick={() => navigate('/onboarding')}
            className="btn-secondary flex items-center gap-2"
          >
            Optimize Inventory <ArrowRight className="w-4 h-4" />
          </motion.button>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 container mx-auto px-6">
        <section className="min-h-[80vh] flex flex-col items-center justify-center text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-4xl"
          >
            {/* Badge */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-glass mb-8"
            >
              <Shield className="w-4 h-4 text-accent-400" />
              <span className="text-sm text-dark-200">AI-Powered Inventory Intelligence for MSMEs</span>
            </motion.div>

            {/* Main heading */}
            <h1 className="text-5xl md:text-7xl font-display font-bold mb-6 leading-tight">
              Stop Guessing,
              <span className="block text-gradient">Start Deciding</span>
            </h1>

            <p className="text-xl md:text-2xl text-dark-300 mb-8 max-w-2xl mx-auto">
              MAESTRO analyzes your demand patterns, supplier reliability, and constraints 
              to tell you exactly <strong>when</strong> to reorder and <strong>how much</strong>.
            </p>

            {/* Pain points */}
            <div className="flex items-center justify-center gap-4 mb-10 flex-wrap">
              {painPoints.map((point, index) => (
                <motion.div
                  key={point.text}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                  className="flex items-center gap-2 px-4 py-2 rounded-full bg-red-900/20 border border-red-700/50"
                >
                  <span className="text-red-400">{point.icon}</span>
                  <span className="text-sm font-medium text-red-300">{point.text}</span>
                </motion.div>
              ))}
            </div>

            {/* CTA Button */}
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              onClick={() => navigate('/onboarding')}
              className="btn-primary text-lg flex items-center gap-3 mx-auto"
            >
              <BarChart3 className="w-5 h-5" />
              Get Your Inventory Plan
              <ArrowRight className="w-5 h-5" />
            </motion.button>
          </motion.div>
        </section>

        {/* Features Section */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">
              What MAESTRO Does For You
            </h2>
            <p className="text-dark-300 max-w-xl mx-auto">
              Five specialized AI agents work together to give you one clear inventory decision
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="card group hover:border-primary-500/50 transition-all duration-300"
              >
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                  <div className="text-primary-400 group-hover:text-accent-400 transition-colors">
                    {feature.icon}
                  </div>
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-dark-400 text-sm">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">
              Simple 3-Step Process
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              { step: "01", title: "Tell Us Your Situation", desc: "Answer 10 questions about your business, suppliers, and challenges" },
              { step: "02", title: "AI Agents Analyze", desc: "Our 5 specialized agents assess risks and compute optimal policies" },
              { step: "03", title: "Get Clear Recommendation", desc: "Receive timing, quantity, and delivery schedule you can act on" }
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2 }}
                className="text-center"
              >
                <div className="text-6xl font-display font-bold text-gradient mb-4">{item.step}</div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-dark-400">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Benefits Section */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="card max-w-3xl mx-auto p-10"
          >
            <div className="flex items-center gap-3 mb-6">
              <Building2 className="w-8 h-8 text-primary-400" />
              <h2 className="text-2xl font-display font-bold">Built for MSME Business Owners</h2>
            </div>
            <p className="text-dark-300 mb-8">
              Whether you run a retail shop, wholesale business, or manufacturing unit, 
              MAESTRO understands your unique constraints and gives you practical recommendations.
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              {benefits.map((benefit, index) => (
                <motion.div
                  key={benefit}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center gap-3"
                >
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                  <span className="text-dark-200">{benefit}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Final CTA */}
        <section className="py-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="card max-w-2xl mx-auto p-10 border-primary-500/30"
          >
            <h2 className="text-3xl font-display font-bold mb-4">
              Ready to Optimize Your Inventory?
            </h2>
            <p className="text-dark-300 mb-8">
              Stop losing money to stockouts and excess inventory. Get your personalized 
              recommendation in under 5 minutes.
            </p>
            <button
              onClick={() => navigate('/onboarding')}
              className="btn-primary text-lg flex items-center gap-3 mx-auto"
            >
              <Package className="w-5 h-5" />
              Start Inventory Assessment
            </button>
          </motion.div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-dark-800 py-8 mt-10">
        <div className="container mx-auto px-6 text-center text-dark-400 text-sm">
          <p>© 2024 MAESTRO. MSME Inventory Intelligence System.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
