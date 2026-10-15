const STATUS_FILTERS = [
  {
    value: 'all',
    label: 'All',
  },
  {
    value: 'online',
    label: 'Online',
  },
  {
    value: 'offline',
    label: 'Offline',
  },
  {
    value: 'warning',
    label: 'Warning',
  },
  {
    value: 'fault',
    label: 'Fault',
  },
  {
    value: 'stopped',
    label: 'Stopped',
  },
]


export default function PrinterStatusFilter({
  value,
  onChange,
}) {
  return (
    <div className="printer-status-filters">

      {
        STATUS_FILTERS.map(
          filter => (
            <button
              key={filter.value}
              type="button"
              className={
                [
                  'printer-status-filter',
                  filter.value,
                  value === filter.value
                    ? 'selected'
                    : '',
                ]
                  .filter(Boolean)
                  .join(' ')
              }
              onClick={() =>
                onChange(
                  filter.value
                )
              }
            >
              {filter.label}
            </button>
          )
        )
      }

    </div>
  )
}
