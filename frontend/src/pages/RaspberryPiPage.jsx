import { useState } from 'react'
import { CARE_INSPECTOR_SERVICE, readPiIdentity } from '../bluetooth/piIdentity'
import '../styles/management.css'
import '../styles/raspberry-pi.css'

export default function RaspberryPiPage() {
  const [devices, setDevices] = useState([])
  const [details, setDetails] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [inspectingId, setInspectingId] = useState(null)
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
        optionalServices: [CARE_INSPECTOR_SERVICE],
      })

      const candidate = {
        id: bluetoothDevice.id,
        name: bluetoothDevice.name || 'Unknown Bluetooth device',
        device: bluetoothDevice,
        foundAt: new Date().toLocaleTimeString(),
        identity: null,
        identityError: '',
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

  async function inspectDevice(candidate) {
    setDetails(candidate)
    setError('')
    setInspectingId(candidate.id)
    try {
      const identity = await readPiIdentity(candidate.device)
      const updated = { ...candidate, identity, identityError: '' }
      setDevices(previous => previous.map(item => item.id === candidate.id ? updated : item))
      setDetails(updated)
      setNotice('Care-Inspector identity service detected. Cryptographic verification is still required.')
    } catch (err) {
      const updated = { ...candidate, identity: null,
        identityError: 'Pi identity service unavailable: ' + (err.message || 'Unknown error') }
      setDevices(previous => previous.map(item => item.id === candidate.id ? updated : item))
      setDetails(updated)
    } finally {
      setInspectingId(null)
    }
  }

  function removeDevice(id) {
    const device = devices.find(item => item.id === id)?.device
    if (device?.gatt?.connected) device.gatt.disconnect()
    setDevices(previous => previous.filter(item => item.id !== id))
    if (details?.id === id) setDetails(null)
    setNotice('Temporary device removed from this page.')
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
          <span className="pi-stat-subtitle">Identity check requires the Pi BLE service</span>
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
            <p>Devices selected in Chrome remain temporary until secure pairing is complete.</p>
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
                  <span>Selected at {item.foundAt} · {item.identity ? 'Pi service detected, not authenticated' : 'Identity not verified'}</span>
                </div>
                <span className="pi-status">{item.identity ? 'Service found' : 'Unverified'}</span>
                <div className="pi-actions">
                  <button className="pi-info-btn" type="button"
                    onClick={() => setDetails(item)} aria-label={`Information about ${item.name}`}>
                    ⓘ Info
                  </button>
                  <button className="pi-info-btn" type="button"
                    disabled={inspectingId === item.id}
                    onClick={() => inspectDevice(item)}>
                    {inspectingId === item.id ? 'Checking...' : 'Check Pi'}
                  </button>
                  <button className="pi-info-btn" type="button"
                    onClick={() => removeDevice(item.id)}
                    aria-label={`Remove ${item.name} from temporary list`}>× Remove</button>
                  <button className="pi-connect-btn" type="button" disabled
                    title="Available only after cryptographic device verification and secure enrollment">
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
              <div className="pi-info-row"><span>Device verification</span><strong>Not authenticated</strong></div>
              <div className="pi-info-row"><span>Care-Inspector BLE service</span><strong>{details.identity ? 'Found (untrusted)' : 'Not checked / unavailable'}</strong></div>
              {details.identityError && <p role="status" className="pi-alert pi-alert-error">{details.identityError}</p>}
              {details.identity && <>
                <div className="pi-info-row"><span>Hardware ID (reported)</span><code>{details.identity.hardwareId}</code></div>
                <div className="pi-info-row"><span>Hostname (reported)</span><strong>{details.identity.hostname}</strong></div>
                <div className="pi-info-row"><span>Model (reported)</span><strong>{details.identity.model}</strong></div>
              </>}
              <div className="pi-info-row"><span>MAC address</span><strong>{details.identity?.macAddress || 'Unavailable (Chrome does not expose it)'}</strong></div>
              
              <div className="pi-info-row"><span>Cloud connection</span><strong>Not paired</strong></div>
            </div>
            <p className="pi-info-explanation">The displayed Bluetooth name, MAC and GATT identity may be spoofed. Connect remains disabled until a cryptographic proof of device identity and secure enrollment are implemented.</p>
            <div className="pi-modal-footer">
              <button className="pi-info-btn" type="button"
                disabled={inspectingId === details.id}
                onClick={() => inspectDevice(details)}>{inspectingId === details.id ? 'Checking...' : 'Check Pi Identity'}</button>
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
