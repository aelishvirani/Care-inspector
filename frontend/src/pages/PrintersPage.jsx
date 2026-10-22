import {
  useMemo,
  useState,
} from 'react'

import PrinterTable
  from '../components/printers/PrinterTable'

import {
  usePrinters,
} from '../hooks/usePrinters'

import PrinterStatusFilter
  from '../components/filters/PrinterStatusFilter'


export default function PrintersPage() {
  const {
    printers,
    loading,
    error,
    refresh,
  } = usePrinters()

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    statusFilter,
    setStatusFilter,
  ] = useState('all')


  const filteredPrinters =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        return printers.filter(
          printer => {

            const matchesSearch =
              !term
              || [
                printer.display_name,
                printer.device_id,
                printer.customer_name,
                printer.model_name,
                printer.serial_number,
                printer.location,
                printer.status,
                printer.ink_name,
              ]
                .filter(Boolean)
                .some(
                  value =>
                    String(value)
                      .toLowerCase()
                      .includes(term)
                )

            const matchesStatus =
              statusFilter === 'all'
              || (
                statusFilter === 'online'
                && printer.online
              )
              || (
                statusFilter === 'offline'
                && !printer.online
              )
              || (
                statusFilter
                  === printer.status
              )

            return (
              matchesSearch
              && matchesStatus
            )
          }
        )
      },
      [
        printers,
        search,
        statusFilter,
      ]
    )


  if (loading) {
    return (
      <div className="loading-panel">
        Loading printers...
      </div>
    )
  }


  const onlineCount =
    printers.filter(
      printer =>
        printer.online
    ).length


  return (
    <div className="page">

      <div className="page-heading">

        <div>
          <h1>
            Printer Fleet
          </h1>

          <p>
            All monitored industrial
            printers
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
          <span>
            Total Printers
          </span>

          <strong>
            {printers.length}
          </strong>
        </div>


        <div className="summary-card">
          <span>
            Online
          </span>

          <strong>
            {onlineCount}
          </strong>
        </div>


        <div className="summary-card">
          <span>
            Offline
          </span>

          <strong>
            {
              printers.length
              - onlineCount
            }
          </strong>
        </div>

      </div>


      <section className="panel">

        <div className="printer-filter-toolbar">

          <div className="printer-filter-top-row">

            <input
              className="role-search"
              type="search"
              placeholder={
                'Search printer, model, serial, location...'
              }
              value={search}
              onChange={
                event =>
                  setSearch(
                    event.target.value
                  )
              }
            />


            {
              (
                search
                || statusFilter !== 'all'
              )
              && (
                <button
                  type="button"
                  className="clear-filter-button"
                  onClick={() => {
                    setSearch('')
                    setStatusFilter('all')
                  }}
                >
                  Clear
                </button>
              )
            }

          </div>


          <PrinterStatusFilter
            value={statusFilter}
            onChange={setStatusFilter}
          />

        </div>



        <div className="panel-header">

          <div>
            <h2>
              Printers
            </h2>

            <p>
              {
                filteredPrinters.length
              }
              {' '}
              matching printers
            </p>
          </div>

        </div>


        <PrinterTable
          printers={
            filteredPrinters
          }
          onPrinterChanged={
            refresh
          }
        />

      </section>

    </div>
  )
}
