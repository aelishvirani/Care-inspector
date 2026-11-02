import { useState } from 'react'
import '../styles/management.css'
import '../styles/raspberry-pi.css'

export default function RaspberryPiPage() {
  const [devices, setDevices] = useState([])
  const [details, setDetails] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  async function discoverNearby() {
    setNotice('')
    setError('')
    if (!window.isSecureContext || !navigator.bluetooth?.requestDevice) {
      setError('Use Chrome with Bluetooth enabled on HTTPS or localhost to search nearby.')
      return
    }

    setScanning(true)
    try {
      // Chrome controls the mandatory system picker. This is permission to
      // select a device, NOT pairing or verification of Raspberry Pi identity.
      const bluetoothDevice = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
      })

      const candidate = {
        id: bluetoothDevice.id,
        name: bluetoothDevice.name || 'Unknown Bluetooth device',
        device: bluetoothDevice,
        foundAt: new Date().toLocaleTimeString(),
      }

      setDevices(previous => [
        candidate,
        ...previous.filter(item => item.id !== candidate.id),
      ])
      setNotice('Device added to the list. Inspect its information before pairing.')
      setDetails(candidate)
    } catch (err) {
      if (err.name !== 'NotFoundError') {
        setError(err.message || 'Bluetooth search failed.')
      }
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="role-dashboard pi-page">
      <div className="role-dashboard-header pi-header">
        <div>
          <span className="role-dashboard-eyebrow">HARDWARE DISCOVERY</span>
          <h1>Raspberry Pi</h1>
          <p>Find nearby devices, inspect their identity, and connect them to Care-Inspector.</p>
        </div>
        <button type="button" className="management-primary-button pi-search-button"
          disabled={scanning} onClick={discoverNearby}>
          {scanning ? 'Searching...' : '⌁  Search Nearby'}
        </button>
      </div>

      {error && <div role="alert" className="pi-alert pi-alert-error">{error}</div>}
      {notice && <div role="status" className="pi-alert pi-alert-info">{notice}</div>}

      <div className="pi-overview">
        <div className="pi-stat">
          <span className="pi-stat-label">Selected nearby devices</span>
          <strong>{devices.length}</strong>
          <span className="pi-stat-subtitle">From Chrome Bluetooth selection</span>
        </div>
        <div className="pi-stat">
          <span className="pi-stat-label">Verified Raspberry Pis</span>
          <strong>0</strong>
          <span className="pi-stat-subtitle">Verification agent not installed yet</span>
        </div>
        <div className="pi-stat">
          <span className="pi-stat-label">Paired to cloud</span>
          <strong>0</strong>
          <span className="pi-stat-subtitle">Secure enrollment not available yet</span>
        </div>
      </div>

      <section className="pi-devices" aria-labelledby="pi-devices-title">
        <div className="pi-section-head">
          <div>
            <h2 id="pi-devices-title">Nearby Devices</h2>
            <p>Devices you select in Chrome appear here. Only verified Raspberry Pis will be connectable.</p>
          </div>
          <span className="pi-count">{devices.length} selected</span>
        </div>

        {devices.length === 0 ? (
          <div className="pi-empty">
            <div className="pi-empty-symbol" aria-hidden="true">⌁</div>
            <h3>Ready to find nearby devices</h3>
            <p>Turn on Bluetooth, then select <strong>Search Nearby</strong>. Chrome will open its required device picker.</p>
            <p className="pi-muted">Your Raspberry Pi will need the Care-Inspector BLE service for automatic identity verification.</p>
          </div>
        ) : (
          <div className="pi-device-list">
            {devices.map(item => (
              <div className="pi-device-row" key={item.id}>
                <div className="pi-device-icon" aria-hidden="true">⌁</div>
                <div className="pi-device-copy">
                  <strong>{item.name}</strong>
                  <span>Selected at {item.foundAt} · Identity not verified</span>
                </div>
                <span className="pi-status">Unverified</span>
                <div className="pi-actions">
                  <button className="pi-info-btn" type="button"
                    onClick={() => setDetails(item)} aria-label={`Information about ${item.name}`}>
                    ⓘ Info
                  </button>
                  <button className="pi-connect-btn" type="button" disabled
                    title="Available only after secure Raspberry Pi identity verification">
                    Connect
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <p className="pi-footer-note">For security, choosing a Bluetooth device does not register it, connect it to the backend, or authorize printer commands.</p>

      {details && (
        <div className="pi-modal-backdrop" role="presentation"
          onMouseDown={event => {
            if (event.target === event.currentTarget) setDetails(null)
          }}>
          <section className="pi-modal" role="dialog" aria-modal="true"
            aria-labelledby="pi-info-heading">
            <div className="pi-modal-header">
              <div>
                <span className="role-dashboard-eyebrow">DEVICE INFORMATION</span>
                <h2 id="pi-info-heading">{details.name}</h2>
              </div>
              <button className="pi-close" type="button" onClick={() => setDetails(null)}
                aria-label="Close device information">×</button>
            </div>
            <div className="pi-modal-content">
              <div className="pi-info-row"><span>Bluetooth name</span><strong>{details.name}</strong></div>
              <div className="pi-info-row"><span>Browser device identifier</span><code>{details.id}</code></div>
              <div className="pi-info-row"><span>Detected</span><strong>{details.foundAt}</strong></div>
              <div className="pi-info-row"><span>Device verification</span><strong>Not verified</strong></div>
              <div className="pi-info-row"><span>MAC address</span><strong>Unavailable from Chrome</strong></div>
              <div className="pi-info-row"><span>Model / serial number</span><strong>Awaiting Pi BLE identity service</strong></div>
              <div className="pi-info-row"><span>Cloud connection</span><strong>Not paired</strong></div>
            </div>
            <p className="pi-info-explanation">A Bluetooth name is not proof this is a Raspberry Pi. The Connect button will become available after authenticated Pi identification is implemented.</p>
            <div className="pi-modal-footer">
              <button className="pi-info-btn" type="button"
                onClick={() => setDetails(null)}>Close</button>
              <button className="pi-connect-btn" type="button" disabled>Connect</button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
