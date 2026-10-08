import {
  useMemo,
  useState,
} from 'react'

import {
  useSearchParams,
} from 'react-router-dom'

import AlertTable
  from '../components/alerts/AlertTable'

import {
  useAlerts,
} from '../hooks/useAlerts'

import {
  usePrinters,
} from '../hooks/usePrinters'


export default function AlertsPage() {

  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams()


  const initialDevice =
    searchParams.get(
      'device_id'
    ) || ''


  const [
    status,
    setStatus,
  ] = useState('')


  const [
    severity,
    setSeverity,
  ] = useState('')


  const [
    deviceId,
    setDeviceId,
  ] = useState(
    initialDevice
  )


  const [
    search,
    setSearch,
  ] = useState('')


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


  const filteredAlerts =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        if (!term) {
          return alerts
        }

        return alerts.filter(
          alert =>
            [
              alert.alert_type,
              alert.message,
              alert.device_id,
              alert.severity,
            ]
              .filter(Boolean)
              .some(
                value =>
                  String(value)
                    .toLowerCase()
                    .includes(term)
              )
        )
      },
      [
        alerts,
        search,
      ]
    )


  const activeCount =
    filteredAlerts.filter(
      alert =>
        alert.active
        && !alert.acknowledged_at
    ).length


  const criticalCount =
    filteredAlerts.filter(
      alert =>
        alert.severity
          === 'critical'
    ).length


  function updateDevice(
    value
  ) {
    setDeviceId(value)

    if (value) {
      setSearchParams({
        device_id: value,
      })
    } else {
      setSearchParams({})
    }
  }


  return (
    <div className="page">

      <div className="page-heading">

        <div>
          <h1>
            Alerts & Problems
          </h1>

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
            {
              filteredAlerts.length
            }
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
              Search
            </label>

            <input
              type="search"
              placeholder={
                'Problem, printer, message...'
              }
              value={search}
              onChange={
                event =>
                  setSearch(
                    event.target.value
                  )
              }
            />

          </div>


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

              <option value="acknowledged">
                Acknowledged
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
                  updateDevice(
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
                        printer.display_name
                        || printer.device_id
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
              setSearch('')
              setStatus('')
              setSeverity('')
              setDeviceId('')
              setSearchParams({})
            }}
          >
            Clear filters
          </button>

        </div>


        {
          loading
          ? (
            <div className="loading-panel">
              Loading alerts...
            </div>
          )
          : (
            <AlertTable
              alerts={
                filteredAlerts
              }
              onAcknowledged={
                refresh
              }
            />
          )
        }

      </section>

    </div>
  )
}
