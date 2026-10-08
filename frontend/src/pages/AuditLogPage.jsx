import {
  useEffect,
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


  async function load() {
    try {
      setError(null)

      setRows(
        await getAuditLog()
      )

    } catch (err) {
      setError(err.message)
    }
  }


  useEffect(() => {
    load()
  }, [])


  return (
    <div className="page">

      <div className="page-header">

        <div>
          <h1>Audit Log</h1>

          <p>
            Administrative activity history
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
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

        <div className="alert-table-wrapper">

          <table className="alert-table">

            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Role</th>
                <th>Action</th>
                <th>Object</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>

              {
                rows.map(
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
                        {row.action}
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
                        {row.details || '—'}
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
