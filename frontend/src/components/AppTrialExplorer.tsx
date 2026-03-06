import { useEffect, useMemo, useState } from 'react'
import { Calendar, FileText, Filter, MapPin, Search, Users } from 'lucide-react'
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

const AppTrialExplorer = () => {
  const [trials, setTrials] = useState<Trial[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPhase, setSelectedPhase] = useState('')
  const [selectedCondition, setSelectedCondition] = useState('')

  useEffect(() => {
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

    loadTrials()
  }, [])

  const filteredTrials = useMemo(() => {
    return trials.filter((trial) => {
      const matchesSearch = !searchTerm ||
        trial.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trial.condition.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trial.sponsor.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesPhase = !selectedPhase || trial.phase === selectedPhase
      const matchesCondition = !selectedCondition || trial.condition.toLowerCase().includes(selectedCondition.toLowerCase())

      return matchesSearch && matchesPhase && matchesCondition
    })
  }, [trials, searchTerm, selectedPhase, selectedCondition])

  const phases = [...new Set(trials.map((trial) => trial.phase))]
  const conditions = [...new Set(trials.map((trial) => trial.condition))]

  return (
    <div className="section-stack">
      <section className="glass-card hero-card">
        <h1 className="hero-title">Clinical Trial Explorer</h1>
        <p className="hero-sub">Browse and search available clinical trials with detailed eligibility criteria.</p>
      </section>

      <section className="glass-card">
        <div className="card-body">
          <div className="mb-6 flex items-center gap-3">
            <div className="section-icon" style={{ background: 'rgba(167,139,250,0.1)', borderColor: 'rgba(167,139,250,0.2)', color: 'var(--purple)' }}>
              <Filter className="h-4 w-4" />
            </div>
            <div className="section-title">Search &amp; Filter</div>
          </div>

          <div className="triple-grid">
            <div>
              <label className="mb-2 block text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Search Trials</label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 muted-text" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by title, condition..."
                  className="field-input pl-10"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Phase</label>
              <select value={selectedPhase} onChange={(e) => setSelectedPhase(e.target.value)} className="field-select">
                <option value="">All Phases</option>
                {phases.map((phase) => (
                  <option key={phase} value={phase}>{phase}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Condition</label>
              <select value={selectedCondition} onChange={(e) => setSelectedCondition(e.target.value)} className="field-select">
                <option value="">All Conditions</option>
                {conditions.map((condition) => (
                  <option key={condition} value={condition}>{condition}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
            <div className="flex items-center gap-2 text-sm muted-text">
              <div className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--green)', boxShadow: '0 0 8px var(--green)' }}></div>
              Showing <strong style={{ color: 'var(--blue)' }}>{filteredTrials.length}</strong> of <strong style={{ color: 'var(--blue)' }}>{trials.length}</strong> trials
            </div>
            <button
              type="button"
              className="soft-button"
              onClick={() => {
                setSearchTerm('')
                setSelectedPhase('')
                setSelectedCondition('')
              }}
            >
              Clear Filters
            </button>
          </div>
        </div>
      </section>

      <section className="trial-list">
        {loading ? (
          <div className="glass-card card-body">
            <div className="empty-state">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]"></div>
              <p>Loading trials...</p>
            </div>
          </div>
        ) : filteredTrials.length > 0 ? (
          filteredTrials.map((trial, index) => (
            <div key={trial.trial_id} className="glass-card card-body">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-lg font-semibold text-white">{trial.title}</div>
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-sm muted-text">
                    <span className="flex items-center gap-1.5 font-mono" style={{ color: index % 2 === 0 ? 'var(--blue)' : 'var(--purple)' }}>
                      <FileText className="h-4 w-4" />
                      {trial.trial_id}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="h-4 w-4" />
                      {trial.phase}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Users className="h-4 w-4" />
                      {trial.estimated_enrollment} participants
                    </span>
                  </div>
                </div>

                <span
                  className="pill-badge"
                  style={{
                    background: trial.status === 'Recruiting' ? 'rgba(52,211,153,0.1)' : 'rgba(255,255,255,0.08)',
                    color: trial.status === 'Recruiting' ? 'var(--green)' : 'var(--text-mid)',
                    border: `1px solid ${trial.status === 'Recruiting' ? 'rgba(52,211,153,0.22)' : 'rgba(255,255,255,0.12)'}`
                  }}
                >
                  {trial.status}
                </span>
              </div>

              <div className="split-grid border-t border-white/10 pt-5">
                <div>
                  <div className="mb-3 text-[11px] font-bold uppercase tracking-[1.4px]" style={{ color: 'var(--blue)' }}>Study Details</div>
                  <div className="space-y-2 text-sm muted-text">
                    <div><span className="font-semibold mid-text">Condition:</span> {trial.condition}</div>
                    <div><span className="font-semibold mid-text">Sponsor:</span> {trial.sponsor}</div>
                    <div className="flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4" style={{ color: 'var(--orange)' }} /> <span>{trial.location}</span></div>
                  </div>
                </div>

                <div>
                  <div className="mb-3 text-[11px] font-bold uppercase tracking-[1.4px]" style={{ color: 'var(--purple)' }}>Eligibility Criteria</div>
                  <p className="text-sm muted-text" style={{ lineHeight: 1.75 }}>{trial.eligibility_criteria}</p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
                <div className="text-xs muted-text">Last updated: {new Date().toLocaleDateString()}</div>
                <button type="button" className="primary-button">View Full Details</button>
              </div>
            </div>
          ))
        ) : (
          <div className="glass-card card-body">
            <div className="empty-state">
              <Search className="h-12 w-12 text-slate-500/60" />
              <div>
                <p>No trials found matching your criteria</p>
                <p className="mt-1 text-sm">Try adjusting your search filters.</p>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

export default AppTrialExplorer
