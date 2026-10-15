import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Link,
  useSearchParams,
} from 'react-router-dom'

import {
  usePrinters,
} from '../hooks/usePrinters'

import {
  useHistory,
} from '../hooks/useHistory'

import HistoryLineChart
  from '../components/charts/HistoryLineChart'


import {
  offlineReason,
} from '../utils/printerStatus'


function toIsoLocal(value) {
  if (!value) return ''

  return new Date(value)
    .toISOString()
}


function formatNativeLevel(
  label,
  raw
) {
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


function printerStatus(printer) {
  if (!printer) {
    return {
      label: 'Unknown',
      className: 'offline',
    }
  }

  if (!printer.online) {
    return {
      label: 'Offline',
      className: 'offline',
    }
  }

  if (
    printer.status === 'warning'
  ) {
    return {
      label: 'Warning',
      className: 'warning',
    }
  }

  if (
    printer.status === 'fault'
  ) {
    return {
      label: 'Fault',
      className: 'fault',
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


export default function HistoryPage() {

  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams()


  const {
    printers,
    loading: printersLoading,
  } = usePrinters()


  const queryDeviceId =
    searchParams.get(
      'device_id'
    ) || ''


  const [
    deviceId,
    setDeviceId,
  ] = useState(() => {
    if (queryDeviceId) {
      return queryDeviceId
    }

    return (
      sessionStorage.getItem(
        'care_inspector_history_device_id'
      )
      || ''
    )
  })


  const [
    fromTime,
    setFromTime,
  ] = useState('')


  const [
    toTime,
    setToTime,
  ] = useState('')


  /*
   * Handle direct navigation such as:
   *
   * /history?device_id=demo-printer-002
   */
  useEffect(() => {

    if (
      queryDeviceId
      && queryDeviceId !== deviceId
    ) {
      setDeviceId(
        queryDeviceId
      )

      sessionStorage.setItem(
        'care_inspector_history_device_id',
        queryDeviceId
      )
    }

  }, [
    queryDeviceId,
    deviceId,
  ])


  const filters = useMemo(
    () => ({
      deviceId,

      fromTime:
        toIsoLocal(
          fromTime
        ),

      toTime:
        toIsoLocal(
          toTime
        ),
    }),
    [
      deviceId,
      fromTime,
      toTime,
    ]
  )


  const {
    measurements,
    loading,
    error,
    refresh,
  } = useHistory(
    filters
  )


  const selectedPrinter =
    printers.find(
      printer =>
        printer.device_id
        === deviceId
    ) || null


  const latest =
    measurements[0]
    || null


  const status =
    printerStatus(
      selectedPrinter
    )


  const hasInkPercentage =
    measurements.some(
      item =>
        item.ink_level_percent
          !== null
        && item.ink_level_percent
          !== undefined
    )


  const hasMakeupPercentage =
    measurements.some(
      item =>
        item.makeup_level_percent
          !== null
        && item.makeup_level_percent
          !== undefined
    )


  const isRealHitachi =
    selectedPrinter?.source
      === 'hitachi_modbus'


  function changePrinter(
    nextDeviceId
  ) {
    setDeviceId(
      nextDeviceId
    )

    setFromTime('')
    setToTime('')

    if (nextDeviceId) {
      sessionStorage.setItem(
        'care_inspector_history_device_id',
        nextDeviceId
      )

      setSearchParams({
        device_id:
          nextDeviceId,
      })

    } else {
      sessionStorage.removeItem(
        'care_inspector_history_device_id'
      )

      setSearchParams({})
    }
  }


  function clearDateFilters() {
    setFromTime('')
    setToTime('')
  }


  if (printersLoading) {
    return (
      <div className="loading-panel">
        Loading printers...
      </div>
    )
  }


  if (
    !printersLoading
    && printers.length === 0
  ) {
    return (
      <div className="page">

        <div className="page-heading">
          <div>
            <h1>History</h1>

            <p>
              Historical printer
              measurements and trends
            </p>
          </div>
        </div>

        <div className="empty-state">
          No printers are available.
        </div>

      </div>
    )
  }


  return (
    <div className="page">

      <div className="page-heading">

        <div>

          <span
            style={{
              display: 'block',
              marginBottom: '5px',
              color: '#1595a3',
              fontSize: '11px',
              fontWeight: 800,
              textTransform:
                'uppercase',
              letterSpacing:
                '0.8px',
            }}
          >
            Printer History
          </span>

          <h1>
            {
              selectedPrinter
                ?.display_name
              || 'Select Printer'
            }
          </h1>

          <p>
            Historical measurements
            for one selected printer.
          </p>

        </div>


        <button
          className="secondary-button"
          onClick={refresh}
          disabled={!deviceId}
        >
          Refresh
        </button>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <section className="panel">

        <div className="filter-toolbar history-inline-toolbar">

          <div className="filter-group history-printer-filter">

            <label>
              Printer
            </label>

            <select
              value={deviceId}
              onChange={
                event =>
                  changePrinter(
                    event.target.value
                  )
              }
            >

              <option value="">
                Select printer
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
                        || printer.model_name
                        || printer.device_id
                      }

                      {
                        printer.model_name
                        ? ` — ${printer.model_name}`
                        : ''
                      }

                      {
                        printer.serial_number
                        ? ` — S/N ${printer.serial_number}`
                        : ''
                      }

                    </option>
                  )
                )
              }

            </select>

          </div>


          <div className="filter-group">

            <label>
              From
            </label>

            <input
              type="datetime-local"
              value={fromTime}
              disabled={!deviceId}
              onChange={
                event =>
                  setFromTime(
                    event.target.value
                  )
              }
            />

          </div>


          <div className="filter-group">

            <label>
              To
            </label>

            <input
              type="datetime-local"
              value={toTime}
              disabled={!deviceId}
              onChange={
                event =>
                  setToTime(
                    event.target.value
                  )
              }
            />

          </div>


          {
            (
              fromTime
              || toTime
            )
            && (
              <button
                type="button"
                className="clear-filter-button"
                onClick={
                  clearDateFilters
                }
              >
                Clear dates
              </button>
            )
          }

        </div>

      </section>


{
        selectedPrinter
        && (
          <section
            className="panel"
            style={{
              marginBottom: '20px',
            }}
          >

            <div
              style={{
                display: 'flex',
                justifyContent:
                  'space-between',
                alignItems:
                  'flex-start',
                gap: '20px',
                padding:
                  '20px 22px',
                borderBottom:
                  '1px solid #e7ebee',
              }}
            >

              <div>

                <h2
                  style={{
                    margin: 0,
                    fontSize: '20px',
                  }}
                >
                  {
                    selectedPrinter
                      .display_name
                    || selectedPrinter
                      .model_name
                    || 'Printer'
                  }
                </h2>


                <div
                  style={{
                    marginTop: '5px',
                    color: '#75818a',
                    fontSize: '13px',
                  }}
                >
                  {
                    selectedPrinter
                      .model_name
                    || 'Unknown model'
                  }

                  {
                    selectedPrinter
                      .serial_number
                    && (
                      <>
                        {' · Serial '}
                        {
                          selectedPrinter
                            .serial_number
                        }
                      </>
                    )
                  }

                  {
                    selectedPrinter
                      .location
                    && (
                      <>
                        {' · '}
                        {
                          selectedPrinter
                            .location
                        }
                      </>
                    )
                  }
                </div>


                <div
                  style={{
                    marginTop: '7px',
                    color: '#8a959d',
                    fontFamily:
                      'monospace',
                    fontSize: '11px',
                  }}
                >
                  {
                    selectedPrinter
                      .device_id
                  }
                </div>

              </div>


              <div className="printer-status-block">

                <span
                  className={
                    `fleet-status ${status.className}`
                  }
                >
                  {status.label}
                </span>

                {
                  !selectedPrinter.online
                  && (
                    <small className="offline-reason">
                      {
                        offlineReason(
                          selectedPrinter
                        )
                      }
                    </small>
                  )
                }

              </div>

            </div>


            <div
              style={{
                display: 'flex',
                gap: '10px',
                flexWrap: 'wrap',
                padding:
                  '12px 20px',
              }}
            >

              <Link
                className="secondary-button"
                to={
                  `/printers/${encodeURIComponent(
                    selectedPrinter
                      .device_id
                  )}`
                }
              >
                Printer Details
              </Link>


              <Link
                className="secondary-button"
                to={
                  `/alerts?device_id=${encodeURIComponent(
                    selectedPrinter
                      .device_id
                  )}`
                }
              >
                Alerts
              </Link>

            </div>

          </section>
        )
      }


      <div className="history-summary-grid">

        <div className="summary-card">

          <span>
            Measurements
          </span>

          <strong>
            {measurements.length}
          </strong>

        </div>


        <div className="summary-card">

          <span>
            Latest Print Count
          </span>

          <strong>
            {
              latest
                ?.print_count
              ?? '—'
            }
          </strong>

        </div>


        <div className="summary-card">

          <span>
            Latest Status
          </span>

          <strong>
            {
              latest
                ?.status
                ?.replaceAll(
                  '_',
                  ' '
                )
                ?.toUpperCase()
              ?? '—'
            }
          </strong>

        </div>


        <div className="summary-card">

          <span>
            Serial Number
          </span>

          <strong>
            {
              selectedPrinter
                ?.serial_number
              ?? '—'
            }
          </strong>

        </div>


        {
          isRealHitachi
          && (
            <div className="summary-card">

              <span>
                Ink Remaining
              </span>

              <strong>
                {
                  formatNativeLevel(
                    latest
                      ?.ink_remaining_label,
                    latest
                      ?.ink_remaining_raw
                  )
                }
              </strong>

            </div>
          )
        }


        {
          isRealHitachi
          && (
            <div className="summary-card">

              <span>
                Makeup Remaining
              </span>

              <strong>
                {
                  formatNativeLevel(
                    latest
                      ?.makeup_remaining_label,
                    latest
                      ?.makeup_remaining_raw
                  )
                }
              </strong>

            </div>
          )
        }

      </div>


      {
        loading
        ? (
          <div className="loading-panel">
            Loading history...
          </div>
        )

        : measurements.length === 0
        ? (
          <div className="empty-state">
            No measurements found for
            this printer in the selected
            time range.
          </div>
        )

        : (
          <div className="history-grid">


            <HistoryLineChart
              title="Ambient Temperature"
              subtitle={
                `${
                  selectedPrinter
                    ?.display_name
                  || 'Selected printer'
                } — printer-reported ambient temperature`
              }
              data={measurements}
              dataKey="temperature_c"
              unit=" °C"
            />


            <HistoryLineChart
              title="Ink Pressure"
              subtitle={
                `${
                  selectedPrinter
                    ?.display_name
                  || 'Selected printer'
                } — printer-reported ink pressure`
              }
              data={measurements}
              dataKey="pressure_mpa"
              unit=" MPa"
            />


            <HistoryLineChart
              title="Print Count"
              subtitle={
                `${
                  selectedPrinter
                    ?.display_name
                  || 'Selected printer'
                } — cumulative production count`
              }
              data={measurements}
              dataKey="print_count"
              unit=""
            />


            {
              hasInkPercentage
              && (
                <HistoryLineChart
                  title="Ink Level"
                  subtitle={
                    `${
                      selectedPrinter
                        ?.display_name
                      || 'Selected printer'
                    } — ink level over time`
                  }
                  data={measurements}
                  dataKey="ink_level_percent"
                  unit="%"
                />
              )
            }


            {
              hasMakeupPercentage
              && (
                <HistoryLineChart
                  title="Makeup Level"
                  subtitle={
                    `${
                      selectedPrinter
                        ?.display_name
                      || 'Selected printer'
                    } — makeup level over time`
                  }
                  data={measurements}
                  dataKey="makeup_level_percent"
                  unit="%"
                />
              )
            }

          </div>
        )
      }

    </div>
  )
}
