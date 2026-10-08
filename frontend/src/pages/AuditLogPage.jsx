import {
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


  async function load() {
    try {
      setError(null)

      setRows(
        await getAuditLog({
          limit: 1000,
          category,
          outcome,
        })
      )

    } catch (err) {
      setError(err.message)
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
          row =>
            [
              row.actor_email,
              row.actor_role,
              row.category,
              row.action,
              row.outcome,
              row.object_type,
              row.object_id,
              row.path,
              row.ip_address,
              row.details,
              row.error_message,
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
        rows,
        search,
      ]
    )


  return (
    <div className="page">

      <div className="page-header">

        <div>
          <h1>
            System Activity Log
          </h1>

          <p>
            Authentication, security,
            users, printers, collectors,
            alerts and API activity
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
        >
          Refresh
        </button>

      </div>


      <div className="filter-toolbar">

        <div className="filter-group">
          <label>Category</label>

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
              All
            </option>

            <option value="AUTH">
              Authentication
            </option>

            <option value="SECURITY">
              Security
            </option>

            <option value="HTTP">
              API
            </option>

            <option value="USER">
              Users
            </option>

            <option value="CUSTOMER">
              Customers
            </option>

            <option value="DEVICE">
              Devices
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

            <option value="GENERAL">
              General
            </option>
          </select>
        </div>


        <div className="filter-group">
          <label>Result</label>

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
              All
            </option>

            <option value="SUCCESS">
              Success
            </option>

            <option value="FAILURE">
              Failure
            </option>
          </select>
        </div>


        <div className="filter-group">
          <label>Search</label>

          <input
            value={search}
            placeholder={
              'User, action, printer, IP...'
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


      <section className="panel">

        <p>
          {filteredRows.length}
          {' '}
          events
        </p>

        <div className="alert-table-wrapper">

          <table className="alert-table">

            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Role</th>
                <th>Category</th>
                <th>Action</th>
                <th>Result</th>
                <th>HTTP</th>
                <th>Object</th>
                <th>IP</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>

              {
                filteredRows.map(
                  row => (
                    <tr key={row.id}>

                      <td>
                        {
                          formatDateTime(
                            row.created_at
                          )
                        }
                      </td>

                      <td>
                        {row.actor_email}
                      </td>

                      <td>
                        {row.actor_role}
                      </td>

                      <td>
                        {
                          row.category
                          || '—'
                        }
                      </td>

                      <td>
                        {row.action}
                      </td>

                      <td>
                        {
                          row.outcome
                          || '—'
                        }
                      </td>

                      <td>
                        {
                          row.method
                            ? `${row.method} ${
                                row.status_code
                                ?? ''
                              }`
                            : '—'
                        }

                        {
                          row.path
                            ? (
                              <div>
                                {row.path}
                              </div>
                            )
                            : null
                        }
                      </td>

                      <td>
                        {
                          row.object_type
                          || '—'
                        }

                        {
                          row.object_id
                            ? ` #${row.object_id}`
                            : ''
                        }
                      </td>

                      <td>
                        {
                          row.ip_address
                          || '—'
                        }
                      </td>

                      <td>
                        {
                          row.error_message
                          || row.details
                          || '—'
                        }

                        {
                          row.old_value
                          && (
                            <div>
                              Old:
                              {' '}
                              {row.old_value}
                            </div>
                          )
                        }

                        {
                          row.new_value
                          && (
                            <div>
                              New:
                              {' '}
                              {row.new_value}
                            </div>
                          )
                        }
                      </td>

                    </tr>
                  )
                )
              }

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}
