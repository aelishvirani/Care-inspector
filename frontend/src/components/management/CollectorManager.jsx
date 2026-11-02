import { useEffect, useState } from 'react'
import {
  getCollectors,
  getCollectorCustomers,
  registerCollector,
} from '../../api/collectorsApi'
import { useAuth } from '../../auth/AuthContext'

export default function CollectorManager() {
  const { user } = useAuth()
  const [collectors, setCollectors] = useState([])
  const [customers, setCustomers] = useState([])
  const [collectorId, setCollectorId] = useState('')
  const [name, setName] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [enrollment, setEnrollment] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const canManage = ['TECHNICIAN', 'ADMIN'].includes(user?.role)

  useEffect(() => {
    if (!canManage) return
    let active = true
    Promise.all([getCollectors(), getCollectorCustomers()])
      .then(([items, clients]) => {
        if (active) {
          setCollectors(items)
          setCustomers(clients)
        }
      })
      .catch(err => { if (active) setError(err.message) })
    return () => { active = false }
  }, [canManage])

  if (!canManage) return null

  async function register(event) {
    event.preventDefault()
    setError('')
    setEnrollment(null)
    setSaving(true)
    try {
      const result = await registerCollector({
        collector_id: collectorId.trim().toLowerCase(),
        name: name.trim(),
        customer_id: customerId ? Number(customerId) : null,
      })
      setEnrollment({
        collector_id: result.collector_id,
        token: result.enrollment_token,
      })
      setCollectors(await getCollectors())
      setCollectorId('')
      setName('')
      setCustomerId('')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="config-section-card">
      <div className="config-section-header">
        <div>
          <h2>Raspberry Pi / Collector Management</h2>
          <p>Register collector identities. Physical device enrollment and monitoring are not active yet.</p>
        </div>
      </div>

      <form className="config-fields" onSubmit={register}>
        <label>
          <span>Collector ID</span>
          <input required minLength={3} maxLength={64}
            pattern="[a-z0-9][a-z0-9_-]{2,63}"
            placeholder="raspberry-pi-01" value={collectorId}
            onChange={e => setCollectorId(e.target.value.toLowerCase())} />
        </label>
        <label>
          <span>Collector Name</span>
          <input required maxLength={100}
            placeholder="Production Line Pi 01" value={name}
            onChange={e => setName(e.target.value)} />
        </label>
        <label>
          <span>Customer (optional)</span>
          <select value={customerId} onChange={e => setCustomerId(e.target.value)}>
            <option value="">Not assigned</option>
            {customers.map(c => (
              <option value={c.id} key={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary-button" disabled={saving}>
          {saving ? 'Registering...' : 'Register Collector'}
        </button>
      </form>

      {error && <div role="alert" className="error-banner">{error}</div>}

      {enrollment && (
        <div style={{ padding: 16 }} role="status">
          <strong>Collector {enrollment.collector_id} registered.</strong>
          <p>Save this enrollment token securely on the Pi. It is only shown now.
            Do not share it in screenshots or chat.</p>
          <input aria-label="One-time enrollment token"
            value={enrollment.token} readOnly style={{ width: '100%' }} />
          <button type="button" onClick={() => setEnrollment(null)}>
            Hide token
          </button>
        </div>
      )}

      <div style={{ padding: 16 }}>
        <h3>Registered Collectors</h3>
        {collectors.length === 0 && <p>No Raspberry Pi collectors registered yet.</p>}
        {collectors.map(c => (
          <div key={c.collector_id} style={{ marginBottom: 12 }}>
            <strong>{c.name}</strong> — <code>{c.collector_id}</code>
            <div style={{ fontSize: 12 }}>
              {c.last_seen ? 'Last authenticated: ' + c.last_seen :
                'Not connected / no authenticated heartbeat'}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
