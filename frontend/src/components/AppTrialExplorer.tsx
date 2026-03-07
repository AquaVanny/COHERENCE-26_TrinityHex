import { useEffect, useMemo, useState } from 'react'
import { Calendar, Download, FileText, Filter, MapPin, Search, Users, ChevronDown, ChevronUp } from 'lucide-react'
import axios from 'axios'

interface ParsedCriterion {
  field: string
  operator?: string
  value?: any
  code?: string
  system?: string
  display?: string
  name?: string
  within_months?: number
  unit?: string
}

interface ParsedCriteria {
  inclusion: ParsedCriterion[]
  exclusion: ParsedCriterion[]
  parse_confidence: number
  low_confidence_flags: string[]
}

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
  const [selectedLocation, setSelectedLocation] = useState('')
  const [expandedCriteria, setExpandedCriteria] = useState<Record<string, ParsedCriteria | null>>({})
  const [parsingId, setParsingId] = useState<string | null>(null)

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
      const matchesLocation = !selectedLocation || trial.location.toLowerCase().includes(selectedLocation.toLowerCase())

      return matchesSearch && matchesPhase && matchesCondition && matchesLocation
    })
  }, [trials, searchTerm, selectedPhase, selectedCondition, selectedLocation])

  const phases = [...new Set(trials.map((trial) => trial.phase))]
  const conditions = [...new Set(trials.map((trial) => trial.condition))]
  const locations = useMemo(() => {
    const locs = new Set<string>()
    trials.forEach((t) => {
      t.location.split(/[;,]/).forEach((l) => {
        const trimmed = l.trim()
        if (trimmed && trimmed !== 'Multiple US locations') locs.add(trimmed)
      })
    })
    return [...locs].sort()
  }, [trials])

  const parseCriteria = async (trialId: string, criteriaText: string) => {
    if (expandedCriteria[trialId] !== undefined) {
      setExpandedCriteria((prev) => {
        const next = { ...prev }
        delete next[trialId]
        return next
      })
      return
    }
    setParsingId(trialId)
    try {
      const res = await axios.post('http://localhost:5000/api/v2/parse-criteria', {
        criteria_text: criteriaText
      })
      setExpandedCriteria((prev) => ({ ...prev, [trialId]: res.data.parsed_criteria }))
    } catch {
      setExpandedCriteria((prev) => ({ ...prev, [trialId]: null }))
    } finally {
      setParsingId(null)
    }
  }

  const exportTrials = () => {
    const blob = new Blob([JSON.stringify(filteredTrials, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `clinical_trials_export_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatCriterion = (c: ParsedCriterion): string => {
    if (c.field === 'age') {
      if (c.operator === 'between' && Array.isArray(c.value)) return `Age ${c.value[0]}-${c.value[1]} years`
      return `Age ${c.operator} ${c.value}`
    }
    if (c.field === 'diagnosis') return `${c.display || c.code} (${c.system})`
    if (c.field === 'lab') {
      if (c.operator === 'between' && Array.isArray(c.value)) return `${c.name} ${c.value[0]}-${c.value[1]}`
      return `${c.name} ${c.operator} ${c.value ?? ''}`
    }
    if (c.field === 'medication') {
      const time = c.within_months ? ` (within ${c.within_months} months)` : ''
      return `${c.operator === 'not_taking' ? 'No ' : ''}${c.name}${time}`
    }
    if (c.field === 'gender') return `Gender: ${c.value}`
    return `${c.field}: ${c.operator || ''} ${c.value ?? ''}`
  }

  return (
    <div className="section-stack">
      <section className="glass-card hero-card">
        <h1 className="hero-title">TrialMaxxAI — Trial Explorer</h1>
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

          <div className="quad-grid">
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

            <div>
              <label className="mb-2 block text-[11px] font-bold uppercase tracking-[1.2px] muted-text">Location</label>
              <select value={selectedLocation} onChange={(e) => setSelectedLocation(e.target.value)} className="field-select">
                <option value="">All Locations</option>
                {locations.map((loc) => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
            <div className="flex items-center gap-2 text-sm muted-text">
              <div className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--green)', boxShadow: '0 0 8px var(--green)' }}></div>
              Showing <strong style={{ color: 'var(--blue)' }}>{filteredTrials.length}</strong> of <strong style={{ color: 'var(--blue)' }}>{trials.length}</strong> trials
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="soft-button"
                onClick={() => {
                  setSearchTerm('')
                  setSelectedPhase('')
                  setSelectedCondition('')
                  setSelectedLocation('')
                }}
              >
                Clear Filters
              </button>
              <button
                type="button"
                className="soft-button"
                onClick={exportTrials}
                disabled={filteredTrials.length === 0}
              >
                <Download className="h-4 w-4" />
                Export JSON
              </button>
            </div>
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

              {/* Parsed Criteria Panel */}
              {expandedCriteria[trial.trial_id] !== undefined && (
                <div className="mt-4 rounded-[10px] border border-white/10 bg-[rgba(8,14,30,0.5)] p-4">
                  {expandedCriteria[trial.trial_id] ? (
                    <>
                      <div className="mb-3 flex items-center justify-between">
                        <div className="text-[11px] font-bold uppercase tracking-[1.2px]" style={{ color: 'var(--green)' }}>Parsed Criteria (NLP)</div>
                        <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1 text-[10px] muted-text">
                          Confidence: {Math.round((expandedCriteria[trial.trial_id]!.parse_confidence) * 100)}%
                        </span>
                      </div>
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <div className="mb-2 text-[10px] font-bold uppercase tracking-[1px] text-green-300">Inclusion ({expandedCriteria[trial.trial_id]!.inclusion.length})</div>
                          <div className="space-y-1.5">
                            {expandedCriteria[trial.trial_id]!.inclusion.map((c, i) => (
                              <div key={`inc-${i}`} className="flex items-start gap-2 text-xs text-green-200/80">
                                <span className="mt-0.5">✓</span>
                                <span>{formatCriterion(c)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div className="mb-2 text-[10px] font-bold uppercase tracking-[1px] text-red-300">Exclusion ({expandedCriteria[trial.trial_id]!.exclusion.length})</div>
                          <div className="space-y-1.5">
                            {expandedCriteria[trial.trial_id]!.exclusion.map((c, i) => (
                              <div key={`exc-${i}`} className="flex items-start gap-2 text-xs text-red-200/80">
                                <span className="mt-0.5">✗</span>
                                <span>{formatCriterion(c)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                      {expandedCriteria[trial.trial_id]!.low_confidence_flags.length > 0 && (
                        <div className="mt-3 space-y-1">
                          {expandedCriteria[trial.trial_id]!.low_confidence_flags.map((flag, i) => (
                            <div key={`flag-${i}`} className="flex items-start gap-2 text-[11px] text-yellow-300/70">
                              <span className="mt-0.5">⚠</span>
                              <span>{flag}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-xs text-red-300">Failed to parse criteria</div>
                  )}
                </div>
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
                <div className="text-xs muted-text">Last updated: {new Date().toLocaleDateString()}</div>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => parseCriteria(trial.trial_id, trial.eligibility_criteria)}
                  disabled={parsingId === trial.trial_id}
                >
                  {parsingId === trial.trial_id ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white"></div>
                  ) : expandedCriteria[trial.trial_id] !== undefined ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                  {expandedCriteria[trial.trial_id] !== undefined ? 'Hide Parsed Criteria' : 'Parse Criteria (NLP)'}
                </button>
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
