import { useEffect, useState } from 'react'
import { Activity, AlertCircle, CheckCircle, FileText, TrendingUp, Users } from 'lucide-react'
import axios from 'axios'
import NearbyTrialsMap from './NearbyTrialsMap'

interface Patient {
  patient_id: string
  age_range: string
  gender: string
  region: string
  diagnosis?: string[]
  medications?: string[]
  lab_results?: Record<string, any>
}

interface PatientSummary {
  index: number
  patient_id: string
  age_range: string
  gender: string
  region: string
  diagnosis_count: number
  medication_count: number
}

interface RuleExplanation {
  text: string
  status: string
  icon: string
  is_exclusion: boolean
  criterion_type: string
}

interface ConfidenceBreakdown {
  confidence_tier: string
  fused_score: number
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

interface DemoMatch {
  trial_id: string
  title: string
  phase: string
  sponsor: string
  location: string
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
  eligibility_score?: number
  confidence?: number
  explanations?: string[]
}

interface MatchResult {
  patient: Patient
  patient_index: number
  total_patients_available: number
  top_matches: DemoMatch[]
  all_matches: DemoMatch[]
  total_trials_evaluated: number
}

const AppDashboard = () => {
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null)
  const [availablePatients, setAvailablePatients] = useState<PatientSummary[]>([])
  const [selectedPatientIndex, setSelectedPatientIndex] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadPatients = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/v2/patients')
      setAvailablePatients(response.data.patients)
    } catch (err) {
      console.error('Failed to load patients:', err)
    }
  }

  const runMatching = async (patientIndex?: number) => {
    setLoading(true)
    setError(null)

    try {
      const url = patientIndex !== undefined 
        ? `http://localhost:5000/api/v2/demo-match?patient_index=${patientIndex}`
        : 'http://localhost:5000/api/v2/demo-match'
      const response = await axios.get(url)
      setMatchResult(response.data)
      setSelectedPatientIndex(response.data.patient_index)
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to run matching')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPatients()
    runMatching()
  }, [])

  const stats = [
    { 
      title: 'Patients in Database', 
      value: matchResult?.total_patients_available?.toString() || '0', 
      icon: Users, 
      color: 'rgba(96,165,250,0.12)', 
      iconColor: 'var(--blue)' 
    },
    { 
      title: 'Clinical Trials', 
      value: matchResult?.total_trials_evaluated?.toString() || '5', 
      icon: FileText, 
      color: 'rgba(52,211,153,0.12)', 
      iconColor: 'var(--green)' 
    },
    {
      title: 'Eligible Matches',
      value: matchResult ? matchResult.all_matches.filter((t) => (t.fused_score ?? t.eligibility_score ?? 0) > 0.5).length.toString() : '0',
      icon: TrendingUp,
      color: 'rgba(167,139,250,0.12)',
      iconColor: 'var(--purple)'
    },
    {
      title: 'Top Match Score',
      value: matchResult ? `${matchResult.top_matches[0]?.confidence_breakdown?.fused_score_pct ?? Math.round((matchResult.top_matches[0]?.fused_score || 0) * 100)}%` : '0%',
      icon: Activity,
      color: 'rgba(251,146,60,0.12)',
      iconColor: 'var(--orange)'
    }
  ]

  return (
    <div className="section-stack">
      <section className="glass-card hero-card">
        <h1 className="hero-title">Clinical Trial Matching Platform</h1>
        <p className="hero-sub">
          AI-powered system matching {matchResult?.total_patients_available || 250} anonymized patient records to {matchResult?.total_trials_evaluated || 12} active clinical trials using hybrid rule-based and machine learning algorithms with geographic proximity filtering.
        </p>
      </section>

      <section className="quad-grid">
        {stats.map((stat) => (
          <div key={stat.title} className="glass-card card-body">
            <div className="flex items-center gap-4">
              <div
                className="flex h-12 w-12 items-center justify-center rounded-xl border"
                style={{ background: stat.color, borderColor: 'var(--border)', color: stat.iconColor }}
              >
                <stat.icon className="h-6 w-6" />
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[1.2px] muted-text">{stat.title}</div>
                <div className="text-2xl font-bold text-white">{stat.value}</div>
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="glass-card">
        <div className="card-header-row">
          <div className="section-title">
            <div className="section-icon">
              <Activity className="h-4 w-4" />
            </div>
            Patient Matching Results
          </div>
          <div className="flex items-center gap-3">
            {availablePatients.length > 0 && (
              <select 
                value={selectedPatientIndex ?? ''} 
                onChange={(e) => runMatching(parseInt(e.target.value))}
                className="field-select"
                style={{ minWidth: '200px' }}
              >
                <option value="">Random Patient</option>
                {availablePatients.slice(0, 20).map((p) => (
                  <option key={p.index} value={p.index}>
                    {p.patient_id} ({p.age_range}, {p.gender})
                  </option>
                ))}
              </select>
            )}
            <button type="button" className="soft-button" onClick={() => runMatching()} disabled={loading}>
              <Activity className="h-4 w-4" />
              {loading ? 'Analyzing...' : 'Run Matching'}
            </button>
          </div>
        </div>

        <div className="card-body section-stack">
          {error && (
            <div className="rounded-[12px] border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-200">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            </div>
          )}

          {loading && !matchResult && (
            <div className="empty-state">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]"></div>
              <p>Running AI matching algorithm...</p>
            </div>
          )}

          {matchResult && (
            <>
              <div className="status-panel">
                <div className="mb-4 text-[11px] font-bold uppercase tracking-[1.5px]" style={{ color: 'var(--blue)' }}>
                  Patient Profile (Anonymized)
                </div>
                <div className="info-grid">
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Patient ID</div>
                    <div className="mt-1 font-mono text-sm" style={{ color: 'var(--blue)' }}>{matchResult.patient.patient_id}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Age Range</div>
                    <div className="mt-1 text-sm text-white">{matchResult.patient.age_range}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Gender</div>
                    <div className="mt-1 text-sm text-white">{matchResult.patient.gender}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Region</div>
                    <div className="mt-1 text-sm text-white">{matchResult.patient.region}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Conditions</div>
                    <div className="mt-1 text-sm text-white">{matchResult.patient.diagnosis?.length || 0}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Medications</div>
                    <div className="mt-1 text-sm text-white">{matchResult.patient.medications?.length || 0}</div>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-4 flex items-center gap-3 text-[13px] font-bold uppercase tracking-[1.5px] mid-text">
                  <span>Top Trial Matches</span>
                  <div className="h-px flex-1 bg-[linear-gradient(90deg,rgba(255,255,255,0.08),transparent)]"></div>
                </div>

                <div className="result-list">
                  {matchResult.top_matches.map((trial) => {
                    const score = trial.fused_score ?? trial.eligibility_score ?? 0
                    const high = score > 0.7
                    const mid = score > 0.4 && score <= 0.7
                    const tier = trial.confidence_tier || (high ? 'HIGH' : mid ? 'MEDIUM' : 'LOW')
                    const ruleExplanations = trial.rule_explanations || []
                    const legacyExplanations = trial.explanations || []

                    return (
                      <div key={trial.trial_id} className="rounded-[12px] border border-white/10 bg-[rgba(13,22,45,0.6)] p-6">
                        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                          <div>
                            <div className="text-[15px] font-bold text-white">{trial.title}</div>
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                              <span className="rounded-md border border-blue-400/20 bg-blue-400/10 px-2 py-1 font-mono" style={{ color: 'var(--blue)' }}>
                                {trial.trial_id}
                              </span>
                              <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1 muted-text">
                                {trial.phase}
                              </span>
                              {trial.overall_status && (
                                <span className={`rounded-md px-2 py-1 text-xs font-semibold ${
                                  trial.overall_status === 'ELIGIBLE' ? 'border border-green-400/20 bg-green-400/10 text-green-300'
                                  : trial.overall_status === 'INELIGIBLE' ? 'border border-red-400/20 bg-red-400/10 text-red-300'
                                  : 'border border-yellow-400/20 bg-yellow-400/10 text-yellow-300'
                                }`}>
                                  {trial.overall_status}
                                </span>
                              )}
                            </div>
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
                              {high ? <CheckCircle className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                              {Math.round(score * 100)}% Match
                            </span>
                            <div className="mt-1 text-xs muted-text">{tier} Confidence</div>
                          </div>
                        </div>

                        {/* Score breakdown bar */}
                        {trial.confidence_breakdown && (
                          <div className="mb-4 flex items-center gap-3 text-xs muted-text">
                            <span>Rule: {trial.confidence_breakdown.rule_score_pct}%</span>
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                              <div className="flex h-full">
                                <div className="h-full bg-blue-400/60" style={{ width: `${trial.confidence_breakdown.rule_score_pct * 0.6}%` }}></div>
                                <div className="h-full bg-purple-400/60" style={{ width: `${trial.confidence_breakdown.ml_score_pct * 0.4}%` }}></div>
                              </div>
                            </div>
                            <span>ML: {trial.confidence_breakdown.ml_score_pct}%</span>
                          </div>
                        )}

                        {/* Geographic info */}
                        {trial.geographic_info && (
                          <div className="mb-3 flex items-center gap-2 text-xs muted-text">
                            <span>📍</span>
                            <span>{trial.geographic_info.nearest_site} — {trial.geographic_info.distance_miles} miles away</span>
                          </div>
                        )}

                        <div className="text-[11.5px] font-bold uppercase tracking-[0.8px] muted-text">Eligibility Analysis</div>
                        <div className="mt-3 flex flex-col gap-2">
                          {ruleExplanations.length > 0
                            ? ruleExplanations.slice(0, 4).map((exp, idx) => (
                                <div key={`${trial.trial_id}-r-${idx}`} className="flex items-start gap-3 text-sm">
                                  <span className="mt-0.5 flex-shrink-0 text-sm">{exp.icon}</span>
                                  <span className={exp.status === 'ELIGIBLE' ? 'text-green-300' : exp.status === 'INELIGIBLE' ? 'text-red-300' : 'text-yellow-300'}>
                                    {exp.text}
                                  </span>
                                </div>
                              ))
                            : legacyExplanations.slice(0, 3).map((explanation, idx) => (
                                <div key={`${trial.trial_id}-${idx}`} className="flex items-start gap-3 text-sm mid-text">
                                  <div className="mt-2 h-[5px] w-[5px] flex-shrink-0 rounded-full bg-slate-400"></div>
                                  <span>{explanation}</span>
                                </div>
                              ))
                          }
                        </div>

                        {/* Match summary */}
                        {trial.match_summary && (
                          <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs italic muted-text">
                            {trial.match_summary}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      <NearbyTrialsMap patientIndex={selectedPatientIndex} />

      <section className="triple-grid">
        {[
          {
            title: 'Real Patient Data',
            text: `Analyzed ${matchResult?.total_patients_available || 50} real anonymized patient records from clinical health system data with comprehensive medical histories.`,
            icon: Users,
            color: 'var(--blue)',
            bg: 'rgba(96,165,250,0.1)'
          },
          {
            title: 'Hybrid AI Matching',
            text: 'Combines rule-based eligibility filtering (60%) with XGBoost ML scoring (40%) for accurate, explainable trial matching.',
            icon: Activity,
            color: 'var(--green)',
            bg: 'rgba(52,211,153,0.1)'
          },
          {
            title: 'Transparent Explanations',
            text: 'Per-criterion justifications, SHAP feature importance, confidence tiers, and geographic distance for every match.',
            icon: FileText,
            color: 'var(--purple)',
            bg: 'rgba(167,139,250,0.1)'
          }
        ].map((feature) => {
          const Icon = feature.icon
          return (
            <div key={feature.title} className="glass-card card-body">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full border" style={{ background: feature.bg, borderColor: 'var(--border)', color: feature.color }}>
                  <Icon className="h-6 w-6" />
                </div>
                <div className="text-lg font-semibold text-white">{feature.title}</div>
              </div>
              <p className="text-sm muted-text">{feature.text}</p>
            </div>
          )
        })}
      </section>
    </div>
  )
}

export default AppDashboard
