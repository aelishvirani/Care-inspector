import PrinterTable
  from '../components/printers/PrinterTable'

import {
  usePrinters,
} from '../hooks/usePrinters'


export default function PrintersPage() {
  const {
    printers,
    loading,
    error,
  } = usePrinters()


  if (loading) {
    return (
      <div className="loading-panel">
        Loading printers...
      </div>
    )
  }


  const onlineCount =
    printers.filter(
      printer => printer.online
    ).length


  return (
    <div className="page">

      <div className="page-heading">

        <div>
          <h1>Printers</h1>

          <p>
            Connected industrial printer
            devices
          </p>
        </div>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <div className="printer-summary-grid">

        <div className="summary-card">
          <span>Total Printers</span>
          <strong>
            {printers.length}
          </strong>
        </div>

        <div className="summary-card">
          <span>Online</span>
          <strong>
            {onlineCount}
          </strong>
        </div>

        <div className="summary-card">
          <span>Offline</span>
          <strong>
            {
              printers.length -
              onlineCount
            }
          </strong>
        </div>

      </div>


      <section className="panel">

        <div className="panel-header">

          <div>
            <h2>
              Registered Printers
            </h2>

            <p>
              Current printer
              connectivity and state
            </p>
          </div>

        </div>

        <PrinterTable
          printers={printers}
        />

      </section>

    </div>
  )
}
