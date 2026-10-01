import {
  Link,
  useParams,
} from 'react-router-dom'

import PrinterCard
  from '../components/printers/PrinterCard'

import MeasurementChart
  from '../components/charts/MeasurementChart'

import {
  usePrinterDetail,
} from '../hooks/usePrinterDetail'

import {
  formatDateTime,
} from '../utils/formatters'


export default function PrinterDetailPage() {
  const {
    deviceId,
  } = useParams()


  const {
    printer,
    measurements,
    alerts,
    loading,
    error,
  } = usePrinterDetail(
    deviceId
  )


  if (loading) {
    return (
      <div className="loading-panel">
        Loading printer...
      </div>
    )
  }


  if (error) {
    return (
      <div className="error-banner">
        {error}
      </div>
    )
  }


  if (!printer) {
    return (
      <div className="empty-state">
        Printer not found.
      </div>
    )
  }


  return (
    <div className="page">

      <div className="detail-page-header">

        <div>

          <Link
            to="/printers"
            className="back-link"
          >
            ← Printers
          </Link>

          <h1>
            Printer Detail
          </h1>

          <p>
            {printer.device_id}
          </p>

        </div>

      </div>


      <PrinterCard
        device={printer}
      />


      <div className="printer-detail-grid">

        <MeasurementChart
          deviceId={
            printer.device_id
          }
          measurements={
            measurements
          }
        />


        <section className="panel">

          <div className="panel-header">

            <div>
              <h2>
                Recent Alerts
              </h2>

              <p>
                Printer-specific
                alert history
              </p>
            </div>

          </div>


          <div className="detail-alert-list">

            {alerts.length === 0 ? (

              <div className="healthy-state">

                <div className="healthy-icon">
                  ✓
                </div>

                <div>
                  <strong>
                    No alert history
                  </strong>

                  <p>
                    No alerts recorded
                    for this printer.
                  </p>
                </div>

              </div>

            ) : (

              alerts
                .slice(0, 10)
                .map(alert => (

                  <div
                    key={alert.id}
                    className={
                      `detail-alert ${
                        alert.severity
                      }`
                    }
                  >

                    <div>

                      <strong>
                        {
                          alert.alert_type
                            .replaceAll(
                              '_',
                              ' '
                            )
                            .toUpperCase()
                        }
                      </strong>

                      <p>
                        {alert.message}
                      </p>

                    </div>


                    <div className="detail-alert-meta">

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

                      <small>
                        {formatDateTime(
                          alert.created_at
                        )}
                      </small>

                    </div>

                  </div>

                ))

            )}

          </div>

        </section>

      </div>

    </div>
  )
}
