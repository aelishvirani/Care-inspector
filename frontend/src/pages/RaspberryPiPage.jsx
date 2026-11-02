import { useEffect, useState } from 'react'
import { apiGet } from '../api/client'
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
      const result = await apiGet('/secure/management/raspberry-pis/nearby')
      setDevices(result.devices)
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
          {loading ? 'Refreshing...' : 'Discover Nearby'}
        </button>
      </div>

      <section className="role-section">
        <div className="role-section-header">
          <div>
            <h2>Raspberry Pi Devices</h2>
            <p>Only Raspberry Pis advertising Care-Inspector on the backend's local network appear here.
              Pairing is not enabled yet.</p>
          </div>
          <div className="role-section-count">{devices.length}</div>
        </div>

        {error && <p role="alert" className="error-banner">{error}</p>}
        {!loading && !devices.length && !error && (
          <div className="empty-state">
            No nearby Care-Inspector Raspberry Pis discovered. Run the Pi discovery agent on the same network.
          </div>
        )}
        <div className="management-printer-list">
          {devices.map(device => (
            <div key={device.service_name} className="management-printer-row">
              <div>
                <strong>{device.display_name}</strong>
                <span>{device.hostname || device.service_name}</span>
              </div>
              <div>
                <span>Status</span>
                <strong>{'Nearby · Not paired'}</strong>
              </div>
              <div className="management-row-actions">
                <button type="button" className="secondary-button"
                  onClick={() => setSelected(device)} aria-label={`Info for ${device.display_name}`}>
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
            <p><strong>Name:</strong> {selected.display_name}</p>
            <p><strong>Discovery service:</strong> {selected.service_name}</p>
            <p><strong>Hostname:</strong> {selected.hostname}</p>
            <p><strong>Network IP:</strong> {(selected.ip_addresses || []).join(', ')}</p>
            <p><strong>MAC address:</strong> {selected.mac_address || 'Not reported'}</p>
            <p><strong>Device model / architecture:</strong> {selected.model || 'Not reported'}</p>
            <p>Discovered information is unverified until secure pairing is implemented.</p>
          </div>
        </section>
      )}
    </div>
  )
}
