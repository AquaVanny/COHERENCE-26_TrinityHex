import { useEffect, useState } from 'react'
import { Activity, AlertCircle, CheckCircle, FileText, TrendingUp, Users } from 'lucide-react'
import axios from 'axios'

interface DemoPatient {
  patient_id: string
  age_range: string
  gender: string
  region: string
}

interface DemoMatch {
  trial_id: string
  title: string
  phase: string
  eligibility_score: number
  confidence: number
  explanations: string[]
}

interface DemoResult {
  demo_patient: DemoPatient
  top_matches: DemoMatch[]
  total_trials_evaluated: number
}

const AppDashboard = () => {
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
    { title: 'Total Patients', value: '4', icon: Users, color: 'rgba(96,165,250,0.12)', iconColor: 'var(--blue)' },
    { title: 'Active Trials', value: '5', icon: FileText, color: 'rgba(52,211,153,0.12)', iconColor: 'var(--green)' },
    {
      title: 'Successful Matches',
      value: demoResult ? demoResult.top_matches.filter((t) => t.eligibility_score > 0.5).length.toString() : '0',
      icon: TrendingUp,
      color: 'rgba(167,139,250,0.12)',
      iconColor: 'var(--purple)'
    },
    {
      title: 'AI Confidence',
      value: demoResult ? `${Math.round((demoResult.top_matches[0]?.confidence || 0) * 100)}%` : '0%',
      icon: Activity,
      color: 'rgba(251,146,60,0.12)',
      iconColor: 'var(--orange)'
    }
  ]

  return (
    <div className="section-stack">
      <section className="glass-card hero-card">
        <h1 className="hero-title">AI-Powered Clinical Trial Matching Engine</h1>
        <p className="hero-sub">
          Intelligent infrastructure for matching anonymized patient records to the most relevant clinical trials.
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
            Live Demo Results
          </div>
          <button type="button" className="soft-button" onClick={runDemo} disabled={loading}>
            <Activity className="h-4 w-4" />
            {loading ? 'Running Demo...' : 'Run Demo'}
          </button>
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

          {loading && !demoResult && (
            <div className="empty-state">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]"></div>
              <p>Running AI matching algorithm...</p>
            </div>
          )}

          {demoResult && (
            <>
              <div className="status-panel">
                <div className="mb-4 text-[11px] font-bold uppercase tracking-[1.5px]" style={{ color: 'var(--blue)' }}>
                  Anonymized Patient Profile
                </div>
                <div className="info-grid">
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">ID</div>
                    <div className="mt-1 font-mono text-sm" style={{ color: 'var(--blue)' }}>{demoResult.demo_patient.patient_id}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Age Range</div>
                    <div className="mt-1 text-sm text-white">{demoResult.demo_patient.age_range}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Gender</div>
                    <div className="mt-1 text-sm text-white">{demoResult.demo_patient.gender}</div>
                  </div>
                  <div>
                    <div className="text-[10.5px] font-semibold uppercase tracking-[1px] muted-text">Region</div>
                    <div className="mt-1 text-sm text-white">{demoResult.demo_patient.region}</div>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-4 flex items-center gap-3 text-[13px] font-bold uppercase tracking-[1.5px] mid-text">
                  <span>Top Trial Matches</span>
                  <div className="h-px flex-1 bg-[linear-gradient(90deg,rgba(255,255,255,0.08),transparent)]"></div>
                </div>

                <div className="result-list">
                  {demoResult.top_matches.map((trial) => {
                    const high = trial.eligibility_score > 0.7
                    const mid = trial.eligibility_score > 0.4 && trial.eligibility_score <= 0.7

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
                              {Math.round(trial.eligibility_score * 100)}% Match
                            </span>
                            <div className="mt-1 text-xs muted-text">{Math.round(trial.confidence * 100)}% Confidence</div>
                          </div>
                        </div>

                        <div className="text-[11.5px] font-bold uppercase tracking-[0.8px] muted-text">Eligibility Analysis</div>
                        <div className="mt-3 flex flex-col gap-2">
                          {trial.explanations.slice(0, 3).map((explanation, idx) => (
                            <div key={`${trial.trial_id}-${idx}`} className="flex items-start gap-3 text-sm mid-text">
                              <div className="mt-2 h-[5px] w-[5px] flex-shrink-0 rounded-full bg-slate-400"></div>
                              <span>{explanation}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      <section className="triple-grid">
        {[
          {
            title: 'Patient Anonymization',
            text: 'Advanced anonymization preserves clinical relevance while protecting patient privacy.',
            icon: Users,
            color: 'var(--blue)',
            bg: 'rgba(96,165,250,0.1)'
          },
          {
            title: 'AI Matching',
            text: 'Machine learning algorithms analyze eligibility criteria and patient data for optimal matches.',
            icon: Activity,
            color: 'var(--green)',
            bg: 'rgba(52,211,153,0.1)'
          },
          {
            title: 'Explainable Results',
            text: 'Transparent explanations and confidence scores support every match recommendation.',
            icon: FileText,
            color: 'var(--purple)',
            bg: 'rgba(167,139,250,0.1)'
          }
        ].map((feature) => (
          <div key={feature.title} className="glass-card card-body">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full border" style={{ background: feature.bg, borderColor: 'var(--border)', color: feature.color }}>
                <feature.icon className="h-6 w-6" />
              </div>
              <div className="text-lg font-semibold text-white">{feature.title}</div>
            </div>
            <p className="text-sm muted-text">{feature.text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}

export default AppDashboard
