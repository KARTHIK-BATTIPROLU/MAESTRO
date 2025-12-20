import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import ResultsPage from './pages/ResultsPage';
import DashboardPage from './pages/DashboardPage';

function App() {
  const [sessionData, setSessionData] = useState(null);
  const [results, setResults] = useState(null);

  return (
    <Router>
      <div className="min-h-screen bg-hero-gradient">
        <Routes>
          <Route 
            path="/" 
            element={<LandingPage />} 
          />
          <Route 
            path="/onboarding" 
            element={
              <OnboardingPage 
                sessionData={sessionData}
                setSessionData={setSessionData}
                setResults={setResults}
              />
            } 
          />
          <Route 
            path="/results" 
            element={
              <ResultsPage 
                results={results}
                sessionData={sessionData}
              />
            } 
          />
          <Route 
            path="/dashboard" 
            element={<DashboardPage />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
