import {
  useNavigate,
} from 'react-router-dom'

import StatusBadge
  from '../common/StatusBadge'

import PrinterControlButtons
  from './PrinterControlButtons'

import {
  formatDateTime,
} from '../../utils/formatters'


export default function PrinterTable({
  printers,
  onPrinterChanged,
}) {
  const navigate =
    useNavigate()


  if (printers.length === 0) {
    return (
      <div className="empty-state">
        No printers found.
      </div>
    )
  }


  return (
    <div className="printer-table-wrapper">

      <table className="printer-table">

        <thead>
          <tr>
            <th>Printer ID</th>
            <th>Customer Name</th>
            <th>Model</th>
            <th>Status</th>
            <th>Source</th>
            <th>Last Seen</th>
            <th>Control</th>
          </tr>
        </thead>


        <tbody>

          {printers.map(
            printer => (

              <tr
                key={
                  printer.device_id
                }
                onClick={() =>
                  navigate(
                    `/printers/${encodeURIComponent(
                      printer.device_id
                    )}`
                  )
                }
                style={{
                  cursor: 'pointer',
                }}
              >

                <td>
                  <div className="printer-table-id">
                    {
                      printer.device_id
                    }
                  </div>
                </td>


                <td>
                  {
                    printer.customer_name
                    || '—'
                  }
                </td>


                <td>
                  {
                    printer.model_name
                    || '—'
                  }
                </td>


                <td>
                  <StatusBadge
                    printer={printer}
                  />
                </td>


                <td>
                  {
                    printer.source
                    || '—'
                  }
                </td>


                <td>
                  {
                    formatDateTime(
                      printer.last_seen
                    )
                  }
                </td>


                <td>
                  <PrinterControlButtons
                    printer={printer}
                    compact
                    onChanged={
                      onPrinterChanged
                    }
                  />
                </td>

              </tr>

            )
          )}

        </tbody>

      </table>

    </div>
  )
}
