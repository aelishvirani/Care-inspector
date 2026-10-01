import {
  useMemo,
  useState,
} from 'react'

import {
  usePrinters,
} from '../hooks/usePrinters'

import {
  useHistory,
} from '../hooks/useHistory'

import HistoryLineChart
  from '../components/charts/HistoryLineChart'


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
        char => char.toUpperCase()
      )
  }

  if (
    raw !== null
    && raw !== undefined
  ) {
    return `Level ${raw}`
  }

  return '-'
}


export default function HistoryPage() {

  const {
    printers,
  } = usePrinters()


  const [
    deviceId,
    setDeviceId,
  ] = useState('')


  const [
    fromTime,
    setFromTime,
  ] = useState('')


  const [
    toTime,
    setToTime,
  ] = useState('')


  const filters = useMemo(
    () => ({
      deviceId,
      fromTime:
        toIsoLocal(fromTime),
      toTime:
        toIsoLocal(toTime),
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
  } = useHistory(filters)


  const selectedPrinter =
    printers.find(
      printer =>
        printer.device_id === deviceId
    ) || null


  const latest =
    measurements[0] || null


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


  return (
    <div className="page">

      <div className="page-heading">

        <div>
          <h1>
            History
          </h1>

          <p>
            Historical printer
            measurements and trends
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


      <section className="panel">

        <div className="filter-toolbar">

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

              {printers.map(
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
                      printer.model_name
                        ? `${printer.model_name} — ${printer.device_id}`
                        : printer.device_id
                    }
                  </option>

                )
              )}

            </select>

          </div>


          <div className="filter-group">

            <label>
              From
            </label>

            <input
              type="datetime-local"
              value={fromTime}
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
              onChange={
                event =>
                  setToTime(
                    event.target.value
                  )
              }
            />

          </div>


          <button
            className="clear-filter-button"
            onClick={() => {
              setDeviceId('')
              setFromTime('')
              setToTime('')
            }}
          >
            Clear filters
          </button>

        </div>

      </section>


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
              latest?.print_count
              ?? '-'
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
              ?? '-'
            }
          </strong>

        </div>


        {
          isRealHitachi
          && (
            <div className="summary-card">

              <span>
                Serial Number
              </span>

              <strong>
                {
                  selectedPrinter
                    ?.serial_number
                  ?? '-'
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


      {loading ? (

        <div className="loading-panel">
          Loading history...
        </div>

      ) : (

        <div className="history-grid">

          <HistoryLineChart
            title="Ambient Temperature"
            subtitle="Printer-reported ambient temperature over time"
            data={measurements}
            dataKey="temperature_c"
            unit=" °C"
          />


          <HistoryLineChart
            title="Ink Pressure"
            subtitle="Printer-reported ink pressure over time"
            data={measurements}
            dataKey="pressure_mpa"
            unit=" MPa"
          />


          <HistoryLineChart
            title="Print Count"
            subtitle="Cumulative printer production counter"
            data={measurements}
            dataKey="print_count"
          />


          {
            hasInkPercentage
            && (
              <HistoryLineChart
                title="Ink Level"
                subtitle="Ink percentage over time"
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
                subtitle="Makeup percentage over time"
                data={measurements}
                dataKey="makeup_level_percent"
                unit="%"
              />
            )
          }

        </div>

      )}

    </div>
  )
}
