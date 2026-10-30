import { useEffect, useState } from 'react'
import {
  getPrinterConnection,
  savePrinterConnection,
} from '../../api/printerConnectionsApi'

const DEFAULTS = {
  manufacturer: 'hitachi',
  protocol: 'modbus_tcp',
  host: '',
  port: 502,
  unit_id: 1,
  collector_id: '',
  enabled: false,
}

export default function PrinterConnectionForm({
  deviceId,
  onClose,
}) {
  const [settings, setSettings] = useState(DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      setSuccess('')

      try {
        const data = await getPrinterConnection(deviceId)

        if (!cancelled) {
          setSettings(
            data.configured
              ? {
                  ...DEFAULTS,
                  ...data,
                  enabled: false,
                }
              : { ...DEFAULTS }
          )
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [deviceId])

  function change(field, value) {
    setSettings(previous => ({
      ...previous,
      [field]: value,
    }))
    setSuccess('')
  }

  async function save(event) {
    event.preventDefault()
    if (saving) return

    setSaving(true)
    setError('')
    setSuccess('')

    try {
      await savePrinterConnection(deviceId, {
        manufacturer: settings.manufacturer,
        protocol: settings.protocol,
        host: settings.host.trim(),
        port: Number(settings.port),
        unit_id: Number(settings.unit_id),
        collector_id: (settings.collector_id || '').trim() || null,
        enabled: false,
      })

      setSuccess('Connection settings saved successfully.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="loading-panel">Loading connection settings...</div>
  }

  return (
    <section className="management-form-card">
      <div className="management-section-title">
        <h2>Printer Connection — {deviceId}</h2>
        <p>Configure connection details. Monitoring activation is not available yet.</p>
      </div>

      <form className="management-form-grid" onSubmit={save}>
        <label>
          Manufacturer
          <select
            value={settings.manufacturer}
            onChange={e => change('manufacturer', e.target.value)}
          >
            <option value="hitachi">Hitachi</option>
          </select>
        </label>

        <label>
          Protocol
          <select
            value={settings.protocol}
            onChange={e => change('protocol', e.target.value)}
          >
            <option value="modbus_tcp">Modbus TCP</option>
          </select>
        </label>

        <label>
          Printer IP Address *
          <input
            required
            placeholder="192.168.50.1"
            value={settings.host}
            onChange={e => change('host', e.target.value)}
          />
        </label>

        <label>
          TCP Port *
          <input
            required
            type="number"
            min="1"
            max="65535"
            value={settings.port}
            onChange={e => change('port', e.target.value)}
          />
        </label>

        <label>
          Modbus Unit ID *
          <input
            required
            type="number"
            min="1"
            max="247"
            value={settings.unit_id}
            onChange={e => change('unit_id', e.target.value)}
          />
        </label>

        <label>
          Collector ID
          <input
            placeholder="e.g. raspberry-pi-01"
            value={settings.collector_id || ''}
            onChange={e => change('collector_id', e.target.value)}
          />
        </label>

        <div className="management-form-actions">
          <button
            className="management-primary-button"
            type="submit"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Connection'}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        {error && <div role="alert" className="error-banner">{error}</div>}
        {success && <p role="status" style={{ color: '#16794f' }}>{success}</p>}
      </form>
    </section>
  )
}
