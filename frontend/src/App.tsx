import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import PatientMatcher from './components/PatientMatcher'
import TrialExplorer from './components/TrialExplorer'
import Navigation from './components/Navigation'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/matcher" element={<PatientMatcher />} />
            <Route path="/trials" element={<TrialExplorer />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
