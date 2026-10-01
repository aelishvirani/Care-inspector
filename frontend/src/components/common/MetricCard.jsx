export default function MetricCard({
  label,
  value,
  unit = '',
}) {
  return (
    <div className="metric-card">

      <span className="metric-label">
        {label}
      </span>

      <div className="metric-value">
        {value ?? '-'}

        {value !== null &&
          value !== undefined &&
          unit && (
            <span className="metric-unit">
              {unit}
            </span>
          )}

      </div>

    </div>
  )
}
