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

import '../styles/alert-filters.css'


const FILTERS = [
  {
    id: 'all',
    label: 'All',
    status: '',
    severity: '',
  },
  {
    id: 'active',
    label: 'Active',
    status: 'active',
    severity: '',
  },
  {
    id: 'acknowledged',
    label: 'Acknowledged',
    status: 'acknowledged',
    severity: '',
  },
  {
    id: 'resolved',
    label: 'Resolved',
    status: 'resolved',
    severity: '',
  },
  {
    id: 'warning',
    label: 'Warning',
    status: '',
    severity: 'warning',
  },
  {
    id: 'critical',
    label: 'Critical',
    status: '',
    severity: 'critical',
  },
]


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
    selectedFilter,
    setSelectedFilter,
  ] = useState('all')

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


  const activeFilter =
    FILTERS.find(
      filter =>
        filter.id
        === selectedFilter
    ) || FILTERS[0]


  const {
    printers,
  } = usePrinters()


  const {
    alerts,
    loading,
    error,
    refresh,
  } = useAlerts({
    status:
      activeFilter.status,

    severity:
      activeFilter.severity,

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
            Alerts &amp; Problems
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
            {filteredAlerts.length}
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

        <div className="alert-controls">

          <div className="alert-search-row">

            <input
              className="alert-search-input"
              type="search"
              placeholder={
                'Search problem, printer or message...'
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
              className="alert-printer-select"
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
                      {
                        printer.serial_number
                          ? ` · SN ${printer.serial_number}`
                          : ''
                      }
                    </option>
                  )
                )
              }

            </select>

          </div>


          <div className="alert-filter-row">

            {
              FILTERS.map(
                filter => (
                  <button
                    key={filter.id}
                    type="button"
                    className={
                      [
                        'alert-filter-button',
                        filter.id,
                        selectedFilter
                          === filter.id
                          ? 'selected'
                          : '',
                      ]
                        .filter(Boolean)
                        .join(' ')
                    }
                    onClick={() =>
                      setSelectedFilter(
                        filter.id
                      )
                    }
                  >
                    {filter.label}
                  </button>
                )
              )
            }

          </div>

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
