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


export default function HistoryLineChart({
  title,
  subtitle,
  data,
  dataKey,
  unit = '',
}) {
  const chartData = useMemo(
    () =>
      data
        .filter(
          item =>
            item[dataKey] !== null
            && item[dataKey] !== undefined
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
      data,
      dataKey,
    ]
  )


  return (
    <section className="panel history-chart-panel">

      <div className="panel-header">

        <div>
          <h2>
            {title}
          </h2>

          <p>
            {subtitle}
          </p>
        </div>

      </div>


      <div className="history-chart-wrapper">

        {chartData.length === 0 ? (

          <div className="empty-state">
            No data available.
          </div>

        ) : (

          <ResponsiveContainer
            width="100%"
            height={260}
          >

            <LineChart
              data={chartData}
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
