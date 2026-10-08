import {
  useNavigate,
} from 'react-router-dom'

import StatusBadge
  from '../common/StatusBadge'

import {
  formatDateTime,
} from '../../utils/formatters'


export default function PrinterTable({
  printers,
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
            <th>Printer</th>
            <th>Model</th>
            <th>Serial</th>
            <th>Status</th>
            <th>Location</th>
            <th>Print Count</th>
            <th>Temperature</th>
            <th>Last Seen</th>
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
                  <div className="printer-name">
                    {
                      printer.display_name
                      || 'Printer'
                    }
                  </div>

                  <div className="printer-table-id">
                    {printer.device_id}
                  </div>
                </td>


                <td>
                  {
                    printer.model_name
                    || '—'
                  }
                </td>


                <td>
                  {
                    printer.serial_number
                    || '—'
                  }
                </td>


                <td>
                  <StatusBadge
                    online={
                      printer.online
                    }
                  />
                </td>


                <td>
                  {
                    printer.location
                    || '—'
                  }
                </td>


                <td>
                  {
                    printer.print_count
                    ?? '—'
                  }
                </td>


                <td>
                  {
                    printer.temperature_c
                    ?? '—'
                  }
                  {
                    printer.temperature_c
                    !== null
                    && printer.temperature_c
                      !== undefined
                    && ' °C'
                  }
                </td>


                <td>
                  {
                    formatDateTime(
                      printer.last_seen
                    )
                  }
                </td>

              </tr>

            )
          )}

        </tbody>

      </table>

    </div>
  )
}
