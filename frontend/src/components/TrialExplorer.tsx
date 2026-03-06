import { useState, useEffect } from 'react'
import { Search, MapPin, Calendar, Users, FileText, Filter } from 'lucide-react'
import axios from 'axios'

interface Trial {
  trial_id: string
  title: string
  phase: string
  sponsor: string
  location: string
  status: string
  condition: string
  eligibility_criteria: string
  estimated_enrollment: number
}

const TrialExplorer = () => {
  const [trials, setTrials] = useState<Trial[]>([])
  const [filteredTrials, setFilteredTrials] = useState<Trial[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPhase, setSelectedPhase] = useState('')
  const [selectedCondition, setSelectedCondition] = useState('')

  useEffect(() => {
    loadTrials()
  }, [])

  useEffect(() => {
    filterTrials()
  }, [trials, searchTerm, selectedPhase, selectedCondition])

  const loadTrials = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/sample-data')
      setTrials(response.data.trials)
    } catch (error) {
      console.error('Failed to load trials:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterTrials = () => {
    let filtered = trials

    if (searchTerm) {
      filtered = filtered.filter(trial =>
        trial.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trial.condition.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trial.sponsor.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (selectedPhase) {
      filtered = filtered.filter(trial => trial.phase === selectedPhase)
    }

    if (selectedCondition) {
      filtered = filtered.filter(trial =>
        trial.condition.toLowerCase().includes(selectedCondition.toLowerCase())
      )
    }

    setFilteredTrials(filtered)
  }

  const phases = [...new Set(trials.map(trial => trial.phase))]
  const conditions = [...new Set(trials.map(trial => trial.condition))]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Clinical Trial Explorer</h1>
        <p className="text-gray-600">
          Browse and search available clinical trials with detailed eligibility criteria
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Filter className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900">Search & Filter</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Trials
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by title, condition, or sponsor..."
                className="pl-10 w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phase
            </label>
            <select
              value={selectedPhase}
              onChange={(e) => setSelectedPhase(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Phases</option>
              {phases.map(phase => (
                <option key={phase} value={phase}>{phase}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Condition
            </label>
            <select
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Conditions</option>
              {conditions.map(condition => (
                <option key={condition} value={condition}>{condition}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Showing {filteredTrials.length} of {trials.length} trials
          </p>
          <button
            onClick={() => {
              setSearchTerm('')
              setSelectedPhase('')
              setSelectedCondition('')
            }}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Trial Results */}
      <div className="space-y-4">
        {loading ? (
          <div className="bg-white rounded-lg shadow p-8">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading trials...</span>
            </div>
          </div>
        ) : filteredTrials.length > 0 ? (
          filteredTrials.map((trial) => (
            <div key={trial.trial_id} className="bg-white rounded-lg shadow">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {trial.title}
                    </h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span className="flex items-center">
                        <FileText className="h-4 w-4 mr-1" />
                        {trial.trial_id}
                      </span>
                      <span className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        {trial.phase}
                      </span>
                      <span className="flex items-center">
                        <Users className="h-4 w-4 mr-1" />
                        {trial.estimated_enrollment} participants
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      trial.status === 'Recruiting' 
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {trial.status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Study Details</h4>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Condition:</span>
                        <span className="ml-2 text-gray-600">{trial.condition}</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Sponsor:</span>
                        <span className="ml-2 text-gray-600">{trial.sponsor}</span>
                      </div>
                      <div className="flex items-start">
                        <MapPin className="h-4 w-4 text-gray-400 mr-1 mt-0.5" />
                        <span className="text-gray-600">{trial.location}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Eligibility Criteria</h4>
                    <div className="text-sm text-gray-600 max-h-32 overflow-y-auto">
                      <p>{trial.eligibility_criteria}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-500">
                      Last updated: {new Date().toLocaleDateString()}
                    </div>
                    <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm">
                      View Full Details
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-white rounded-lg shadow p-8">
            <div className="text-center text-gray-500">
              <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No trials found matching your criteria</p>
              <p className="text-sm mt-1">Try adjusting your search filters</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default TrialExplorer
