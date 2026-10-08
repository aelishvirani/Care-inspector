import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  apiGet,
} from '../api/client'

import '../styles/role-panels.css'


const REFRESH_INTERVAL = 5000


function nativeLevel(
  label,
  raw
) {
  if (label) {
    return label
      .replaceAll('_', ' ')
      .replace(
        /\b\w/g,
        char => char.toUpperCase()
      )
  }

  if (
    raw !== null
    && raw !== undefined
  ) {
    return `Level ${raw}`
  }

  return '—'
}


function statusInfo(printer) {
  if (!printer.online) {
    return {
      label: 'Offline',
      className: 'offline',
    }
  }

  if (printer.status === 'fault') {
    return {
      label: 'Fault',
      className: 'fault',
    }
  }

  if (printer.status === 'warning') {
    return {
      label: 'Warning',
      className: 'warning',
    }
  }

  return {
    label:
      printer.status
        ?.replaceAll('_', ' ')
        ?.toUpperCase()
      || 'Online',

    className: 'online',
  }
}


function formatLastSeen(value) {
  if (!value) return 'Never'

  return new Date(value)
    .toLocaleString()
}


export default function CustomerDashboardPage() {
  const [
    printers,
    setPrinters,
  ] = useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  async function refresh() {
    try {
      const data =
        await apiGet(
          '/secure/devices'
        )

      setPrinters(data)
      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        'Unable to load your printers'
      )

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()

    const interval =
      setInterval(
        refresh,
        REFRESH_INTERVAL
      )

    return () =>
      clearInterval(interval)
  }, [])


  const summary = useMemo(
    () => {
      const online =
        printers.filter(
          printer =>
            printer.online
        ).length

      const offline =
        printers.length
        - online

      const problems =
        printers.filter(
          printer =>
            !printer.online
            || printer.status
              === 'warning'
            || printer.status
              === 'fault'
        ).length

      return {
        total:
          printers.length,

        online,
        offline,
        problems,
      }
    },
    [printers]
  )


  if (loading) {
    return (
      <div className="loading-panel">
        Loading your printer fleet...
      </div>
    )
  }


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>
          <span className="role-dashboard-eyebrow">
            Customer Portal
          </span>

          <h1>
            My Printer Fleet
          </h1>

          <p>
            Monitor all printers assigned
            to your company from one place.
          </p>
        </div>

        <button
          className="role-refresh-button"
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


      <div className="role-kpi-grid">

        <div className="role-kpi">

          <div className="role-kpi-top">
            <span className="role-kpi-label">
              Printers
            </span>

            <span className="role-kpi-icon">
              P
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.total}
          </strong>

          <span className="role-kpi-hint">
            Assigned to your company
          </span>

        </div>


        <div className="role-kpi">

          <div className="role-kpi-top">
            <span className="role-kpi-label">
              Online
            </span>

            <span className="role-kpi-icon">
              ✓
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.online}
          </strong>

          <span className="role-kpi-hint">
            Reporting normally
          </span>

        </div>


        <div className="role-kpi offline">

          <div className="role-kpi-top">
            <span className="role-kpi-label">
              Offline
            </span>

            <span className="role-kpi-icon">
              !
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.offline}
          </strong>

          <span className="role-kpi-hint">
            Not currently reporting
          </span>

        </div>


        <div className="role-kpi problem">

          <div className="role-kpi-top">
            <span className="role-kpi-label">
              Needs Attention
            </span>

            <span className="role-kpi-icon">
              !
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.problems}
          </strong>

          <span className="role-kpi-hint">
            Offline, warning or fault
          </span>

        </div>

      </div>


      <div className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              My Printers
            </h2>

            <p>
              Live status and important
              machine information
            </p>
          </div>

          <div className="role-section-count">
            {printers.length}
          </div>

        </div>

      </div>


      {
        printers.length === 0
        ? (
          <div className="empty-state">
            No printers are assigned
            to your account.
          </div>
        )
        : (
          <div className="customer-printer-grid">

            {
              printers.map(
                printer => {

                  const status =
                    statusInfo(
                      printer
                    )

                  const cardState =
                    !printer.online
                      ? 'offline'
                      : (
                          printer.status
                            === 'warning'
                          || printer.status
                            === 'fault'
                            ? 'attention'
                            : 'online'
                        )

                  return (
                    <article
                      key={
                        printer.device_id
                      }
                      className={
                        `customer-printer-card ${cardState}`
                      }
                    >

                      <div className="customer-printer-top">

                        <div className="customer-printer-title">

                          <h2>
                            {
                              printer.display_name
                              || 'Printer'
                            }
                          </h2>

                          <p>
                            {
                              printer.model_name
                              || 'Unknown model'
                            }
                            {
                              printer.location
                              && (
                                <>
                                  {' · '}
                                  {printer.location}
                                </>
                              )
                            }
                          </p>

                          <span className="customer-printer-serial">
                            Serial: {
                              printer.serial_number
                              ?? '—'
                            }
                          </span>

                        </div>


                        <span
                          className={
                            `fleet-status ${status.className}`
                          }
                        >
                          {status.label}
                        </span>

                      </div>


                      <div className="customer-printer-meta">

                        <div>
                          <span>
                            Ink
                          </span>

                          <strong>
                            {
                              printer.ink_name
                              || '—'
                            }
                          </strong>
                        </div>


                        <div>
                          <span>
                            Last Seen
                          </span>

                          <strong>
                            {
                              formatLastSeen(
                                printer.last_seen
                              )
                            }
                          </strong>
                        </div>

                      </div>


                      <div className="customer-printer-metrics">

                        <div className="customer-mini-metric">
                          <span>
                            Print Count
                          </span>

                          <strong>
                            {
                              printer.print_count
                              ?? '—'
                            }
                          </strong>
                        </div>


                        <div className="customer-mini-metric">
                          <span>
                            Ambient Temperature
                          </span>

                          <strong>
                            {
                              printer.temperature_c
                              ?? '—'
                            }

                            {
                              printer.temperature_c
                              !== null
                              && printer.temperature_c
                                !== undefined
                              && (
                                <small>
                                  °C
                                </small>
                              )
                            }
                          </strong>
                        </div>


                        <div className="customer-mini-metric">
                          <span>
                            Ink Pressure
                          </span>

                          <strong>
                            {
                              printer.pressure_mpa
                              ?? '—'
                            }

                            {
                              printer.pressure_mpa
                              !== null
                              && printer.pressure_mpa
                                !== undefined
                              && (
                                <small>
                                  MPa
                                </small>
                              )
                            }
                          </strong>
                        </div>


                        <div className="customer-mini-metric">
                          <span>
                            Ink Remaining
                          </span>

                          <strong>
                            {
                              nativeLevel(
                                printer
                                  .ink_remaining_label,
                                printer
                                  .ink_remaining_raw
                              )
                            }
                          </strong>
                        </div>


                        <div className="customer-mini-metric">
                          <span>
                            Makeup Remaining
                          </span>

                          <strong>
                            {
                              nativeLevel(
                                printer
                                  .makeup_remaining_label,
                                printer
                                  .makeup_remaining_raw
                              )
                            }
                          </strong>
                        </div>


                        <div className="customer-mini-metric">
                          <span>
                            Operating Time
                          </span>

                          <strong>
                            {
                              printer
                                .ink_operating_time_hours
                              ?? '—'
                            }

                            {
                              printer
                                .ink_operating_time_hours
                              !== null
                              && printer
                                .ink_operating_time_hours
                                !== undefined
                              && (
                                <small>
                                  h
                                </small>
                              )
                            }
                          </strong>
                        </div>

                      </div>

                    </article>
                  )
                }
              )
            }

          </div>
        )
      }

    </div>
  )
}
