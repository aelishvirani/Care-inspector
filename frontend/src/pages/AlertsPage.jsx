import {
  useState,
} from 'react'

import AlertTable
  from '../components/alerts/AlertTable'

import {
  useAlerts,
} from '../hooks/useAlerts'

import {
  usePrinters,
} from '../hooks/usePrinters'


export default function AlertsPage() {

  const [status, setStatus] =
    useState('')

  const [severity, setSeverity] =
    useState('')

  const [deviceId, setDeviceId] =
    useState('')


  const {
    printers,
  } = usePrinters()


  const {
    alerts,
    loading,
    error,
    refresh,
  } = useAlerts({
    status,
    severity,
    deviceId,
  })


  const activeCount =
    alerts.filter(
      alert => alert.active
    ).length


  const criticalCount =
    alerts.filter(
      alert =>
        alert.severity === 'critical'
    ).length


  return (
    <div className="page">

      <div className="page-heading">

        <div>
          <h1>Alerts</h1>

          <p>
            Current and historical
            printer alerts
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={refresh}
        >
          Refresh
        </button>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <div className="printer-summary-grid">

        <div className="summary-card">
          <span>
            Results
          </span>

          <strong>
            {alerts.length}
          </strong>
        </div>


        <div className="summary-card">
          <span>
            Active
          </span>

          <strong>
            {activeCount}
          </strong>
        </div>


        <div className="summary-card">
          <span>
            Critical
          </span>

          <strong>
            {criticalCount}
          </strong>
        </div>

      </div>


      <section className="panel">

        <div className="filter-toolbar">

          <div className="filter-group">

            <label>
              Status
            </label>

            <select
              value={status}
              onChange={
                event =>
                  setStatus(
                    event.target.value
                  )
              }
            >
              <option value="">
                All
              </option>

              <option value="active">
                Active
              </option>

              <option value="resolved">
                Resolved
              </option>
            </select>

          </div>


          <div className="filter-group">

            <label>
              Severity
            </label>

            <select
              value={severity}
              onChange={
                event =>
                  setSeverity(
                    event.target.value
                  )
              }
            >
              <option value="">
                All
              </option>

              <option value="warning">
                Warning
              </option>

              <option value="critical">
                Critical
              </option>
            </select>

          </div>


          <div className="filter-group">

            <label>
              Printer
            </label>

            <select
              value={deviceId}
              onChange={
                event =>
                  setDeviceId(
                    event.target.value
                  )
              }
            >
              <option value="">
                All printers
              </option>

              {
                printers.map(
                  printer => (
                    <option
                      key={
                        printer.device_id
                      }
                      value={
                        printer.device_id
                      }
                    >
                      {
                        printer.device_id
                      }
                    </option>
                  )
                )
              }

            </select>

          </div>


          <button
            className="clear-filter-button"
            onClick={() => {
              setStatus('')
              setSeverity('')
              setDeviceId('')
            }}
          >
            Clear filters
          </button>

        </div>


        {loading ? (

          <div className="loading-panel">
            Loading alerts...
          </div>

        ) : (

          <AlertTable
            alerts={alerts}
          />

        )}

      </section>

    </div>
  )
}
