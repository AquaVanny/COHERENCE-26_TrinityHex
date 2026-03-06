import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import AppDashboard from './components/AppDashboard'
import AppPatientMatcher from './components/AppPatientMatcher'
import AppTrialExplorer from './components/AppTrialExplorer'
import AppNavigation from './components/AppNavigation'

function App() {
  return (
    <Router>
      <div className="app-shell">
        <AppNavigation />
        <div className="app-background">
          <div className="orb orb-1"></div>
          <div className="orb orb-2"></div>
          <div className="orb orb-3"></div>
          <div className="orb orb-4"></div>
          <div className="grid-overlay"></div>
        </div>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<AppDashboard />} />
            <Route path="/matcher" element={<AppPatientMatcher />} />
            <Route path="/trials" element={<AppTrialExplorer />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
