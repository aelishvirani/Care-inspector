import { useEffect, useState } from 'react'
import { getCollectors } from '../api/collectorsApi'
import '../styles/management.css'

export default function RaspberryPiPage() {
  const [devices, setDevices] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    setLoading(true)
    setError('')
    try {
      setDevices(await getCollectors())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  return (
    <div className="role-dashboard">
      <div className="role-dashboard-header">
        <div>
          <span className="role-dashboard-eyebrow">Hardware pairing</span>
          <h1>Raspberry Pi</h1>
          <p>Discover, identify, and securely pair Raspberry Pi collectors.</p>
        </div>
        <button className="management-primary-button" type="button"
          disabled={loading} onClick={refresh}>
          {loading ? 'Refreshing...' : 'Refresh Devices'}
        </button>
      </div>

      <section className="role-section">
        <div className="role-section-header">
          <div>
            <h2>Raspberry Pi Devices</h2>
            <p>Nearby scanning and one-click pairing require a Pi discovery agent.
              They are not active yet. This list shows existing collector records only.</p>
          </div>
          <div className="role-section-count">{devices.length}</div>
        </div>

        {error && <p role="alert" className="error-banner">{error}</p>}
        {!loading && !devices.length && !error && (
          <div className="empty-state">
            No Raspberry Pi devices registered. Nearby discovery is not available yet.
          </div>
        )}
        <div className="management-printer-list">
          {devices.map(device => (
            <div key={device.collector_id} className="management-printer-row">
              <div>
                <strong>{device.name}</strong>
                <span>{device.collector_id}</span>
              </div>
              <div>
                <span>Status</span>
                <strong>{device.last_seen ? 'Previously authenticated' : 'Not connected'}</strong>
              </div>
              <div className="management-row-actions">
                <button type="button" className="secondary-button"
                  onClick={() => setSelected(device)} aria-label={`Info for ${device.name}`}>
                  ⓘ Info
                </button>
                <button type="button" className="management-primary-button" disabled
                  title="Secure local pairing is not implemented yet">
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
            <p><strong>Name:</strong> {selected.name}</p>
            <p><strong>Collector ID:</strong> {selected.collector_id}</p>
            <p><strong>Customer:</strong> {selected.customer_id ?? 'Not assigned'}</p>
            <p><strong>Last authenticated:</strong> {selected.last_seen || 'Never'}</p>
            <p><strong>MAC address:</strong> Not yet reported</p>
            <p><strong>Model and hostname:</strong> Not yet reported</p>
            <p>Hardware details will be available when the Pi discovery agent is installed.</p>
          </div>
        </section>
      )}
    </div>
  )
}
