import { useState } from 'react'
import '../styles/management.css'

export default function RaspberryPiPage() {
  const [devices, setDevices] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function discoverNearby() {
    setError('')
    setMessage('')
    if (!window.isSecureContext || !navigator.bluetooth?.requestDevice) {
      setError('Nearby Bluetooth discovery requires Chrome with Bluetooth access on HTTPS or localhost.')
      return
    }
    setLoading(true)
    try {
      // A browser permission picker, not a silent scan of nearby MAC addresses.
      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
      })
      const item = { id: device.id, name: device.name || 'Unnamed Bluetooth device', bluetooth: device }
      setDevices(previous => {
        const others = previous.filter(entry => entry.id !== item.id)
        return [...others, item]
      })
      setSelected(item)
      setMessage('Bluetooth device selected. Raspberry Pi identity is not verified; secure pairing is not implemented yet.')
    } catch (err) {
      if (err.name !== 'NotFoundError') {
        setError(err.message || 'Bluetooth discovery failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="role-dashboard">
      <div className="role-dashboard-header">
        <div>
          <span className="role-dashboard-eyebrow">Nearby hardware</span>
          <h1>Raspberry Pi</h1>
          <p>Find Care-Inspector Raspberry Pis near this laptop using Bluetooth.</p>
        </div>
        <button className="management-primary-button" type="button"
          disabled={loading} onClick={discoverNearby}>
          {loading ? 'Searching...' : 'Search Nearby'}
        </button>
      </div>

      <section className="role-section">
        <div className="role-section-header">
          <div>
            <h2>Nearby Raspberry Pis</h2>
            <p>Chrome will show its Bluetooth device picker without a name filter.
              Selecting a device does not verify or pair it with Care-Inspector.</p>
          </div>
          <div className="role-section-count">{devices.length}</div>
        </div>
        {error && <p role="alert" className="error-banner">{error}</p>}
        {message && <p role="status" style={{ padding: 16 }}>{message}</p>}
        {!devices.length && (
          <div className="empty-state">
            No device selected. Power on the Raspberry Pi with Bluetooth enabled,
            then click Search Nearby. Our Pi verification service is still being developed.
          </div>
        )}
        <div className="management-printer-list">
          {devices.map(device => (
            <div key={device.id} className="management-printer-row">
              <div>
                <strong>{device.name}</strong>
                <span>Selected Bluetooth device · Unverified</span>
              </div>
              <div className="management-row-actions">
                <button type="button" className="secondary-button"
                  onClick={() => setSelected(device)}>
                  ⓘ Info
                </button>
                <button type="button" className="management-primary-button"
                  disabled title="Secure pairing and cloud enrollment must be implemented first">
                  Connect
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      {selected && (
        <section className="role-section" aria-label="Raspberry Pi details">
          <div className="role-section-header">
            <h2>Device information</h2>
            <button type="button" className="secondary-button"
              onClick={() => setSelected(null)}>Close</button>
          </div>
          <div style={{ padding: 16 }}>
            <p><strong>Advertised name:</strong> {selected.name}</p>
            <p><strong>Browser device ID:</strong> {selected.id}</p>
            <p><strong>Bluetooth MAC:</strong> Not accessible through Chrome Web Bluetooth</p>
            <p><strong>Model, hostname and network:</strong> Awaiting verified Pi agent response</p>
            <p><strong>Status:</strong> Selected, not verified or paired</p>
          </div>
        </section>
      )}
    </div>
  )
}
