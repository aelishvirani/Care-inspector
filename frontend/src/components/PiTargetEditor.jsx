import { useEffect, useState } from 'react'
import { apiPut } from '../api/client'

const EMPTY_TARGET = { host: '', port: '502', protocol: 'modbus', manufacturer: 'Hitachi', device_id: '' }

function toFormTarget(target) {
  return {
    host: target.host || '',
    port: String(target.port ?? 502),
    protocol: target.protocol || 'modbus',
    manufacturer: target.manufacturer || 'Hitachi',
    device_id: target.device_id || '',
  }
}

/** Edit staged config only. Does not apply settings to physical hardware. */
export default function PiTargetEditor({ configuration, onSaved, onCancel }) {
  const [targets, setTargets] = useState(() => configuration.printers.map(toFormTarget))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    setTargets(configuration.printers.map(toFormTarget))
    setError('')
    setNotice('')
  }, [configuration])

  function update(index, field, value) {
    setTargets(previous => previous.map((target, i) =>
      i === index ? { ...target, [field]: value } : target
    ))
    setError('')
    setNotice('')
  }

  function add() {
    if (targets.length >= 30) return
    setTargets(previous => [...previous, { ...EMPTY_TARGET }])
    setError('')
  }

  function remove(index) {
    setTargets(previous => previous.filter((_, i) => i !== index))
    setError('')
  }

  async function save(event) {
    event.preventDefault()
    if (saving) return
    setError('')
    setNotice('')

    // Validate locally to prevent accidental incomplete/duplicate entries.
    const printers = []
    const seen = new Set()
    for (const target of targets) {
      const host = target.host.trim()
      const port = Number(target.port)
      const deviceId = target.device_id.trim()
      if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
        setError('Enter an IP address and a valid port (1–65535) for every printer.')
        return
      }
      if (deviceId && !/^[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,99}$/.test(deviceId)) {
        setError('Printer device ID must be 3–100 valid characters.')
        return
      }
      const endpoint = `${host.toLowerCase()}:${port}`
      if (seen.has(endpoint)) {
        setError('Duplicate printer endpoint. Each IP and port combination must be unique.')
        return
      }
      seen.add(endpoint)
      printers.push({
        host, port, protocol: 'modbus', manufacturer: 'Hitachi', device_id: deviceId,
      })
    }

    setSaving(true)
    try {
      const result = await apiPut(
        `/secure/management/pi-targets/${encodeURIComponent(configuration.hardware_id)}`,
        { expected_version: configuration.version, printers }
      )
      if (result.hardware_id !== configuration.hardware_id ||
          result.version !== configuration.version + 1 ||
          !Array.isArray(result.printers) ||
          result.applied_to_pi !== false) {
        throw new Error('Unexpected configuration save response; reload before editing again.')
      }
      setNotice('Configuration staged successfully. Not yet applied to the Pi.')
      onSaved(result)
    } catch (err) {
      const message = err.message || 'Could not save configuration'
      // Backend uses 409 for optimistic locking. Do not overwrite newer data.
      setError(message.includes('409') || message.includes('reload before saving')
        ? 'Configuration changed on the server. Cancel editing, refresh and try again.'
        : message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="pi-target-editor" onSubmit={save}>
      <h3>Stage printer targets</h3>
      <p className="pi-muted">Save updates only the backend's staged configuration. It does not start monitoring or control a printer.</p>
      {error && <p role="alert" className="pi-alert pi-alert-error">{error}</p>}
      {notice && <p role="status" className="pi-alert pi-alert-info">{notice}</p>}

      {targets.map((target, index) => (
        <div className="pi-target-row" key={index}>
          <label>
            Printer IP
            <input required type="text" maxLength={45} autoComplete="off"
              value={target.host} onChange={event => update(index, 'host', event.target.value)}
              placeholder="192.168.10.50" disabled={saving} />
          </label>
          <label>
            Modbus port
            <input required type="number" min="1" max="65535" step="1"
              value={target.port} onChange={event => update(index, 'port', event.target.value)}
              disabled={saving} />
          </label>
          <label>
            Device ID (optional)
            <input type="text" maxLength={100} autoComplete="off"
              value={target.device_id} onChange={event => update(index, 'device_id', event.target.value)}
              placeholder="Auto-generated" disabled={saving} />
          </label>
          <span className="pi-target-protocol">Hitachi · Modbus</span>
          <button className="pi-info-btn" type="button" disabled={saving}
            onClick={() => remove(index)} aria-label={`Remove target ${index + 1}`}>Remove</button>
        </div>
      ))}

      <div className="pi-target-actions">
        <button className="pi-info-btn" type="button"
          disabled={saving || targets.length >= 30} onClick={add}>
          + Add printer
        </button>
        <span className="pi-muted">{targets.length}/30 targets</span>
        <div className="pi-target-spacer" />
        <button className="pi-info-btn" type="button" onClick={onCancel}
          disabled={saving}>Cancel</button>
        <button className="pi-connect-btn" type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save staged targets'}
        </button>
      </div>
    </form>
  )
}
