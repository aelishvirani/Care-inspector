import {
  Link,
} from 'react-router-dom'

import StatusBadge
  from '../common/StatusBadge'

import {
  formatDateTime,
} from '../../utils/formatters'


export default function PrinterTable({
  printers,
}) {
  if (printers.length === 0) {
    return (
      <div className="empty-state">
        No printers registered.
      </div>
    )
  }


  return (
    <div className="printer-table-wrapper">

      <table className="printer-table">

        <thead>
          <tr>
            <th>Printer</th>
            <th>Status</th>
            <th>Source</th>
            <th>Print Count</th>
            <th>Temperature</th>
            <th>Last Seen</th>
            <th />
          </tr>
        </thead>

        <tbody>

          {printers.map(
            printer => (

              <tr key={printer.device_id}>

                <td>
                  <div className="printer-name">
                    Printer
                  </div>

                  <div className="printer-table-id">
                    {printer.device_id}
                  </div>
                </td>

                <td>
                  <StatusBadge
                    online={
                      printer.online
                    }
                  />
                </td>

                <td>
                  {printer.source}
                </td>

                <td>
                  {printer.print_count}
                </td>

                <td>
                  {printer.temperature_c}
                  {' °C'}
                </td>

                <td>
                  {formatDateTime(
                    printer.last_seen
                  )}
                </td>

                <td>
                  <Link
                    className="detail-link"
                    to={
                      `/printers/${encodeURIComponent(
                        printer.device_id
                      )}`
                    }
                  >
                    View
                  </Link>
                </td>

              </tr>

            )
          )}

        </tbody>

      </table>

    </div>
  )
}
