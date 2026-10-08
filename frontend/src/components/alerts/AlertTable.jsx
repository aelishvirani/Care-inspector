import {
  useState,
} from 'react'

import {
  useAuth,
} from '../../auth/AuthContext'

import {
  acknowledgeAlert,
} from '../../services/alertService'

import {
  formatAlertType,
  formatDateTime,
} from '../../utils/formatters'


export default function AlertTable({
  alerts,
  onAcknowledged,
}) {
  const {
    user,
  } = useAuth()

  const [
    acknowledgingId,
    setAcknowledgingId,
  ] = useState(null)

  const [
    actionError,
    setActionError,
  ] = useState(null)


  async function handleAcknowledge(
    alert
  ) {
    try {
      setAcknowledgingId(
        alert.id
      )

      setActionError(null)

      await acknowledgeAlert(
        alert.id
      )

      if (onAcknowledged) {
        await onAcknowledged()
      }

    } catch (err) {
      console.error(err)

      setActionError(
        err.message
        || 'Unable to acknowledge alert'
      )

    } finally {
      setAcknowledgingId(null)
    }
  }


  if (alerts.length === 0) {
    return (
      <div className="empty-state">
        No alerts found.
      </div>
    )
  }


  return (
    <div>

      {actionError && (
        <div className="error-banner">
          {actionError}
        </div>
      )}


      <div className="alert-table-wrapper">

        <table className="alert-table">

          <thead>
            <tr>
              <th>Status</th>
              <th>Severity</th>
              <th>Printer</th>
              <th>Type</th>
              <th>Message</th>
              <th>Created</th>
              <th>Acknowledged</th>
              <th>Resolved</th>

              {
                user?.role
                  === 'TECHNICIAN'
                && (
                  <th>Action</th>
                )
              }

            </tr>
          </thead>


          <tbody>

            {alerts.map(alert => {

              const acknowledged =
                Boolean(
                  alert.acknowledged_at
                )

              let statusLabel =
                'Active'

              let statusClass =
                'alert-state active'

              if (!alert.active) {
                statusLabel =
                  'Resolved'

                statusClass =
                  'alert-state resolved'

              } else if (acknowledged) {
                statusLabel =
                  'Acknowledged'

                statusClass =
                  'alert-state acknowledged'
              }


              return (
                <tr key={alert.id}>

                  <td>
                    <span
                      className={
                        statusClass
                      }
                    >
                      {statusLabel}
                    </span>
                  </td>


                  <td>
                    <span
                      className={
                        `severity-badge ${
                          alert.severity
                        }`
                      }
                    >
                      {alert.severity}
                    </span>
                  </td>


                  <td>
                    <span
                      className="table-device-id"
                    >
                      {alert.device_id}
                    </span>
                  </td>


                  <td>
                    {
                      formatAlertType(
                        alert.alert_type
                      )
                    }
                  </td>


                  <td>
                    {alert.message}
                  </td>


                  <td>
                    {
                      formatDateTime(
                        alert.created_at
                      )
                    }
                  </td>


                  <td>
                    {
                      acknowledged
                        ? (
                          <div>
                            <div>
                              {
                                formatDateTime(
                                  alert
                                    .acknowledged_at
                                )
                              }
                            </div>

                            <small>
                              {
                                alert
                                  .acknowledged_by
                                || 'Technician'
                              }
                            </small>
                          </div>
                        )
                        : '-'
                    }
                  </td>


                  <td>
                    {
                      alert.resolved_at
                        ? formatDateTime(
                            alert.resolved_at
                          )
                        : '-'
                    }
                  </td>


                  {
                    user?.role
                      === 'TECHNICIAN'
                    && (
                      <td>

                        {
                          alert.active
                          && !acknowledged
                            ? (
                              <button
                                type="button"
                                className="secondary-button"
                                disabled={
                                  acknowledgingId
                                    === alert.id
                                }
                                onClick={() =>
                                  handleAcknowledge(
                                    alert
                                  )
                                }
                              >
                                {
                                  acknowledgingId
                                    === alert.id
                                    ? 'Acknowledging...'
                                    : 'Acknowledge'
                                }
                              </button>
                            )
                            : (
                              <span>
                                —
                              </span>
                            )
                        }

                      </td>
                    )
                  }

                </tr>
              )
            })}

          </tbody>

        </table>

      </div>

    </div>
  )
}
