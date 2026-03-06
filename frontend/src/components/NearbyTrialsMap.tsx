import { useEffect, useState, useRef } from 'react'
import { MapPin, Navigation, Filter, ChevronDown, ChevronUp } from 'lucide-react'
import axios from 'axios'

interface TrialSite {
  name: string
  lat: number | null
  lon: number | null
  distance_miles: number | null
}

interface NearbyTrial {
  trial_id: string
  title: string
  phase: string
  condition: string
  status: string
  location_raw: string
  sites: TrialSite[]
  nearest_site: string | null
  nearest_distance_miles: number | null
  nearest_site_lat: number | null
  nearest_site_lon: number | null
  within_radius: boolean
}

interface NearbyTrialsData {
  patient_id: string
  patient_index: number
  patient_location: string
  patient_lat: number | null
  patient_lon: number | null
  radius_miles: number
  total_trials: number
  nearby_count: number
  nearby_trials: NearbyTrial[]
  all_trials: NearbyTrial[]
  summary: string
}

interface Props {
  patientIndex: number | null
}

const RADIUS_OPTIONS = [50, 100, 150, 250, 500]

const NearbyTrialsMap = ({ patientIndex }: Props) => {
  const [data, setData] = useState<NearbyTrialsData | null>(null)
  const [radius, setRadius] = useState(100)
  const [loading, setLoading] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const fetchNearby = async () => {
    setLoading(true)
    try {
      const idx = patientIndex ?? 0
      const res = await axios.get(
        `http://localhost:5000/api/v2/nearby-trials?patient_index=${idx}&radius_miles=${radius}`
      )
      setData(res.data)
    } catch (err) {
      console.error('Failed to fetch nearby trials:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNearby()
  }, [patientIndex, radius])

  // Draw the map visualization on canvas
  useEffect(() => {
    if (!data || !canvasRef.current || !data.patient_lat) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)
    const W = rect.width
    const H = rect.height

    // Clear
    ctx.clearRect(0, 0, W, H)

    // Collect all points for bounding box
    const points: { lat: number; lon: number; label: string; isPatient: boolean; nearby: boolean; dist: number | null }[] = []

    if (data.patient_lat && data.patient_lon) {
      points.push({ lat: data.patient_lat, lon: data.patient_lon, label: 'You', isPatient: true, nearby: true, dist: null })
    }

    data.all_trials.forEach((t) => {
      if (t.nearest_site_lat && t.nearest_site_lon) {
        points.push({
          lat: t.nearest_site_lat,
          lon: t.nearest_site_lon,
          label: t.nearest_site || t.title.substring(0, 20),
          isPatient: false,
          nearby: t.within_radius,
          dist: t.nearest_distance_miles,
        })
      }
    })

    if (points.length < 2) return

    // Compute bounding box with padding
    let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity
    points.forEach((p) => {
      if (p.lat < minLat) minLat = p.lat
      if (p.lat > maxLat) maxLat = p.lat
      if (p.lon < minLon) minLon = p.lon
      if (p.lon > maxLon) maxLon = p.lon
    })

    const padLat = (maxLat - minLat) * 0.15 || 5
    const padLon = (maxLon - minLon) * 0.15 || 5
    minLat -= padLat; maxLat += padLat
    minLon -= padLon; maxLon += padLon

    const margin = 40
    const mapW = W - margin * 2
    const mapH = H - margin * 2

    const toX = (lon: number) => margin + ((lon - minLon) / (maxLon - minLon)) * mapW
    const toY = (lat: number) => margin + ((maxLat - lat) / (maxLat - minLat)) * mapH

    // Draw background grid
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.06)'
    ctx.lineWidth = 1
    for (let i = 0; i <= 8; i++) {
      const x = margin + (mapW / 8) * i
      ctx.beginPath(); ctx.moveTo(x, margin); ctx.lineTo(x, H - margin); ctx.stroke()
      const y = margin + (mapH / 8) * i
      ctx.beginPath(); ctx.moveTo(margin, y); ctx.lineTo(W - margin, y); ctx.stroke()
    }

    // Draw radius circle around patient
    if (data.patient_lat && data.patient_lon) {
      const px = toX(data.patient_lon)
      const py = toY(data.patient_lat)

      // Approximate radius in degrees (rough: 1 degree lat ≈ 69 miles)
      const radiusDegLat = radius / 69
      const radiusPx = Math.abs(toY(data.patient_lat - radiusDegLat) - py)

      // Draw radius circle
      ctx.beginPath()
      ctx.arc(px, py, radiusPx, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(96, 165, 250, 0.06)'
      ctx.fill()
      ctx.strokeStyle = 'rgba(96, 165, 250, 0.25)'
      ctx.lineWidth = 1.5
      ctx.setLineDash([6, 4])
      ctx.stroke()
      ctx.setLineDash([])

      // Radius label
      ctx.font = '10px Inter, system-ui, sans-serif'
      ctx.fillStyle = 'rgba(96, 165, 250, 0.5)'
      ctx.textAlign = 'center'
      ctx.fillText(`${radius} mi radius`, px, py - radiusPx - 6)
    }

    // Draw connection lines from patient to nearby trial sites
    const patientPt = points.find((p) => p.isPatient)
    if (patientPt) {
      const px = toX(patientPt.lon)
      const py = toY(patientPt.lat)

      points.filter((p) => !p.isPatient && p.nearby).forEach((p) => {
        const sx = toX(p.lon)
        const sy = toY(p.lat)
        ctx.beginPath()
        ctx.moveTo(px, py)
        ctx.lineTo(sx, sy)
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.3)'
        ctx.lineWidth = 1.5
        ctx.stroke()

        // Distance label on line
        if (p.dist !== null) {
          const midX = (px + sx) / 2
          const midY = (py + sy) / 2
          ctx.font = 'bold 9px Inter, system-ui, sans-serif'
          ctx.fillStyle = 'rgba(52, 211, 153, 0.7)'
          ctx.textAlign = 'center'
          ctx.fillText(`${Math.round(p.dist)} mi`, midX, midY - 5)
        }
      })
    }

    // Draw trial site dots
    points.filter((p) => !p.isPatient).forEach((p) => {
      const x = toX(p.lon)
      const y = toY(p.lat)

      // Outer glow
      if (p.nearby) {
        ctx.beginPath()
        ctx.arc(x, y, 10, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(52, 211, 153, 0.15)'
        ctx.fill()
      }

      // Dot
      ctx.beginPath()
      ctx.arc(x, y, p.nearby ? 5 : 3.5, 0, Math.PI * 2)
      ctx.fillStyle = p.nearby ? '#34d399' : 'rgba(148, 163, 184, 0.4)'
      ctx.fill()

      // Label
      ctx.font = `${p.nearby ? 'bold ' : ''}10px Inter, system-ui, sans-serif`
      ctx.fillStyle = p.nearby ? 'rgba(255,255,255,0.8)' : 'rgba(148, 163, 184, 0.5)'
      ctx.textAlign = 'center'
      ctx.fillText(p.label, x, y + 16)
    })

    // Draw patient dot (on top)
    if (patientPt) {
      const px = toX(patientPt.lon)
      const py = toY(patientPt.lat)

      // Pulse ring
      ctx.beginPath()
      ctx.arc(px, py, 14, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(96, 165, 250, 0.12)'
      ctx.fill()

      // Outer ring
      ctx.beginPath()
      ctx.arc(px, py, 8, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(96, 165, 250, 0.3)'
      ctx.fill()

      // Inner dot
      ctx.beginPath()
      ctx.arc(px, py, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#60a5fa'
      ctx.fill()

      // Label
      ctx.font = 'bold 11px Inter, system-ui, sans-serif'
      ctx.fillStyle = '#60a5fa'
      ctx.textAlign = 'center'
      ctx.fillText(data.patient_location, px, py - 18)
      ctx.font = '9px Inter, system-ui, sans-serif'
      ctx.fillStyle = 'rgba(96, 165, 250, 0.6)'
      ctx.fillText('Patient Location', px, py - 7)
    }
  }, [data, radius])

  if (!data && !loading) return null

  const trialsToShow = showAll ? data?.all_trials : data?.nearby_trials
  const nearestTrial = data?.nearby_trials?.[0]

  return (
    <section className="glass-card">
      <div className="card-header-row">
        <div className="section-title">
          <div className="section-icon">
            <MapPin className="h-4 w-4" />
          </div>
          Geographic Proximity Filter
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 muted-text" />
            <select
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="field-select"
              style={{ minWidth: '130px' }}
            >
              {RADIUS_OPTIONS.map((r) => (
                <option key={r} value={r}>{r}-mile radius</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card-body section-stack">
        {loading && !data && (
          <div className="empty-state">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[rgba(96,165,250,0.2)] border-t-[var(--blue)]" />
            <p className="muted-text text-sm">Searching nearby trial sites...</p>
          </div>
        )}

        {data && (
          <>
            {/* Summary Banner */}
            <div className="rounded-xl border border-blue-400/20 bg-blue-400/5 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-blue-400/20 bg-blue-400/10">
                    <Navigation className="h-5 w-5" style={{ color: 'var(--blue)' }} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white">
                      {data.nearby_count} of {data.total_trials} trials have nearby sites
                    </div>
                    <div className="text-xs muted-text">
                      Within {radius}-mile radius of <span style={{ color: 'var(--blue)' }}>{data.patient_location}</span>
                    </div>
                  </div>
                </div>
                {nearestTrial && nearestTrial.nearest_distance_miles !== null && (
                  <div className="text-right">
                    <div className="text-xs muted-text">Nearest site</div>
                    <div className="text-lg font-bold" style={{ color: 'var(--green)' }}>
                      {Math.round(nearestTrial.nearest_distance_miles)} mi
                    </div>
                    <div className="text-[10px] muted-text">{nearestTrial.nearest_site}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Map View */}
            <div className="rounded-xl border border-white/10 bg-[rgba(8,14,30,0.6)] p-1">
              <div className="relative" style={{ paddingBottom: '50%' }}>
                <canvas
                  ref={canvasRef}
                  className="absolute inset-0 h-full w-full"
                  style={{ width: '100%', height: '100%' }}
                />
              </div>
              <div className="flex items-center justify-between px-3 pb-2 pt-1">
                <div className="flex items-center gap-4 text-[10px]">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#60a5fa]" />
                    Patient
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#34d399]" />
                    Nearby Site
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-slate-500/40" />
                    Distant Site
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-0 w-4 border-t border-dashed border-blue-400/40" />
                    {radius} mi Radius
                  </span>
                </div>
                <span className="text-[10px] muted-text">Approximate locations</span>
              </div>
            </div>

            {/* Trial List */}
            <div>
              <div className="mb-3 flex items-center justify-between">
                <div className="text-[11px] font-bold uppercase tracking-[1.2px] muted-text">
                  {showAll ? `All ${data.total_trials} Trials` : `${data.nearby_count} Nearby Trials`}
                </div>
                <button
                  type="button"
                  className="flex items-center gap-1 text-[11px] muted-text hover:text-white transition-colors"
                  onClick={() => setShowAll(!showAll)}
                >
                  {showAll ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {showAll ? 'Show nearby only' : 'Show all trials'}
                </button>
              </div>

              <div className="flex flex-col gap-2">
                {(trialsToShow || []).map((trial) => (
                  <div
                    key={trial.trial_id}
                    className={`rounded-lg border p-3 transition-all ${
                      trial.within_radius
                        ? 'border-green-400/20 bg-green-400/5'
                        : 'border-white/5 bg-white/[0.02] opacity-60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <MapPin
                            className={`h-3.5 w-3.5 flex-shrink-0 ${trial.within_radius ? 'text-green-400' : 'text-slate-500'}`}
                          />
                          <span className="text-sm font-semibold text-white truncate">{trial.title}</span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-[10.5px] muted-text">
                          <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono">
                            {trial.trial_id}
                          </span>
                          <span>{trial.phase}</span>
                          <span>·</span>
                          <span>{trial.condition}</span>
                        </div>
                        {trial.nearest_site && (
                          <div className="mt-1 text-[10.5px] muted-text">
                            Nearest site: {trial.nearest_site}
                          </div>
                        )}
                      </div>
                      <div className="flex-shrink-0 text-right">
                        {trial.nearest_distance_miles !== null ? (
                          <>
                            <div
                              className="text-sm font-bold"
                              style={{ color: trial.within_radius ? 'var(--green)' : 'var(--muted)' }}
                            >
                              {Math.round(trial.nearest_distance_miles)} mi
                            </div>
                            {trial.within_radius && (
                              <div className="text-[9px] font-semibold uppercase tracking-wider text-green-400/70">
                                Within range
                              </div>
                            )}
                          </>
                        ) : (
                          <span className="text-xs muted-text">Unknown</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {(trialsToShow || []).length === 0 && (
                  <div className="rounded-lg border border-white/5 bg-white/[0.02] p-6 text-center text-sm muted-text">
                    No trials found within {radius} miles. Try increasing the search radius.
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  )
}

export default NearbyTrialsMap
