import {
  useMemo,
  useState,
} from 'react'

import {
  Link,
  useNavigate,
} from 'react-router-dom'

import {
  usePrinters,
} from '../hooks/usePrinters'

import '../styles/role-panels.css'


function getStatus(printer) {
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


function remainingValue(
  percent,
  label,
  raw
) {
  if (
    percent !== null
    && percent !== undefined
  ) {
    return `${percent}%`
  }

  if (label) {
    return label
      .replaceAll('_', ' ')
      .replace(
        /\b\w/g,
        char =>
          char.toUpperCase()
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


export default function OverviewPage() {
  const navigate =
    useNavigate()

  const {
    printers,
    loading,
    error,
  } = usePrinters()

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    statusFilter,
    setStatusFilter,
  ] = useState('all')


  const filteredPrinters =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        return printers.filter(
          printer => {

            const state =
              getStatus(printer)

            const matchesSearch =
              !term
              || [
                printer.display_name,
                printer.device_id,
                printer.model_name,
                printer.serial_number,
                printer.location,
                printer.ink_name,
              ]
                .filter(Boolean)
                .some(
                  value =>
                    String(value)
                      .toLowerCase()
                      .includes(term)
                )

            const matchesStatus =
              statusFilter === 'all'
              || (
                statusFilter
                === 'online'
                && printer.online
              )
              || (
                statusFilter
                === 'offline'
                && !printer.online
              )
              || (
                statusFilter
                === 'warning'
                && printer.status
                  === 'warning'
              )
              || (
                statusFilter
                === 'fault'
                && printer.status
                  === 'fault'
              )
              || (
                statusFilter
                === 'stopped'
                && printer.status
                  === 'stopped'
              )

            return (
              matchesSearch
              && matchesStatus
            )
          }
        )
      },
      [
        printers,
        search,
        statusFilter,
      ]
    )


  const onlineCount =
    printers.filter(
      printer =>
        printer.online
    ).length

  const problemCount =
    printers.filter(
      printer =>
        !printer.online
        || printer.status
          === 'warning'
        || printer.status
          === 'fault'
    ).length


  if (loading) {
    return (
      <div className="loading-panel">
        Loading printer fleet...
      </div>
    )
  }


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>
          <span className="role-dashboard-eyebrow">
            Fleet Monitoring
          </span>

          <h1>
            Printer Overview
          </h1>

          <p>
            Live operational status of
            all monitored printers.
          </p>
        </div>

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
            {printers.length}
          </strong>

          <span className="role-kpi-hint">
            Total monitored devices
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
            {onlineCount}
          </strong>

          <span className="role-kpi-hint">
            Currently reporting
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
            {
              printers.length
              - onlineCount
            }
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
            {problemCount}
          </strong>

          <span className="role-kpi-hint">
            Offline, warning or fault
          </span>

        </div>

      </div>


      <div className="role-toolbar">

        <input
          className="role-search"
          type="search"
          placeholder={
            'Search printer, model, serial, location...'
          }
          value={search}
          onChange={
            event =>
              setSearch(
                event.target.value
              )
          }
        />


        <select
          className="role-filter"
          value={statusFilter}
          onChange={
            event =>
              setStatusFilter(
                event.target.value
              )
          }
        >
          <option value="all">
            All statuses
          </option>

          <option value="online">
            Online
          </option>

          <option value="offline">
            Offline
          </option>

          <option value="warning">
            Warning
          </option>

          <option value="fault">
            Fault
          </option>

          <option value="stopped">
            Stopped
          </option>
        </select>


        {
          (
            search
            || statusFilter !== 'all'
          )
          && (
            <button
              className="clear-filter-button"
              onClick={() => {
                setSearch('')
                setStatusFilter('all')
              }}
            >
              Clear filters
            </button>
          )
        }

      </div>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Printer Fleet
            </h2>

            <p>
              Select a printer to open
              its complete monitoring view.
            </p>
          </div>

          <div className="role-section-count">
            {
              filteredPrinters.length
            }
          </div>

        </div>

      </section>


      {
        filteredPrinters.length === 0
        ? (
          <div className="empty-state">
            No matching printers.
          </div>
        )
        : (
          <div className="customer-printer-grid">

            {
              filteredPrinters.map(
                printer => {

                  const state =
                    getStatus(printer)

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
                      style={{
                        cursor: 'pointer',
                      }}
                      onClick={() =>
                        navigate(
                          `/printers/${encodeURIComponent(
                            printer.device_id
                          )}`
                        )
                      }
                    >

                      <div className="customer-printer-top">

                        <div className="customer-printer-title">

                          <h2>
                            {
                              printer.display_name
                              || printer.model_name
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
                                  {
                                    printer.location
                                  }
                                </>
                              )
                            }
                          </p>

                          <span className="customer-printer-serial">
                            Serial:
                            {' '}
                            {
                              printer.serial_number
                              ?? '—'
                            }
                          </span>

                        </div>


                        <span
                          className={
                            `fleet-status ${state.className}`
                          }
                        >
                          {state.label}
                        </span>

                      </div>


                      <div className="customer-printer-meta">

                        <div>
                          <span>
                            Source
                          </span>

                          <strong>
                            {
                              printer.source
                              || '—'
                            }
                          </strong>
                        </div>


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
                              remainingValue(
                                printer
                                  .ink_level_percent,
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
                              remainingValue(
                                printer
                                  .makeup_level_percent,
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
                            Location
                          </span>

                          <strong>
                            {
                              printer.location
                              || '—'
                            }
                          </strong>

                        </div>

                      </div>


                      <div
                        style={{
                          display: 'flex',
                          gap: '8px',
                          padding: '14px 18px',
                          borderTop:
                            '1px solid #e7ecef',
                          flexWrap: 'wrap',
                        }}
                        onClick={
                          event =>
                            event.stopPropagation()
                        }
                      >

                        <Link
                          className="secondary-button"
                          to={
                            `/printers/${encodeURIComponent(
                              printer.device_id
                            )}`
                          }
                        >
                          Details
                        </Link>


                        <Link
                          className="secondary-button"
                          to={
                            `/history?device_id=${encodeURIComponent(
                              printer.device_id
                            )}`
                          }
                        >
                          History
                        </Link>


                        <Link
                          className="secondary-button"
                          to={
                            `/alerts?device_id=${encodeURIComponent(
                              printer.device_id
                            )}`
                          }
                        >
                          Alerts
                        </Link>

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
