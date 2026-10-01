import MetricCard
  from '../common/MetricCard'

import StatusBadge
  from '../common/StatusBadge'

import {
  formatDateTime,
} from '../../utils/formatters'


function formatNativeLevel(
  label,
  raw
) {
  if (label) {
    return label
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char =>
        char.toUpperCase()
      )
  }

  if (
    raw !== null
    && raw !== undefined
  ) {
    return `Level ${raw}`
  }

  return '—'
}


export default function PrinterCard({
  device,
}) {
  const isHitachi =
    device.source === 'hitachi_modbus'

  const inkLevel = isHitachi
    ? formatNativeLevel(
        device.ink_remaining_label,
        device.ink_remaining_raw
      )
    : (
        device.ink_level_percent
          !== null
        && device.ink_level_percent
          !== undefined
          ? `${device.ink_level_percent}%`
          : '—'
      )

  const makeupLevel = isHitachi
    ? formatNativeLevel(
        device.makeup_remaining_label,
        device.makeup_remaining_raw
      )
    : (
        device.makeup_level_percent
          !== null
        && device.makeup_level_percent
          !== undefined
          ? `${device.makeup_level_percent}%`
          : '—'
      )


  return (
    <section className="printer-card">

      <div className="printer-header">

        <div>

          <h2>
            {
              device.model_name
                ? `Hitachi ${device.model_name}`
                : 'Printer'
            }
          </h2>

          <span className="device-id">
            {device.device_id}
          </span>

          {
            device.serial_number
            && (
              <div className="device-id">
                Serial: {
                  device.serial_number
                }
              </div>
            )
          }

        </div>

        <StatusBadge
          online={device.online}
        />

      </div>


      <div className="printer-meta">

        <div>
          <span>Status</span>

          <strong>
            {
              device.status
                ?.replaceAll('_', ' ')
                .toUpperCase()
            }
          </strong>
        </div>


        <div>
          <span>Source</span>

          <strong>
            {device.source}
          </strong>
        </div>


        <div>
          <span>Ink</span>

          <strong>
            {device.ink_name ?? '—'}
          </strong>
        </div>


        <div>
          <span>Last Seen</span>

          <strong>
            {formatDateTime(
              device.last_seen
            )}
          </strong>
        </div>

      </div>


      <div className="metrics-grid">

        <MetricCard
          label="Print Count"
          value={
            device.print_count ?? '—'
          }
        />

        <MetricCard
          label="Operating Time"
          value={
            device
              .ink_operating_time_hours
              ?? '—'
          }
          unit={
            device
              .ink_operating_time_hours
              !== null
            && device
              .ink_operating_time_hours
              !== undefined
              ? ' h'
              : ''
          }
        />

        <MetricCard
          label="Total Operating Time"
          value={
            device
              .cumulative_operation_time_hours
              ?? '—'
          }
          unit={
            device
              .cumulative_operation_time_hours
              !== null
            && device
              .cumulative_operation_time_hours
              !== undefined
              ? ' h'
              : ''
          }
        />

        <MetricCard
          label="Ambient Temperature"
          value={
            device.temperature_c ?? '—'
          }
          unit={
            device.temperature_c
              !== null
            && device.temperature_c
              !== undefined
              ? ' °C'
              : ''
          }
        />

        <MetricCard
          label="Ink Pressure"
          value={
            device.pressure_mpa ?? '—'
          }
          unit={
            device.pressure_mpa
              !== null
            && device.pressure_mpa
              !== undefined
              ? ' MPa'
              : ''
          }
        />

        <MetricCard
          label="Ink Remaining"
          value={inkLevel}
        />

        <MetricCard
          label="Makeup Remaining"
          value={makeupLevel}
        />

      </div>

    </section>
  )
}
