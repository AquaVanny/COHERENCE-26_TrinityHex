import { useEffect, useState } from 'react'
import { Plus, Edit2, Trash2, Save, X, FileText, AlertCircle, CheckCircle } from 'lucide-react'
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
  primary_outcome: string
  estimated_enrollment: number
  study_start_date: string
  estimated_completion: string
}

const EMPTY_TRIAL: Trial = {
  trial_id: '',
  title: '',
  phase: 'Phase I',
  sponsor: '',
  location: '',
  status: 'Recruiting',
  condition: '',
  eligibility_criteria: '',
  primary_outcome: '',
  estimated_enrollment: 0,
  study_start_date: '',
  estimated_completion: ''
}

const TrialManagement = () => {
  const [trials, setTrials] = useState<Trial[]>([])
  const [loading, setLoading] = useState(false)
  const [editingTrial, setEditingTrial] = useState<Trial | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const loadTrials = async () => {
    setLoading(true)
    try {
      const res = await axios.get('http://localhost:5000/api/v2/trials')
      setTrials(res.data.trials)
    } catch (err) {
      console.error('Failed to load trials:', err)
      showMessage('error', 'Failed to load trials')
    } finally {
      setLoading(false)
    }
  }

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleCreate = () => {
    setEditingTrial({ ...EMPTY_TRIAL })
    setIsCreating(true)
  }

  const handleEdit = (trial: Trial) => {
    setEditingTrial({ ...trial })
    setIsCreating(false)
  }

  const handleCancel = () => {
    setEditingTrial(null)
    setIsCreating(false)
  }

  const handleSave = async () => {
    if (!editingTrial) return

    try {
      if (isCreating) {
        await axios.post('http://localhost:5000/api/v2/trials', editingTrial)
        showMessage('success', `Trial ${editingTrial.trial_id} created successfully`)
      } else {
        await axios.put('http://localhost:5000/api/v2/trials', editingTrial)
        showMessage('success', `Trial ${editingTrial.trial_id} updated successfully`)
      }
      setEditingTrial(null)
      setIsCreating(false)
      loadTrials()
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Failed to save trial'
      showMessage('error', errorMsg)
    }
  }

  const handleDelete = async (trialId: string) => {
    if (!confirm(`Are you sure you want to delete trial ${trialId}?`)) return

    try {
      await axios.delete(`http://localhost:5000/api/v2/trials?trial_id=${trialId}`)
      showMessage('success', `Trial ${trialId} deleted successfully`)
      loadTrials()
    } catch (err) {
      showMessage('error', 'Failed to delete trial')
    }
  }

  const updateField = (field: keyof Trial, value: string | number) => {
    if (!editingTrial) return
    setEditingTrial({ ...editingTrial, [field]: value })
  }

  useEffect(() => {
    loadTrials()
  }, [])

  return (
    <div className="section-stack">
      <section className="glass-card hero-card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="hero-title">Clinical Trial Management</h1>
            <p className="hero-sub">
              Manage {trials.length} clinical trials in the system. Add, edit, or remove trials for patient matching.
            </p>
          </div>
          <button
            type="button"
            className="soft-button"
            onClick={handleCreate}
            disabled={!!editingTrial}
          >
            <Plus className="h-4 w-4" />
            Add New Trial
          </button>
        </div>
      </section>

      {message && (
        <div className={`rounded-xl border p-4 ${
          message.type === 'success' 
            ? 'border-green-400/20 bg-green-400/10 text-green-300'
            : 'border-red-400/20 bg-red-400/10 text-red-300'
        }`}>
          <div className="flex items-center gap-2">
            {message.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
            <span className="text-sm font-medium">{message.text}</span>
          </div>
        </div>
      )}

      {editingTrial && (
        <section className="glass-card">
          <div className="card-header-row">
            <div className="section-title">
              <div className="section-icon">
                <FileText className="h-4 w-4" />
              </div>
              {isCreating ? 'Create New Trial' : `Edit Trial: ${editingTrial.trial_id}`}
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className="soft-button" onClick={handleSave}>
                <Save className="h-4 w-4" />
                Save
              </button>
              <button type="button" className="soft-button" onClick={handleCancel}>
                <X className="h-4 w-4" />
                Cancel
              </button>
            </div>
          </div>

          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="field-label">Trial ID (NCT Number)*</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.trial_id}
                  onChange={(e) => updateField('trial_id', e.target.value)}
                  placeholder="NCT12345678"
                  disabled={!isCreating}
                />
              </div>

              <div>
                <label className="field-label">Phase*</label>
                <select
                  className="field-select"
                  value={editingTrial.phase}
                  onChange={(e) => updateField('phase', e.target.value)}
                >
                  <option>Phase I</option>
                  <option>Phase I/II</option>
                  <option>Phase II</option>
                  <option>Phase II/III</option>
                  <option>Phase III</option>
                  <option>Phase IV</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="field-label">Title*</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.title}
                  onChange={(e) => updateField('title', e.target.value)}
                  placeholder="Phase III Study of Novel Diabetes Treatment"
                />
              </div>

              <div>
                <label className="field-label">Sponsor*</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.sponsor}
                  onChange={(e) => updateField('sponsor', e.target.value)}
                  placeholder="Research Institute Name"
                />
              </div>

              <div>
                <label className="field-label">Status*</label>
                <select
                  className="field-select"
                  value={editingTrial.status}
                  onChange={(e) => updateField('status', e.target.value)}
                >
                  <option>Recruiting</option>
                  <option>Active, not recruiting</option>
                  <option>Completed</option>
                  <option>Suspended</option>
                  <option>Terminated</option>
                  <option>Withdrawn</option>
                </select>
              </div>

              <div>
                <label className="field-label">Condition*</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.condition}
                  onChange={(e) => updateField('condition', e.target.value)}
                  placeholder="Type 2 Diabetes Mellitus"
                />
              </div>

              <div>
                <label className="field-label">Location (Sites)*</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.location}
                  onChange={(e) => updateField('location', e.target.value)}
                  placeholder="Boston, MA; New York, NY; Chicago, IL"
                />
                <p className="mt-1 text-xs muted-text">Separate multiple sites with semicolons</p>
              </div>

              <div className="md:col-span-2">
                <label className="field-label">Eligibility Criteria*</label>
                <textarea
                  className="field-input"
                  rows={6}
                  value={editingTrial.eligibility_criteria}
                  onChange={(e) => updateField('eligibility_criteria', e.target.value)}
                  placeholder="Inclusion Criteria: Age 18-75 years; Diagnosed with condition...&#10;Exclusion Criteria: Pregnancy; Severe complications..."
                />
              </div>

              <div className="md:col-span-2">
                <label className="field-label">Primary Outcome</label>
                <input
                  type="text"
                  className="field-input"
                  value={editingTrial.primary_outcome}
                  onChange={(e) => updateField('primary_outcome', e.target.value)}
                  placeholder="Change in HbA1c from baseline to 24 weeks"
                />
              </div>

              <div>
                <label className="field-label">Estimated Enrollment</label>
                <input
                  type="number"
                  className="field-input"
                  value={editingTrial.estimated_enrollment}
                  onChange={(e) => updateField('estimated_enrollment', parseInt(e.target.value) || 0)}
                  placeholder="500"
                />
              </div>

              <div>
                <label className="field-label">Study Start Date</label>
                <input
                  type="date"
                  className="field-input"
                  value={editingTrial.study_start_date}
                  onChange={(e) => updateField('study_start_date', e.target.value)}
                />
              </div>

              <div>
                <label className="field-label">Estimated Completion</label>
                <input
                  type="date"
                  className="field-input"
                  value={editingTrial.estimated_completion}
                  onChange={(e) => updateField('estimated_completion', e.target.value)}
                />
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="glass-card">
        <div className="card-header-row">
          <div className="section-title">
            <div className="section-icon">
              <FileText className="h-4 w-4" />
            </div>
            All Clinical Trials ({trials.length})
          </div>
        </div>

        <div className="card-body">
          {loading && (
            <div className="empty-state">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]" />
              <p className="muted-text text-sm">Loading trials...</p>
            </div>
          )}

          {!loading && trials.length === 0 && (
            <div className="empty-state">
              <FileText className="h-12 w-12 muted-text" />
              <p className="text-lg font-semibold text-white">No trials found</p>
              <p className="muted-text">Click "Add New Trial" to create your first trial</p>
            </div>
          )}

          {!loading && trials.length > 0 && (
            <div className="flex flex-col gap-3">
              {trials.map((trial) => (
                <div
                  key={trial.trial_id}
                  className="rounded-xl border border-white/10 bg-[rgba(13,22,45,0.6)] p-4 transition-all hover:border-white/20"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded border border-blue-400/20 bg-blue-400/10 px-2 py-0.5 font-mono text-xs" style={{ color: 'var(--blue)' }}>
                          {trial.trial_id}
                        </span>
                        <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-xs muted-text">
                          {trial.phase}
                        </span>
                        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${
                          trial.status === 'Recruiting' ? 'border border-green-400/20 bg-green-400/10 text-green-300' : 'border border-white/10 bg-white/5 text-slate-400'
                        }`}>
                          {trial.status}
                        </span>
                      </div>
                      <h3 className="mt-2 text-sm font-bold text-white">{trial.title}</h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs muted-text">
                        <span>📍 {trial.location}</span>
                        <span>🏥 {trial.condition}</span>
                        <span>👥 {trial.estimated_enrollment} participants</span>
                      </div>
                    </div>
                    <div className="flex flex-shrink-0 gap-2">
                      <button
                        type="button"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white transition-all hover:border-blue-400/30 hover:bg-blue-400/10"
                        onClick={() => handleEdit(trial)}
                        disabled={!!editingTrial}
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-white transition-all hover:border-red-400/30 hover:bg-red-400/10"
                        onClick={() => handleDelete(trial.trial_id)}
                        disabled={!!editingTrial}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

export default TrialManagement
