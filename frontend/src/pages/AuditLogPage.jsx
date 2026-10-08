import {
  Fragment,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getAuditLog,
} from '../api/adminApi'

import {
  formatDateTime,
} from '../utils/formatters'

import '../styles/audit-log.css'


const ACTION_LABELS = {
  LOGIN_SUCCESS: 'Login successful',
  LOGIN_FAILED: 'Login failed',
  LOGOUT: 'Logged out',

  USER_CREATED: 'User created',
  USER_UPDATED: 'User updated',

  CUSTOMER_CREATED: 'Customer created',
  CUSTOMER_UPDATED: 'Customer updated',

  DEVICE_REGISTERED: 'Printer registered',
  DEVICE_ASSIGNED: 'Printer assigned',
  DEVICE_UNASSIGNED: 'Printer unassigned',
  DEVICE_UPDATED: 'Printer updated',

  ALERT_CREATED: 'Alert created',
  ALERT_RESOLVED: 'Alert resolved',
  ALERT_ACKNOWLEDGED: 'Alert acknowledged',

  COLLECTOR_CONNECTED: 'Collector connected',
  COLLECTOR_DISCONNECTED: 'Collector disconnected',
  COLLECTOR_ERROR: 'Collector error',

  SYSTEM_START: 'Backend service started',
  SYSTEM_STOP: 'Backend service stopped',

  ACCESS_DENIED: 'Access denied',
  API_REQUEST: 'System request',
}


const ROLE_LABELS = {
  ADMIN: 'Admin',
  TECHNICIAN: 'Technician',
  CUSTOMER: 'Customer',
  SYSTEM: 'System',
  ANONYMOUS: 'Anonymous',
}


const CATEGORY_LABELS = {
  AUTH: 'Authentication',
  SECURITY: 'Security',
  HTTP: 'System access',
  USER: 'Users',
  CUSTOMER: 'Customers',
  DEVICE: 'Printers',
  COLLECTOR: 'Collectors',
  ALERT: 'Alerts',
  SYSTEM: 'System',
  GENERAL: 'General',
}


function actionLabel(action) {
  return (
    ACTION_LABELS[action]
    || action
      ?.replaceAll('_', ' ')
      ?.toLowerCase()
      ?.replace(
        /^\w/,
        value => value.toUpperCase()
      )
    || 'Unknown activity'
  )
}


function roleLabel(role) {
  return (
    ROLE_LABELS[role]
    || role
    || '—'
  )
}


function categoryLabel(category) {
  return (
    CATEGORY_LABELS[category]
    || category
    || '—'
  )
}


function objectLabel(row) {
  if (
    row.action === 'LOGIN_SUCCESS'
    || row.action === 'LOGIN_FAILED'
    || row.action === 'LOGOUT'
  ) {
    return 'User account'
  }

  if (
    row.action === 'SYSTEM_START'
    || row.action === 'SYSTEM_STOP'
  ) {
    return 'Care-Inspector API'
  }

  if (!row.object_type) {
    return '—'
  }

  const labels = {
    device: 'Printer',
    customer: 'Customer',
    user: 'User',
    alert: 'Alert',
    backend: 'Backend',
    collector: 'Collector',
  }

  const label =
    labels[row.object_type]
    || row.object_type

  if (!row.object_id) {
    return label
  }

  return `${label}: ${row.object_id}`
}


function statusLabel(row) {
  if (row.outcome === 'FAILURE') {
    return 'Failed'
  }

  if (row.outcome === 'SUCCESS') {
    return 'Success'
  }

  return row.outcome || '—'
}


function detailsLabel(row) {
  if (
    row.old_value
    && row.new_value
  ) {
    return `${row.old_value} → ${row.new_value}`
  }

  if (row.new_value) {
    return row.new_value
  }

  if (row.old_value) {
    return row.old_value
  }

  if (row.error_message) {
    return row.error_message
  }

  if (row.details) {
    return row.details
  }

  if (row.action === 'LOGIN_SUCCESS') {
    return 'User authenticated successfully'
  }

  if (row.action === 'LOGIN_FAILED') {
    return 'Invalid credentials or inactive account'
  }

  if (row.action === 'LOGOUT') {
    return 'User session ended'
  }

  if (row.action === 'SYSTEM_START') {
    return 'Care-Inspector backend started'
  }

  if (row.action === 'SYSTEM_STOP') {
    return 'Care-Inspector backend stopped'
  }

  return '—'
}


