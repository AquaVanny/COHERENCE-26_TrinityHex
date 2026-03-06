import { useState } from 'react'
import { Upload, User, FileText, Search, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'
import FileUpload from './FileUpload'

interface MatchResult {
  patient_id: string
  ranked_trials: any[]
  total_trials: number
}

const PatientMatcher = () => {
  const [patientData, setPatientData] = useState('')
  const [matchResults, setMatchResults] = useState<MatchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'manual' | 'upload'>('manual')

  const samplePatient = {
    patient_id: "P005",
    name: "Jane Doe",
    age: 52,
    gender: "female",
    location: "Chicago, IL",
    diagnosis: ["Type 2 Diabetes", "Obesity"],
    diagnosis_date: "2023-06-15T00:00:00Z",
    medications: ["Metformin", "Insulin"],
    lab_results: {
      hba1c: 9.1,
      glucose: 220,
      bmi: 32.5
    }
  }

  const loadSampleData = () => {
    setPatientData(JSON.stringify(samplePatient, null, 2))
  }

  const matchPatient = async () => {
    if (!patientData.trim()) {
      setError('Please enter patient data')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Parse patient data
      const patient = JSON.parse(patientData)
      
      // Get sample trials
      const trialsResponse = await axios.get('http://localhost:5000/api/sample-data')
      const trials = trialsResponse.data.trials

      // Match patient to trials
      const matchResponse = await axios.post('http://localhost:5000/api/match-trials', {
        patient_data: patient,
        trials_data: trials
      })

      setMatchResults(matchResponse.data)
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON format in patient data')
      } else {
        setError(err.response?.data?.message || 'Failed to match patient')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleFileUploadSuccess = (data: any) => {
    if (data.matching_results) {
      // Handle upload-and-match results
      const firstResult = data.matching_results[0]
      if (firstResult) {
        setMatchResults({
          patient_id: firstResult.patient_id,
          ranked_trials: firstResult.ranked_trials,
          total_trials: firstResult.total_trials_evaluated
        })
      }
    }
    setError(null)
  }

  const handleFileUploadError = (errorMessage: string) => {
    setError(errorMessage)
    setMatchResults(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Patient Trial Matcher</h1>
        <p className="text-gray-600">
          Upload patient data files or enter data manually to find matching clinical trials with AI-powered analysis
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Patient Data Input</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setActiveTab('manual')}
                  className={`px-3 py-1 text-sm rounded-md ${
                    activeTab === 'manual'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Manual Input
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`px-3 py-1 text-sm rounded-md ${
                    activeTab === 'upload'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  File Upload
                </button>
              </div>
            </div>
          </div>
          
          <div className="p-6">
            {activeTab === 'manual' ? (
              <>
                <div className="mb-4 flex justify-between items-center">
                  <label className="block text-sm font-medium text-gray-700">
                    Patient Information (JSON Format)
                  </label>
                  <button
                    onClick={loadSampleData}
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    Load Sample Data
                  </button>
                </div>
                <textarea
                  value={patientData}
                  onChange={(e) => setPatientData(e.target.value)}
                  placeholder="Enter patient data in JSON format..."
                  className="w-full h-64 p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 font-mono text-sm mb-4"
                />

                <div className="flex items-center space-x-4">
                  <button
                    onClick={matchPatient}
                    disabled={loading || !patientData.trim()}
                    className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    <Search className="h-4 w-4" />
                    <span>{loading ? 'Matching...' : 'Find Trials'}</span>
                  </button>

                  <div className="flex items-center text-sm text-gray-500">
                    <User className="h-4 w-4 mr-1" />
                    <span>Data will be automatically anonymized</span>
                  </div>
                </div>
              </>
            ) : (
              <FileUpload
                uploadType="match"
                onUploadSuccess={handleFileUploadSuccess}
                onUploadError={handleFileUploadError}
              />
            )}

            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
                  <p className="text-red-700 text-sm">{error}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Results Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Matching Results</h2>
          </div>
          
          <div className="p-6">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600">Running AI analysis...</span>
              </div>
            )}

            {matchResults && (
              <div className="space-y-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-blue-900">Patient ID: {matchResults.patient_id}</p>
                      <p className="text-sm text-blue-700">
                        Found {matchResults.ranked_trials.length} potential matches
                      </p>
                    </div>
                    <FileText className="h-6 w-6 text-blue-600" />
                  </div>
                </div>

                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {matchResults.ranked_trials.map((trial, index) => (
                    <div key={trial.trial_id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded">
                              #{index + 1}
                            </span>
                            <h3 className="font-medium text-gray-900 text-sm">{trial.title}</h3>
                          </div>
                          <p className="text-xs text-gray-600">{trial.trial_id} • {trial.phase}</p>
                          <p className="text-xs text-gray-500 mt-1">{trial.location}</p>
                        </div>
                        
                        <div className="text-right ml-4">
                          <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            trial.eligibility_score > 0.7 
                              ? 'bg-green-100 text-green-800' 
                              : trial.eligibility_score > 0.4
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {trial.eligibility_score > 0.5 ? (
                              <CheckCircle className="w-3 h-3 mr-1" />
                            ) : (
                              <AlertCircle className="w-3 h-3 mr-1" />
                            )}
                            {Math.round(trial.eligibility_score * 100)}%
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Confidence: {Math.round(trial.confidence * 100)}%
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <h4 className="text-xs font-medium text-gray-700 mb-2">Eligibility Analysis:</h4>
                        <div className="space-y-1">
                          {trial.explanations.slice(0, 2).map((explanation: string, idx: number) => (
                            <p key={idx} className="text-xs text-gray-600">• {explanation}</p>
                          ))}
                          {trial.explanations.length > 2 && (
                            <p className="text-xs text-gray-500">
                              +{trial.explanations.length - 2} more criteria analyzed
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!loading && !matchResults && (
              <div className="text-center py-8 text-gray-500">
                <Upload className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>Enter patient data and click "Find Trials" to see matching results</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">How It Works</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="bg-blue-100 rounded-full p-3 w-12 h-12 mx-auto mb-3">
              <Upload className="h-6 w-6 text-blue-600" />
            </div>
            <h4 className="font-medium text-gray-900 mb-2">1. Upload Data</h4>
            <p className="text-sm text-gray-600">
              Provide patient information in JSON format. Data is automatically anonymized.
            </p>
          </div>
          
          <div className="text-center">
            <div className="bg-green-100 rounded-full p-3 w-12 h-12 mx-auto mb-3">
              <Search className="h-6 w-6 text-green-600" />
            </div>
            <h4 className="font-medium text-gray-900 mb-2">2. AI Analysis</h4>
            <p className="text-sm text-gray-600">
              Machine learning algorithms analyze eligibility criteria and match trials.
            </p>
          </div>
          
          <div className="text-center">
            <div className="bg-purple-100 rounded-full p-3 w-12 h-12 mx-auto mb-3">
              <FileText className="h-6 w-6 text-purple-600" />
            </div>
            <h4 className="font-medium text-gray-900 mb-2">3. Get Results</h4>
            <p className="text-sm text-gray-600">
              Receive ranked trial matches with explanations and confidence scores.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PatientMatcher
