import PrinterCard
  from '../components/printers/PrinterCard'

import AlertsPanel
  from '../components/alerts/AlertsPanel'

import MeasurementChart
  from '../components/charts/MeasurementChart'

import {
  useDashboard,
} from '../hooks/useDashboard'


export default function OverviewPage() {

  const {
    devices,
    alerts,
    measurements,
    loading,
    error,
  } = useDashboard()


  if (loading) {
    return (
      <div className="loading-screen">
        Loading Care-Inspector...
      </div>
    )
  }


  const selectedDevice =
    devices.length > 0
      ? devices[0]
      : null


  return (
    <div>

      <main className="dashboard">

        <div className="page-heading">

          <div>
            <h1>
              Printer Overview
            </h1>

            <p>
              Live industrial printer
              monitoring
            </p>
          </div>

          <span>
            Refresh every 5 seconds
          </span>

        </div>


        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}


        {devices.length === 0 ? (

          <div className="empty-state">
            No printers connected
          </div>

        ) : (

          devices.map(device => (

            <PrinterCard
              key={device.device_id}
              device={device}
            />

          ))

        )}


        {selectedDevice && (

          <div className="dashboard-grid">

            <MeasurementChart
              deviceId={
                selectedDevice.device_id
              }
              measurements={
                measurements
              }
            />

            <AlertsPanel
              alerts={alerts}
            />

          </div>

        )}

      </main>

    </div>
  )
}
