import {
  formatAlertType,
  formatDateTime,
} from '../../utils/formatters'


export default function AlertsPanel({
  alerts,
}) {
  return (
    <section className="panel alerts-panel">

      <div className="panel-header">

        <div>
          <h2>Active Alerts</h2>

          <p>
            Current printer warnings
          </p>
        </div>

        <span className="alert-count">
          {alerts.length}
        </span>

      </div>


      <div className="alerts-list">

        {alerts.length === 0 ? (

          <div className="healthy-state">

            <div className="healthy-icon">
              ✓
            </div>

            <div>
              <strong>
                System healthy
              </strong>

              <p>
                No active alerts
              </p>
            </div>

          </div>

        ) : (

          alerts.map((alert) => (

            <div
              key={alert.id}
              className={
                `alert-item ${alert.severity}`
              }
            >

              <div className="alert-title">

                <strong>
                  {formatAlertType(
                    alert.alert_type
                  )}
                </strong>

                <span>
                  {alert.severity}
                </span>

              </div>

              <p>
                {alert.message}
              </p>

              <small>
                {formatDateTime(
                  alert.created_at
                )}
              </small>

            </div>

          ))

        )}

      </div>

    </section>
  )
}
