import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Link,
} from 'react-router-dom'

import {
  getCustomers,
  getManagedDevices,
  updateDevice,
} from '../api/managementApi'

import '../styles/management.css'


function lastSeen(value) {
  if (!value) return 'Never'

  const date = new Date(value)

  const seconds = Math.max(
    0,
    Math.round(
      (Date.now() - date.getTime()) / 1000
    )
  )

  if (seconds < 10) return 'Just now'
  if (seconds < 60) return `${seconds}s ago`

  const minutes =
    Math.round(seconds / 60)

  if (minutes < 60) {
    return `${minutes} min ago`
  }

  return date.toLocaleString()
}


function installationStatus(device) {
  if (device.online) {
    return 'Waiting for assignment'
  }

  if (device.last_seen) {
    return 'Offline / unassigned'
  }

  return 'Registered / waiting'
}


export default function UnassignedDevicesPage() {
  const [devices, setDevices] =
    useState([])

  const [customers, setCustomers] =
    useState([])

  const [
    assignments,
    setAssignments,
  ] = useState({})

  const [search, setSearch] =
    useState('')

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  async function refresh() {
    try {
      const [
        deviceRows,
        customerRows,
      ] = await Promise.all([
        getManagedDevices(),
        getCustomers(),
      ])

      setDevices(deviceRows)

      setCustomers(
        customerRows.filter(
          customer => customer.active
        )
      )

      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        err.message
        || 'Unable to load devices'
      )

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()

    const interval =
      setInterval(refresh, 5000)

    return () =>
      clearInterval(interval)
  }, [])


  const unassigned =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        return devices
          .filter(
            device =>
              device.customer_id === null
              || device.customer_id === undefined
          )
          .filter(
            device => {
              if (!term) return true

              return [
                device.device_id,
                device.display_name,
                device.model_name,
                device.serial_number,
                device.location,
                device.source,
              ]
                .filter(Boolean)
                .some(
                  value =>
                    String(value)
                      .toLowerCase()
                      .includes(term)
                )
            }
          )
      },
      [devices, search]
    )


  async function assign(deviceId) {
    const customerId =
      assignments[deviceId]

    if (!customerId) {
      setError(
        'Select a customer first.'
      )
      return
    }

    try {
      await updateDevice(
        deviceId,
        {
          customer_id:
            Number(customerId),
        }
      )

      setAssignments(
        previous => ({
          ...previous,
          [deviceId]: '',
        })
      )

      await refresh()

    } catch (err) {
      setError(err.message)
    }
  }


  if (loading) {
    return (
      <div className="loading-panel">
        Loading unassigned devices...
      </div>
    )
  }


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>
          <span className="role-dashboard-eyebrow">
            Installation
          </span>

          <h1>
            Unassigned Devices
          </h1>

          <p>
            New collectors and printers
            waiting for customer assignment.
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
              Waiting
            </span>

            <span className="role-kpi-icon">
              !
            </span>
          </div>

          <strong className="role-kpi-value">
            {unassigned.length}
          </strong>

          <span className="role-kpi-hint">
            Need customer assignment
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
            {
              unassigned.filter(
                device => device.online
              ).length
            }
          </strong>

          <span className="role-kpi-hint">
            Currently communicating
          </span>

        </div>

      </div>


      <div className="role-toolbar">

        <input
          className="role-search"
          type="search"
          value={search}
          placeholder="Search device ID, model, serial..."
          onChange={
            event =>
              setSearch(
                event.target.value
              )
          }
        />

      </div>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Waiting for Assignment
            </h2>

            <p>
              Select the customer who owns
              each installed printer.
            </p>
          </div>

          <div className="role-section-count">
            {unassigned.length}
          </div>

        </div>


        {
          unassigned.length === 0
          ? (
            <div className="role-healthy">

              <div className="role-healthy-icon">
                ✓
              </div>

              <div>
                <strong>
                  Everything assigned
                </strong>

                <p>
                  There are currently no
                  unassigned devices.
                </p>
              </div>

            </div>
          )
          : (
            <div className="management-printer-list">

              {
                unassigned.map(
                  device => (

                    <div
                      key={device.device_id}
                      className="management-printer-row"
                    >

                      <div>
                        <strong>
                          {
                            device.display_name
                            || device.model_name
                            || device.device_id
                          }
                        </strong>

                        <span>
                          {device.device_id}
                        </span>
                      </div>


                      <div>
                        <span>
                          Installation Status
                        </span>

                        <strong>
                          {
                            installationStatus(
                              device
                            )
                          }
                        </strong>
                      </div>


                      <div>
                        <span>
                          Last Seen
                        </span>

                        <strong>
                          {
                            lastSeen(
                              device.last_seen
                            )
                          }
                        </strong>
                      </div>


                      <div className="management-row-actions">

                        <select
                          value={
                            assignments[
                              device.device_id
                            ] || ''
                          }
                          onChange={
                            event =>
                              setAssignments(
                                previous => ({
                                  ...previous,

                                  [device.device_id]:
                                    event.target.value,
                                })
                              )
                          }
                        >
                          <option value="">
                            Select customer...
                          </option>

                          {
                            customers.map(
                              customer => (
                                <option
                                  key={customer.id}
                                  value={customer.id}
                                >
                                  {customer.name}
                                </option>
                              )
                            )
                          }
                        </select>


                        <button
                          className="management-primary-button"
                          onClick={() =>
                            assign(
                              device.device_id
                            )
                          }
                        >
                          Assign
                        </button>


                        <Link
                          className="secondary-button"
                          to={
                            `/printers/${encodeURIComponent(
                              device.device_id
                            )}`
                          }
                        >
                          View
                        </Link>

                      </div>

                    </div>

                  )
                )
              }

            </div>
          )
        }

      </section>

    </div>
  )
}
