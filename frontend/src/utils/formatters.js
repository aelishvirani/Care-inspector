export function formatDateTime(value) {
  if (!value) return '-'

  return new Date(value)
    .toLocaleString()
}


export function formatChartTime(value) {
  if (!value) return ''

  return new Date(value)
    .toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
}


export function formatAlertType(value) {
  if (!value) return ''

  return value
    .replaceAll('_', ' ')
    .toUpperCase()
}
