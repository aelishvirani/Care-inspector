import { useEffect, useState } from 'react'
import {
  addPrinterCommand,
  deletePrinterCommand,
  getPrinterCommands,
} from '../../api/printerCommandsApi'

export default function PrinterCommandManager({ deviceId }) {
  const [commands, setCommands] = useState([])
  const [name, setName] = useState('')
  const [hexCode, setHexCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    setCommands([])
    setError('')
    setMessage('')
    setName('')
    setHexCode('')
    if (deviceId) {
      getPrinterCommands(deviceId)
        .then(result => { if (active) setCommands(result) })
        .catch(err => { if (active) setError(err.message) })
    }
    return () => { active = false }
  }, [deviceId])

  async function save(event) {
    event.preventDefault()
    if (busy || !deviceId) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await addPrinterCommand(deviceId, {
        name: name.trim(),
        hex_code: hexCode.trim(),
      })
      setCommands(await getPrinterCommands(deviceId))
      setName('')
      setHexCode('')
      setMessage('Command saved. It is available in this printer’s dropdown.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove(command) {
    if (!window.confirm(`Delete "${command.name}"?`)) return
    setBusy(true)
    setError('')
    try {
      await deletePrinterCommand(deviceId, command.id)
      setCommands(await getPrinterCommands(deviceId))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="config-section-card" aria-label="Printer commands">
      <div className="config-section-header">
        <div>
          <h2>Printer Commands</h2>
          <p>Save printer-specific hexadecimal commands. Hardware execution is not enabled yet.</p>
        </div>
      </div>
      <form onSubmit={save} className="config-fields">
        <label>
          <span>Command name</span>
          <input value={name} maxLength={80} required
            onChange={e => setName(e.target.value)} placeholder="e.g. Clear Fault" />
        </label>
        <label>
          <span>Hexadecimal code</span>
          <input value={hexCode} required
            onChange={e => setHexCode(e.target.value)}
            placeholder="e.g. 00 01 (manual-verified only)" />
        </label>
        <button type="submit" className="primary-button" disabled={busy || !deviceId}>
          {busy ? 'Saving...' : 'Add Command'}
        </button>
      </form>
      {error && <div role="alert" className="error-banner">{error}</div>}
      {message && <p role="status">{message}</p>}
      <div style={{ padding: '16px' }}>
        {commands.length === 0 && <p>No custom commands configured for this printer.</p>}
        {commands.map(command => (
          <div key={command.id} style={{
            display: 'flex', gap: 12, justifyContent: 'space-between',
            alignItems: 'center', marginBottom: 10,
          }}>
            <span><strong>{command.name}</strong> · <code>{command.hex_code}</code></span>
            <button type="button" disabled={busy} onClick={() => remove(command)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}
