import { useState, useEffect } from 'react'
import { Activity, Users, FileText, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'

interface DemoResult {
  demo_patient: any
  top_matches: any[]
  total_trials_evaluated: number
}

const Dashboard = () => {
  const [demoResult, setDemoResult] = useState<DemoResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runDemo = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.get('http://localhost:5000/api/demo-match')
      setDemoResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to run demo')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runDemo()
  }, [])

  const stats = [
    {
      title: 'Total Patients',
      value: '4',
      icon: Users,
      color: 'bg-blue-500'
    },
    {
      title: 'Active Trials',
      value: '5',
      icon: FileText,
      color: 'bg-green-500'
    },
    {
      title: 'Successful Matches',
      value: demoResult ? demoResult.top_matches.filter(t => t.eligibility_score > 0.5).length.toString() : '0',
      icon: TrendingUp,
      color: 'bg-purple-500'
    },
    {
      title: 'AI Confidence',
      value: demoResult ? `${Math.round((demoResult.top_matches[0]?.confidence || 0) * 100)}%` : '0%',
      icon: Activity,
      color: 'bg-orange-500'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI-Powered Clinical Trial Matching Engine
        </h1>
        <p className="text-gray-600">
          Intelligent system for matching anonymized patient records to suitable clinical trials
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className={`${stat.color} rounded-lg p-3 mr-4`}>
                <stat.icon className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Demo Results */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900">Live Demo Results</h2>
            <button
              onClick={runDemo}
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Running...' : 'Run Demo'}
            </button>
          </div>
        </div>

        <div className="p-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          )}

          {demoResult && (
            <div className="space-y-6">
              {/* Patient Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-2">Anonymized Patient Profile</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="font-medium">ID:</span> {demoResult.demo_patient.patient_id}
                  </div>
                  <div>
                    <span className="font-medium">Age Range:</span> {demoResult.demo_patient.age_range}
                  </div>
                  <div>
                    <span className="font-medium">Gender:</span> {demoResult.demo_patient.gender}
                  </div>
                  <div>
                    <span className="font-medium">Region:</span> {demoResult.demo_patient.region}
                  </div>
                </div>
              </div>

              {/* Top Matches */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-4">Top Trial Matches</h3>
                <div className="space-y-4">
                  {demoResult.top_matches.map((trial, index) => (
                    <div key={trial.trial_id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900">{trial.title}</h4>
                          <p className="text-sm text-gray-600">{trial.trial_id} • {trial.phase}</p>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center space-x-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              trial.eligibility_score > 0.7 
                                ? 'bg-green-100 text-green-800' 
                                : trial.eligibility_score > 0.4
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {trial.eligibility_score > 0.7 ? (
                                <CheckCircle className="w-3 h-3 mr-1" />
                              ) : (
                                <AlertCircle className="w-3 h-3 mr-1" />
                              )}
                              {Math.round(trial.eligibility_score * 100)}% Match
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {Math.round(trial.confidence * 100)}% Confidence
                          </p>
                        </div>
                      </div>
                      
                      <div className="mt-3">
                        <h5 className="text-sm font-medium text-gray-700 mb-1">Eligibility Analysis:</h5>
                        <div className="space-y-1">
                          {trial.explanations.slice(0, 3).map((explanation: string, idx: number) => (
                            <p key={idx} className="text-xs text-gray-600">• {explanation}</p>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Running AI matching algorithm...</span>
            </div>
          )}
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center mb-4">
            <Users className="h-8 w-8 text-blue-600 mr-3" />
            <h3 className="text-lg font-semibold">Patient Anonymization</h3>
          </div>
          <p className="text-gray-600">
            Advanced anonymization preserves clinical relevance while protecting patient privacy
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center mb-4">
            <Activity className="h-8 w-8 text-green-600 mr-3" />
            <h3 className="text-lg font-semibold">AI Matching</h3>
          </div>
          <p className="text-gray-600">
            Machine learning algorithms analyze eligibility criteria and patient data for optimal matches
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center mb-4">
            <FileText className="h-8 w-8 text-purple-600 mr-3" />
            <h3 className="text-lg font-semibold">Explainable Results</h3>
          </div>
          <p className="text-gray-600">
            Transparent explanations and confidence scores for every match recommendation
          </p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
