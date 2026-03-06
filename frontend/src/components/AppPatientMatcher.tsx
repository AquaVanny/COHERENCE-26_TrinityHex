import { useState } from 'react'
import { AlertCircle, CheckCircle, FileText, Search, Upload, User } from 'lucide-react'
import axios from 'axios'
import FileUpload from './FileUpload'

interface RankedTrial {
  trial_id: string
  title: string
  phase: string
  location: string
  confidence: number
  eligibility_score: number
  explanations: string[]
}

interface MatchResult {
  patient_id: string
  ranked_trials: RankedTrial[]
  total_trials: number
}

const samplePatient = {
  patient_id: 'P005',
  name: 'Jane Doe',
  age: 52,
  gender: 'female',
  location: 'Chicago, IL',
  diagnosis: ['Type 2 Diabetes', 'Obesity'],
  diagnosis_date: '2023-06-15T00:00:00Z',
  medications: ['Metformin', 'Insulin'],
  lab_results: {
    hba1c: 9.1,
    glucose: 220,
    bmi: 32.5
  }
}

const AppPatientMatcher = () => {
  const [patientData, setPatientData] = useState('')
  const [matchResults, setMatchResults] = useState<MatchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'manual' | 'upload'>('manual')

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
      const patient = JSON.parse(patientData)
      const trialsResponse = await axios.get('http://localhost:5000/api/sample-data')
      const trials = trialsResponse.data.trials

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
    <div className="section-stack">
      <section className="glass-card hero-card">
        <h1 className="hero-title">Patient Trial Matcher</h1>
        <p className="hero-sub">
          Upload patient data files or enter data manually to find matching clinical trials with AI-powered analysis.
        </p>
      </section>

      <div className="split-grid">
        <section className="glass-card">
          <div className="card-header-row">
            <div className="section-title">
              <div className="section-icon">
                <User className="h-4 w-4" />
              </div>
              Patient Data Input
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="soft-button"
                onClick={() => setActiveTab('manual')}
                style={activeTab === 'manual' ? { background: 'rgba(96,165,250,0.15)', borderColor: 'rgba(96,165,250,0.4)' } : undefined}
              >
                Manual Input
              </button>
              <button
                type="button"
                className="soft-button"
                onClick={() => setActiveTab('upload')}
                style={activeTab === 'upload' ? { background: 'rgba(96,165,250,0.15)', borderColor: 'rgba(96,165,250,0.4)' } : undefined}
              >
                File Upload
              </button>
            </div>
          </div>

          <div className="card-body section-stack">
            {activeTab === 'manual' ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="text-[11px] font-bold uppercase tracking-[1.5px] muted-text">Patient Information (JSON Format)</div>
                  <button type="button" className="soft-button" onClick={loadSampleData}>
                    <Upload className="h-4 w-4" />
                    Load Sample Data
                  </button>
                </div>

                <textarea
                  value={patientData}
                  onChange={(e) => setPatientData(e.target.value)}
                  placeholder="Enter patient data in JSON format..."
                  className="code-input"
                />

                <div className="flex flex-wrap items-center gap-4">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={matchPatient}
                    disabled={loading || !patientData.trim()}
                  >
                    <Search className="h-4 w-4" />
                    {loading ? 'Matching...' : 'Find Trials'}
                  </button>

                  <div className="flex items-center gap-2 text-sm muted-text">
                    <User className="h-4 w-4" />
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
              <div className="rounded-[12px] border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-200">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="glass-card">
          <div className="card-header-row">
            <div className="section-title">
              <div className="section-icon">
                <Search className="h-4 w-4" />
              </div>
              Matching Results
            </div>
          </div>

          <div className="card-body">
            {loading ? (
              <div className="empty-state">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]"></div>
                <p>Running AI analysis...</p>
              </div>
            ) : matchResults ? (
              <div className="section-stack">
                <div className="status-panel">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-white">Patient ID: {matchResults.patient_id}</p>
                      <p className="text-sm muted-text">Found {matchResults.ranked_trials.length} potential matches</p>
                    </div>
                    <FileText className="h-6 w-6" style={{ color: 'var(--blue)' }} />
                  </div>
                </div>

                <div className="result-list max-h-[560px] overflow-y-auto pr-1">
                  {matchResults.ranked_trials.map((trial, index) => {
                    const high = trial.eligibility_score > 0.7
                    const mid = trial.eligibility_score > 0.4 && trial.eligibility_score <= 0.7

                    return (
                      <div key={trial.trial_id} className="rounded-[12px] border border-white/10 bg-[rgba(13,22,45,0.6)] p-5">
                        <div className="mb-3 flex items-start justify-between gap-3">
                          <div>
                            <div className="mb-1 flex items-center gap-2">
                              <span className="rounded bg-white/8 px-2 py-1 text-xs muted-text">#{index + 1}</span>
                              <h3 className="text-sm font-semibold text-white">{trial.title}</h3>
                            </div>
                            <p className="text-xs muted-text">{trial.trial_id} • {trial.phase}</p>
                            <p className="mt-1 text-xs muted-text">{trial.location}</p>
                          </div>

                          <div className="text-right">
                            <span
                              className="pill-badge"
                              style={{
                                background: high ? 'rgba(52,211,153,0.12)' : mid ? 'rgba(96,165,250,0.12)' : 'rgba(251,191,36,0.1)',
                                color: high ? 'var(--green)' : mid ? 'var(--blue)' : '#fbbf24',
                                border: `1px solid ${high ? 'rgba(52,211,153,0.25)' : mid ? 'rgba(96,165,250,0.25)' : 'rgba(251,191,36,0.2)'}`
                              }}
                            >
                              {trial.eligibility_score > 0.5 ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                              {Math.round(trial.eligibility_score * 100)}%
                            </span>
                            <p className="mt-1 text-xs muted-text">Confidence: {Math.round(trial.confidence * 100)}%</p>
                          </div>
                        </div>

                        <div className="border-t border-white/10 pt-3">
                          <h4 className="mb-2 text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Eligibility Analysis</h4>
                          <div className="space-y-2">
                            {trial.explanations.slice(0, 2).map((explanation, idx) => (
                              <div key={`${trial.trial_id}-${idx}`} className="flex items-start gap-3 text-xs mid-text">
                                <div className="mt-1.5 h-[5px] w-[5px] rounded-full bg-slate-400"></div>
                                <span>{explanation}</span>
                              </div>
                            ))}
                            {trial.explanations.length > 2 && (
                              <p className="text-xs muted-text">+{trial.explanations.length - 2} more criteria analyzed</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <Upload className="h-12 w-12 text-slate-500/60" />
                <p>Enter patient data and click "Find Trials" to see matching results.</p>
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="glass-card card-body">
        <div className="mb-10 text-center text-xl font-bold text-white">How It Works</div>
        <div className="triple-grid">
          {[
            {
              title: 'Upload Data',
              text: 'Provide patient information in JSON format. Data is automatically anonymized.',
              icon: Upload,
              color: 'var(--blue)',
              bg: 'rgba(96,165,250,0.1)'
            },
            {
              title: 'AI Analysis',
              text: 'Machine learning algorithms analyze eligibility criteria and match trials.',
              icon: Search,
              color: 'var(--green)',
              bg: 'rgba(52,211,153,0.1)'
            },
            {
              title: 'Get Results',
              text: 'Receive ranked trial matches with explanations and confidence scores.',
              icon: FileText,
              color: 'var(--purple)',
              bg: 'rgba(167,139,250,0.1)'
            }
          ].map((step, index) => (
            <div key={step.title} className="flex flex-col items-center gap-4 text-center">
              <div className="flex h-[70px] w-[70px] items-center justify-center rounded-full border" style={{ background: step.bg, borderColor: 'var(--border)', color: step.color }}>
                <step.icon className="h-7 w-7" />
              </div>
              <div className="text-[11px] font-bold uppercase tracking-[1px] muted-text">Step {index + 1}</div>
              <div className="text-[15px] font-bold text-white">{step.title}</div>
              <p className="max-w-[220px] text-sm muted-text">{step.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

export default AppPatientMatcher
