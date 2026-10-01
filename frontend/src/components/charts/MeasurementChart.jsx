import { useMemo } from 'react'

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  formatChartTime,
} from '../../utils/formatters'


function SingleMeasurementChart({
  title,
  subtitle,
  data,
  dataKey,
  unit,
}) {
  const availableData = data.filter(
    item =>
      item[dataKey] !== null
      && item[dataKey] !== undefined
  )

  return (
    <section className="panel chart-panel">

      <div className="panel-header">

        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>

      </div>


      <div className="chart-wrapper">

        {availableData.length === 0 ? (

          <div className="empty-state">
            No measurement data
          </div>

        ) : (

          <ResponsiveContainer
            width="100%"
            height={280}
          >
            <LineChart
              data={availableData}
            >

              <CartesianGrid
                strokeDasharray="3 3"
              />

              <XAxis
                dataKey="time"
                minTickGap={30}
              />

              <YAxis
                domain={['auto', 'auto']}
              />

              <Tooltip
                formatter={
                  value =>
                    `${value}${unit}`
                }
              />

              <Line
                type="monotone"
                dataKey={dataKey}
                dot={false}
                strokeWidth={2}
                connectNulls={false}
              />

            </LineChart>
          </ResponsiveContainer>

        )}

      </div>

    </section>
  )
}


export default function MeasurementChart({
  deviceId,
  measurements,
}) {
  const chartData = useMemo(
    () =>
      measurements
        .filter(
          item =>
            item.device_id === deviceId
        )
        .slice()
        .reverse()
        .map(item => ({
          ...item,
          time: formatChartTime(
            item.timestamp
          ),
        })),
    [
      measurements,
      deviceId,
    ]
  )


  return (
    <div className="history-grid">

      <SingleMeasurementChart
        title="Ambient Temperature"
        subtitle="Printer-reported ambient temperature"
        data={chartData}
        dataKey="temperature_c"
        unit=" °C"
      />

      <SingleMeasurementChart
        title="Ink Pressure"
        subtitle="Printer-reported ink pressure"
        data={chartData}
        dataKey="pressure_mpa"
        unit=" MPa"
      />

    </div>
  )
}
