import { apiGet } from '../api/client'


export function getAlerts({
  status = '',
  severity = '',
  deviceId = '',
  limit = 200,
} = {}) {
  const params =
    new URLSearchParams()

  params.set('limit', limit)

  if (status) {
    params.set('status', status)
  }

  if (severity) {
    params.set('severity', severity)
  }

  if (deviceId) {
    params.set(
      'device_id',
      deviceId
    )
  }

  return apiGet(
    `/alerts?${params.toString()}`
  )
}
