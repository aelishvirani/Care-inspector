import {
  formatAlertType,
  formatDateTime,
} from '../../utils/formatters'


export default function AlertTable({
  alerts,
}) {
  if (alerts.length === 0) {
    return (
      <div className="empty-state">
        No alerts found.
      </div>
    )
  }


  return (
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
            <th>Resolved</th>
          </tr>
        </thead>

        <tbody>

          {alerts.map(alert => (

            <tr key={alert.id}>

              <td>
                <span
                  className={
                    alert.active
                      ? 'alert-state active'
                      : 'alert-state resolved'
                  }
                >
                  {
                    alert.active
                      ? 'Active'
                      : 'Resolved'
                  }
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
                <span className="table-device-id">
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
                  alert.resolved_at
                    ? formatDateTime(
                        alert.resolved_at
                      )
                    : '-'
                }
              </td>

            </tr>

          ))}

        </tbody>

      </table>

    </div>
  )
}