export default function AuditLogPage() {
  const [
    rows,
    setRows,
  ] = useState([])

  const [
    error,
    setError,
  ] = useState(null)

  const [
    loading,
    setLoading,
  ] = useState(false)

  const [
    category,
    setCategory,
  ] = useState('')

  const [
    outcome,
    setOutcome,
  ] = useState('')

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    expandedId,
    setExpandedId,
  ] = useState(null)


  async function load() {
    try {
      setLoading(true)
      setError(null)

      const data =
        await getAuditLog({
          limit: 1000,
          category,
          outcome,
        })

      setRows(data)

    } catch (err) {
      setError(err.message)

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    load()
  }, [
    category,
    outcome,
  ])


  const filteredRows =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        if (!term) {
          return rows
        }

        return rows.filter(
          row => {
            const values = [
              row.actor_email,
              roleLabel(
                row.actor_role
              ),
              actionLabel(
                row.action
              ),
              row.action,
              categoryLabel(
                row.category
              ),
              row.object_type,
              row.object_id,
              objectLabel(row),
              row.ip_address,
              detailsLabel(row),
              row.path,
              row.status_code,
            ]

            return values
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
      [
        rows,
        search,
      ]
    )


  return (
    <div className="page audit-page">

      <div className="page-header">

        <div>
          <h1>
            Access & Activity Log
          </h1>

          <p>
            Complete record of user,
            security, printer and system
            activity.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
          disabled={loading}
        >
          {
            loading
              ? 'Loading...'
              : 'Refresh'
          }
        </button>

      </div>


      <div className="audit-toolbar">

        <div className="audit-filter">
          <label>
            Area
          </label>

          <select
            value={category}
            onChange={
              event =>
                setCategory(
                  event.target.value
                )
            }
          >
            <option value="">
              All areas
            </option>

            <option value="AUTH">
              Authentication
            </option>

            <option value="SECURITY">
              Security
            </option>

            <option value="USER">
              Users
            </option>

            <option value="CUSTOMER">
              Customers
            </option>

            <option value="DEVICE">
              Printers
            </option>

            <option value="COLLECTOR">
              Collectors
            </option>

            <option value="ALERT">
              Alerts
            </option>

            <option value="SYSTEM">
              System
            </option>

            <option value="HTTP">
              System access
            </option>
          </select>
        </div>


        <div className="audit-filter">
          <label>
            Result
          </label>

          <select
            value={outcome}
            onChange={
              event =>
                setOutcome(
                  event.target.value
                )
            }
          >
            <option value="">
              All results
            </option>

            <option value="SUCCESS">
              Success
            </option>

            <option value="FAILURE">
              Failed
            </option>
          </select>
        </div>


        <div className="audit-search">
          <label>
            Search
          </label>

          <input
            value={search}
            placeholder={
              'User, printer, action, IP...'
            }
            onChange={
              event =>
                setSearch(
                  event.target.value
                )
            }
          />
        </div>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <section className="audit-panel">

        <div className="audit-panel-header">

          <div>
            <strong>
              Activity history
            </strong>

            <span>
              {filteredRows.length}
              {' '}
              entries
            </span>
          </div>

          <small>
            Latest activity first
          </small>

        </div>


        <div className="audit-table-wrapper">

          <table className="audit-table">

            <thead>
              <tr>
                <th>Date & Time</th>
                <th>User / Source</th>
                <th>Role</th>
                <th>Action</th>
                <th>IP Address</th>
                <th>Object / Device</th>
                <th>Result</th>
                <th>Details</th>
              </tr>
            </thead>


            <tbody>

              {
                filteredRows.map(
                  row => (
                    <Fragment
                      key={row.id}
                    >

                      <tr>

                        <td
                          className="audit-time"
                        >
                          {
                            formatDateTime(
                              row.created_at
                            )
                          }
                        </td>


                        <td>
                          <strong
                            className="audit-user"
                          >
                            {
                              row.actor_email
                              || 'SYSTEM'
                            }
                          </strong>
                        </td>


                        <td>
                          <span
                            className={
                              `audit-role audit-role-${
                                (
                                  row.actor_role
                                  || 'system'
                                )
                                  .toLowerCase()
                              }`
                            }
                          >
                            {
                              roleLabel(
                                row.actor_role
                              )
                            }
                          </span>
                        </td>


                        <td>
                          <div
                            className="audit-action"
                          >
                            {
                              actionLabel(
                                row.action
                              )
                            }
                          </div>

                          <small
                            className="audit-area"
                          >
                            {
                              categoryLabel(
                                row.category
                              )
                            }
                          </small>
                        </td>


                        <td
                          className="audit-ip"
                        >
                          {
                            row.ip_address
                            || '—'
                          }
                        </td>


                        <td>
                          {
                            objectLabel(
                              row
                            )
                          }
                        </td>


                        <td>
                          <span
                            className={
                              `audit-status ${
                                row.outcome
                                === 'FAILURE'
                                  ? 'failed'
                                  : 'success'
                              }`
                            }
                          >
                            {
                              statusLabel(
                                row
                              )
                            }

                            {
                              row.status_code
                              ? ` · ${row.status_code}`
                              : ''
                            }
                          </span>
                        </td>


                        <td>
                          <div
                            className="audit-main-details"
                          >
                            {
                              detailsLabel(
                                row
                              )
                            }
                          </div>

                          <button
                            type="button"
                            className="audit-details-button"
                            onClick={
                              () =>
                                setExpandedId(
                                  expandedId
                                  === row.id
                                    ? null
                                    : row.id
                                )
                            }
                          >
                            {
                              expandedId
                              === row.id
                                ? 'Hide technical details'
                                : 'Technical details'
                            }
                          </button>
                        </td>

                      </tr>


                      {
                        expandedId
                        === row.id
                        && (
                          <tr
                            className="audit-expanded-row"
                          >
                            <td
                              colSpan="8"
                            >
                              <div
                                className="audit-details-grid"
                              >

                                <div>
                                  <span>
                                    Raw action
                                  </span>

                                  <strong>
                                    {
                                      row.action
                                      || '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    Area
                                  </span>

                                  <strong>
                                    {
                                      categoryLabel(
                                        row.category
                                      )
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    HTTP
                                  </span>

                                  <strong>
                                    {
                                      row.method
                                      ? `${row.method} ${
                                          row.status_code
                                          ?? ''
                                        }`
                                      : '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    Endpoint
                                  </span>

                                  <strong>
                                    {
                                      row.path
                                      || '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    Object type
                                  </span>

                                  <strong>
                                    {
                                      row.object_type
                                      || '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    Object ID
                                  </span>

                                  <strong>
                                    {
                                      row.object_id
                                      || '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    IP Address
                                  </span>

                                  <strong>
                                    {
                                      row.ip_address
                                      || '—'
                                    }
                                  </strong>
                                </div>


                                <div>
                                  <span>
                                    HTTP Status
                                  </span>

                                  <strong>
                                    {
                                      row.status_code
                                      ?? '—'
                                    }
                                  </strong>
                                </div>


                                {
                                  row.old_value
                                  && (
                                    <div>
                                      <span>
                                        Previous value
                                      </span>

                                      <strong>
                                        {
                                          row.old_value
                                        }
                                      </strong>
                                    </div>
                                  )
                                }


                                {
                                  row.new_value
                                  && (
                                    <div>
                                      <span>
                                        New value
                                      </span>

                                      <strong>
                                        {
                                          row.new_value
                                        }
                                      </strong>
                                    </div>
                                  )
                                }


                                {
                                  row.error_message
                                  && (
                                    <div>
                                      <span>
                                        Error
                                      </span>

                                      <strong>
                                        {
                                          row.error_message
                                        }
                                      </strong>
                                    </div>
                                  )
                                }

                              </div>
                            </td>
                          </tr>
                        )
                      }

                    </Fragment>
                  )
                )
              }


              {
                !loading
                && filteredRows.length
                === 0
                && (
                  <tr>
                    <td
                      colSpan="8"
                      className="audit-empty"
                    >
                      No audit entries
                      match the selected
                      filters.
                    </td>
                  </tr>
                )
              }

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}
