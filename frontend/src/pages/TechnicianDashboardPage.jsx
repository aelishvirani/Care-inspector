import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  apiGet,
} from '../api/client'

import PrinterStatusFilter
  from '../components/filters/PrinterStatusFilter'

import {
  offlineReason,
} from '../utils/printerStatus'

import '../styles/role-panels.css'


const REFRESH_INTERVAL = 5000


function printerState(
  printer
) {
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

  if (printer.status === 'stopped') {
    return {
      label: 'Stopped',
      className: 'stopped',
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


export default function TechnicianDashboardPage() {
  const [
    printers,
    setPrinters,
  ] = useState([])

  const [
    customers,
    setCustomers,
  ] = useState([])

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    statusFilter,
    setStatusFilter,
  ] = useState('all')

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  async function refresh() {
    try {
      const [
        printerData,
        customerData,
      ] = await Promise.all([
        apiGet(
          '/secure/devices'
        ),

        apiGet(
          '/secure/customers'
        ),
      ])

      setPrinters(
        printerData
      )

      setCustomers(
        customerData
      )

      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        'Unable to load Technik dashboard'
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
    () => ({
      customers:
        customers.length,

      printers:
        printers.length,

      online:
        printers.filter(
          printer =>
            printer.online
        ).length,

      problems:
        printers.filter(
          printer =>
            !printer.online
            || printer.status
              === 'warning'
            || printer.status
              === 'fault'
        ).length,
    }),
    [
      customers,
      printers,
    ]
  )


  const problems = useMemo(
    () =>
      printers.filter(
        printer =>
          !printer.online
          || printer.status
            === 'warning'
          || printer.status
            === 'fault'
      ),
    [printers]
  )


  const filteredPrinters =
    useMemo(
      () => {

        const term =
          search
            .trim()
            .toLowerCase()

        return printers.filter(
          printer => {

            const customer =
              customers.find(
                item =>
                  item.id
                  === printer.customer_id
              )

            const state =
              printerState(
                printer
              )

            const matchesSearch =
              !term
              || [
                printer.display_name,
                printer.device_id,
                printer.model_name,
                printer.serial_number,
                printer.location,
                customer?.name,
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
              || state.className
                === statusFilter

            return (
              matchesSearch
              && matchesStatus
            )
          }
        )
      },
      [
        printers,
        customers,
        search,
        statusFilter,
      ]
    )


  if (loading) {
    return (
      <div className="loading-panel">
        Loading Technik dashboard...
      </div>
    )
  }


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>
          <span className="role-dashboard-eyebrow">
            MFG Service Control
          </span>

          <h1>
            Technik Dashboard
          </h1>

          <p>
            All customers, monitored
            printers and service problems.
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
              Customers
            </span>

            <span className="role-kpi-icon">
              C
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.customers}
          </strong>

          <span className="role-kpi-hint">
            Managed customer accounts
          </span>
        </div>


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
            {summary.printers}
          </strong>

          <span className="role-kpi-hint">
            Across all customers
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
            Currently reporting
          </span>
        </div>


        <div className="role-kpi problem">
          <div className="role-kpi-top">
            <span className="role-kpi-label">
              Problems
            </span>

            <span className="role-kpi-icon">
              !
            </span>
          </div>

          <strong className="role-kpi-value">
            {summary.problems}
          </strong>

          <span className="role-kpi-hint">
            Require technician attention
          </span>
        </div>

      </div>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Needs Attention
            </h2>

            <p>
              Offline, warning and
              fault printers
            </p>
          </div>

          <div className="role-section-count">
            {problems.length}
          </div>

        </div>


        {
          problems.length === 0
          ? (
            <div className="role-healthy">

              <div className="role-healthy-icon">
                ✓
              </div>

              <div>
                <strong>
                  Fleet healthy
                </strong>

                <p>
                  No monitored printer
                  currently requires attention.
                </p>
              </div>

            </div>
          )
          : (
            <div className="technician-attention-list">

              {
                problems.map(
                  printer => {

                    const customer =
                      customers.find(
                        item =>
                          item.id
                          === printer.customer_id
                      )

                    const state =
                      printerState(
                        printer
                      )

                    return (
                      <div
                        key={
                          printer.device_id
                        }
                        className={
                          `technician-attention-item ${state.className}`
                        }
                      >

                        <div className="attention-primary">
                          <strong>
                            {
                              printer.display_name
                              || printer.device_id
                            }
                          </strong>

                          <span>
                            {
                              printer.model_name
                              || 'Unknown model'
                            }
                            {' · '}
                            {
                              printer.location
                              || 'No location'
                            }
                          </span>
                        </div>


                        <div className="attention-secondary">
                          {
                            customer?.name
                            || 'Unassigned customer'
                          }
                        </div>


                        <div className="attention-secondary">
                          Last seen:
                          {' '}
                          {
                            formatLastSeen(
                              printer.last_seen
                            )
                          }
                        </div>


                        <div className="printer-status-block">

                          <span
                            className={
                              `fleet-status attention-status ${state.className}`
                            }
                          >
                            {state.label}
                          </span>

                          {
                            !printer.online
                            && (
                              <small className="offline-reason">
                                {
                                  offlineReason(
                                    printer
                                  )
                                }
                              </small>
                            )
                          }

                        </div>

                      </div>
                    )
                  }
                )
              }

            </div>
          )
        }

      </section>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Customers
            </h2>

            <p>
              Service contacts and
              installed printer fleet
            </p>
          </div>

          <div className="role-section-count">
            {customers.length}
          </div>

        </div>


        <div className="technician-customer-grid">

          {
            customers.map(
              customer => {

                const customerPrinters =
                  printers.filter(
                    printer =>
                      printer.customer_id
                      === customer.id
                  )

                return (
                  <article
                    key={
                      customer.id
                    }
                    className="technician-customer-card"
                  >

                    <div className="technician-customer-card-top">

                      <div>
                        <h3>
                          {customer.name}
                        </h3>

                        <p className="technician-customer-card-address">
                          {
                            customer.address
                            || 'No address'
                          }
                        </p>
                      </div>

                      <div className="customer-printer-count">
                        {
                          customerPrinters.length
                        }
                      </div>

                    </div>


                    <div className="technician-contact-grid">

                      <div className="technician-contact-item">
                        <span>
                          Contact
                        </span>

                        <strong>
                          {
                            customer.contact_name
                            || '—'
                          }
                        </strong>
                      </div>


                      <div className="technician-contact-item">
                        <span>
                          Phone
                        </span>

                        <strong>
                          {
                            customer.contact_phone
                            || '—'
                          }
                        </strong>
                      </div>


                      <div className="technician-contact-item">
                        <span>
                          Email
                        </span>

                        <strong>
                          {
                            customer.contact_email
                            || '—'
                          }
                        </strong>
                      </div>


                      <div className="technician-contact-item">
                        <span>
                          Printers
                        </span>

                        <strong>
                          {
                            customerPrinters.length
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

      </section>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Printer Fleet
            </h2>

            <p>
              All monitored printers
              across every customer
            </p>
          </div>

          <div className="role-section-count">
            {
              filteredPrinters.length
            }
          </div>

        </div>


        <div
          style={{
            padding:
              '16px 18px 0',
          }}
        >

          <div className="printer-filter-toolbar">

            <div className="printer-filter-top-row">

              <input
                className="role-search"
                type="search"
                placeholder={
                  'Search printer, customer, model, serial...'
                }
                value={search}
                onChange={
                  event =>
                    setSearch(
                      event.target.value
                    )
                }
              />

              {
                (
                  search
                  || statusFilter !== 'all'
                )
                && (
                  <button
                    type="button"
                    className="clear-filter-button"
                    onClick={() => {
                      setSearch('')
                      setStatusFilter('all')
                    }}
                  >
                    Clear
                  </button>
                )
              }

            </div>


            <PrinterStatusFilter
              value={statusFilter}
              onChange={setStatusFilter}
            />

          </div>

        </div>


        <div className="fleet-table-wrapper">

          <table className="fleet-table">

            <thead>
              <tr>
                <th>
                  Printer
                </th>

                <th>
                  Customer
                </th>

                <th>
                  Model
                </th>

                <th>
                  Serial
                </th>

                <th>
                  Location
                </th>

                <th>
                  Last Seen
                </th>

                <th>
                  Status
                </th>
              </tr>
            </thead>


            <tbody>

              {
                filteredPrinters.map(
                  printer => {

                    const customer =
                      customers.find(
                        item =>
                          item.id
                          === printer.customer_id
                      )

                    const state =
                      printerState(
                        printer
                      )

                    return (
                      <tr
                        key={
                          printer.device_id
                        }
                      >

                        <td>
                          <span className="fleet-printer-name">
                            {
                              printer.display_name
                              || printer.device_id
                            }
                          </span>

                          <span className="fleet-printer-id">
                            {
                              printer.device_id
                            }
                          </span>
                        </td>


                        <td>
                          {
                            customer?.name
                            || 'Unassigned'
                          }
                        </td>


                        <td>
                          {
                            printer.model_name
                            || '—'
                          }
                        </td>


                        <td>
                          {
                            printer.serial_number
                            || '—'
                          }
                        </td>


                        <td>
                          {
                            printer.location
                            || '—'
                          }
                        </td>


                        <td>
                          {
                            formatLastSeen(
                              printer.last_seen
                            )
                          }
                        </td>


                        <td>
                          <div className="printer-status-block">

                            <span
                              className={
                                `fleet-status ${state.className}`
                              }
                            >
                              {state.label}
                            </span>

                            {
                              !printer.online
                              && (
                                <small className="offline-reason">
                                  {
                                    offlineReason(
                                      printer
                                    )
                                  }
                                </small>
                              )
                            }

                          </div>
                        </td>

                      </tr>
                    )
                  }
                )
              }

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}
