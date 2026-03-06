import { useState } from 'react'
import { AlertCircle, CheckCircle, FileText, Search, Upload, User } from 'lucide-react'
import axios from 'axios'
import FileUpload from './FileUpload'

interface RuleExplanation {
  text: string
  status: string
  icon: string
  is_exclusion: boolean
  criterion_type: string
}

interface ConfidenceBreakdown {
  confidence_tier: string
  fused_score_pct: number
  rule_score_pct: number
  ml_score_pct: number
  hard_exclusion: boolean
  criteria_summary: {
    total: number
    eligible: number
    ineligible: number
    unknown: number
  }
}

interface GeoInfo {
  distance_miles: number
  nearest_site: string
}

interface RankedTrial {
  trial_id: string
  title: string
  phase: string
  location: string
  sponsor: string
  overall_status: string
  fused_score: number
  confidence_tier: string
  rule_score: number
  ml_score: number
  hard_exclusion: boolean
  rule_explanations: RuleExplanation[]
  confidence_breakdown: ConfidenceBreakdown
  geographic_info: GeoInfo | null
  match_summary: string
  rank: number
  // Legacy compat
  confidence?: number
  eligibility_score?: number
  explanations?: string[]
}

interface MatchResult {
  patient_id: string
  ranked_matches: RankedTrial[]
  // Legacy compat
  ranked_trials?: RankedTrial[]
  total_trials?: number
  total_trials_evaluated?: number
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

      // Use v2 pipeline endpoint
      const matchResponse = await axios.post('http://localhost:5000/api/v2/match', {
        patient_data: patient
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
          ranked_matches: firstResult.ranked_matches || firstResult.ranked_trials,
          total_trials_evaluated: firstResult.total_trials_evaluated
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
                      <p className="text-sm muted-text">Found {(matchResults.ranked_matches || matchResults.ranked_trials || []).length} potential matches</p>
                    </div>
                    <FileText className="h-6 w-6" style={{ color: 'var(--blue)' }} />
                  </div>
                </div>

                <div className="result-list max-h-[560px] overflow-y-auto pr-1">
                  {(matchResults.ranked_matches || matchResults.ranked_trials || []).map((trial, index) => {
                    const score = trial.fused_score ?? trial.eligibility_score ?? 0
                    const high = score > 0.7
                    const mid = score > 0.4 && score <= 0.7
                    const tier = trial.confidence_tier || (high ? 'HIGH' : mid ? 'MEDIUM' : 'LOW')
                    const ruleExps = trial.rule_explanations || []
                    const legacyExps = trial.explanations || []

                    return (
                      <div key={trial.trial_id} className="rounded-[12px] border border-white/10 bg-[rgba(13,22,45,0.6)] p-5">
                        <div className="mb-3 flex items-start justify-between gap-3">
                          <div>
                            <div className="mb-1 flex items-center gap-2">
                              <span className="rounded bg-white/8 px-2 py-1 text-xs muted-text">#{trial.rank || index + 1}</span>
                              <h3 className="text-sm font-semibold text-white">{trial.title}</h3>
                            </div>
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                              <span className="muted-text">{trial.trial_id} • {trial.phase}</span>
                              {trial.overall_status && (
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                                  trial.overall_status === 'ELIGIBLE' ? 'bg-green-400/10 text-green-300'
                                  : trial.overall_status === 'INELIGIBLE' ? 'bg-red-400/10 text-red-300'
                                  : 'bg-yellow-400/10 text-yellow-300'
                                }`}>{trial.overall_status}</span>
                              )}
                            </div>
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
                              {score > 0.5 ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                              {Math.round(score * 100)}%
                            </span>
                            <p className="mt-1 text-xs muted-text">{tier} Confidence</p>
                          </div>
                        </div>

                        {/* Score breakdown */}
                        {trial.confidence_breakdown && (
                          <div className="mb-3 flex items-center gap-3 text-[10px] muted-text">
                            <span>Rule {trial.confidence_breakdown.rule_score_pct}%</span>
                            <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/5">
                              <div className="flex h-full">
                                <div className="h-full bg-blue-400/60" style={{ width: `${trial.confidence_breakdown.rule_score_pct * 0.6}%` }}></div>
                                <div className="h-full bg-purple-400/60" style={{ width: `${trial.confidence_breakdown.ml_score_pct * 0.4}%` }}></div>
                              </div>
                            </div>
                            <span>ML {trial.confidence_breakdown.ml_score_pct}%</span>
                          </div>
                        )}

                        {/* Geographic info */}
                        {trial.geographic_info && (
                          <div className="mb-2 text-xs muted-text">
                            Nearest site: {trial.geographic_info.nearest_site} ({trial.geographic_info.distance_miles} mi)
                          </div>
                        )}

                        <div className="border-t border-white/10 pt-3">
                          <h4 className="mb-2 text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Eligibility Analysis</h4>
                          <div className="space-y-2">
                            {ruleExps.length > 0
                              ? ruleExps.slice(0, 4).map((exp, idx) => (
                                  <div key={`${trial.trial_id}-r-${idx}`} className="flex items-start gap-2 text-xs">
                                    <span className="mt-0.5 flex-shrink-0">{exp.icon}</span>
                                    <span className={exp.status === 'ELIGIBLE' ? 'text-green-300' : exp.status === 'INELIGIBLE' ? 'text-red-300' : 'text-yellow-300'}>
                                      {exp.text}
                                    </span>
                                  </div>
                                ))
                              : legacyExps.slice(0, 2).map((explanation, idx) => (
                                  <div key={`${trial.trial_id}-${idx}`} className="flex items-start gap-3 text-xs mid-text">
                                    <div className="mt-1.5 h-[5px] w-[5px] rounded-full bg-slate-400"></div>
                                    <span>{explanation}</span>
                                  </div>
                                ))
                            }
                            {ruleExps.length > 4 && (
                              <p className="text-xs muted-text">+{ruleExps.length - 4} more criteria analyzed</p>
                            )}
                          </div>
                        </div>

                        {trial.match_summary && (
                          <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-2.5 text-[11px] italic muted-text">
                            {trial.match_summary}
                          </div>
                        )}
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
