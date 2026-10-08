import {
  useEffect,
  useState,
} from 'react'

import {
  getSystemHealth,
} from '../api/adminApi'

import {
  formatDateTime,
} from '../utils/formatters'


export default function SystemHealthPage() {
  const [
    health,
    setHealth,
  ] = useState(null)

  const [
    error,
    setError,
  ] = useState(null)


  async function load() {
    try {
      setError(null)

      setHealth(
        await getSystemHealth()
      )

    } catch (err) {
      setError(err.message)
    }
  }


  useEffect(() => {
    load()
  }, [])


  return (
    <div className="page">

      <div className="page-header">

        <div>
          <h1>System Health</h1>

          <p>
            Backend, database and collector
            connectivity overview
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
        >
          Refresh
        </button>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {health && (
        <div className="printer-summary-grid">

          <div className="summary-card">
            <span>API</span>
            <strong>{health.api}</strong>
          </div>

          <div className="summary-card">
            <span>Database</span>
            <strong>{health.database}</strong>
          </div>

          <div className="summary-card">
            <span>Printers</span>
            <strong>
              {health.printers}
            </strong>
          </div>

          <div className="summary-card">
            <span>Online</span>
            <strong>
              {health.online_printers}
            </strong>
          </div>

          <div className="summary-card">
            <span>Offline</span>
            <strong>
              {health.offline_printers}
            </strong>
          </div>

          <div className="summary-card">
            <span>Latest Device Seen</span>

            <strong>
              {
                health.latest_device_seen
                  ? formatDateTime(
                      health.latest_device_seen
                    )
                  : 'Never'
              }
            </strong>
          </div>

        </div>
      )}

    </div>
  )
}
