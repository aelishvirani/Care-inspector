import { useEffect, useState } from 'react'
import { apiGet } from '../api/client'
import PiTargetEditor from './PiTargetEditor'
import '../styles/raspberry-pi.css'

/**
 * Technician-managed staged target settings, hosted only on Configuration page.
 * No BLE, key management, printer control or device-side changes happen here.
 */
export default function PiConfigurationOverview() {
  const [registered, setRegistered] = useState([])
  const [selected, setSelected] = useState('')
  const [config, setConfig] = useState(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingConfig, setLoadingConfig] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const rows = await apiGet('/secure/management/pi-connect')
        if (cancelled) return
        if (!Array.isArray(rows)) throw new Error('Unexpected registered Pi response')
        setRegistered(rows)
        setSelected(previous => rows.some(item => item.hardware_id === previous) ? previous : '')
      } catch (err) {
        if (!cancelled) {
          setRegistered([])
          setSelected('')
          setError(err.message || 'Could not load registered Raspberry Pis')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [refreshKey])

  useEffect(() => {
    let cancelled = false
    setConfig(null)
    setEditing(false)
    if (!selected) return undefined

    async function load() {
      setLoadingConfig(true)
      setError('')
      try {
        const result = await apiGet(`/secure/management/pi-targets/${encodeURIComponent(selected)}`)
        if (cancelled) return
        if (result.hardware_id !== selected || !Array.isArray(result.printers)) {
          throw new Error('Unexpected Pi configuration response')
        }
        setConfig(result)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load Pi configuration')
      } finally {
        if (!cancelled) setLoadingConfig(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [selected, refreshKey])

  return (
    <section className="pi-devices pi-config-overview" aria-labelledby="pi-config-title">
      <div className="pi-section-head">
        <div>
          <h2 id="pi-config-title">Registered Pi configuration</h2>
          <p>Review server-staged printer targets. Settings are not automatically applied to hardware.</p>
        </div>
        <button type="button" className="pi-info-btn" disabled={loading}
          onClick={() => setRefreshKey(value => value + 1)}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="pi-config-content">
        {error && <p role="alert" className="pi-alert pi-alert-error">{error}</p>}
        {!loading && registered.length === 0 && !error && (
          <p className="pi-muted">No Raspberry Pis registered yet.</p>
        )}
        {registered.length > 0 && (
          <>
            <label className="pi-config-label" htmlFor="pi-config-select">Registered Raspberry Pi</label>
            <select id="pi-config-select" className="pi-config-select"
              value={selected} onChange={event => setSelected(event.target.value)}>
              <option value="">Select a registered Pi</option>
              {registered.map(pi => (
                <option key={pi.hardware_id} value={pi.hardware_id}>{pi.hardware_id}</option>
              ))}
            </select>
          </>
        )}
        {selected && loadingConfig && <p className="pi-muted">Loading staged targets...</p>}
        {selected && config && !loadingConfig && (
          <>
            <p className="pi-config-meta">
              Configuration version: <strong>{config.version}</strong> ·
              {' '}{config.printers.length} target(s) ·
              {' '}Not confirmed applied to Pi
            </p>
            {!editing && (
              <button type="button" className="pi-info-btn" onClick={() => setEditing(true)}>
                Edit staged targets
              </button>
            )}
            {editing ? (
              <PiTargetEditor configuration={config}
                onSaved={result => { setConfig(result); setEditing(false) }}
                onCancel={() => setEditing(false)} />
            ) : config.printers.length === 0 ? (
              <p className="pi-muted">No printer targets staged for this Pi.</p>
            ) : (
              <div className="pi-config-list">
                {config.printers.map((printer, index) => (
                  <div className="pi-config-item" key={`${printer.host}:${printer.port}:${index}`}>
                    <strong>{printer.manufacturer} · {printer.protocol}</strong>
                    <span>{printer.host}:{printer.port}</span>
                    {printer.device_id && <span>Device ID: {printer.device_id}</span>}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
