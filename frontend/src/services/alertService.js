import {
  apiGet,
  apiPost,
} from '../api/client'


export function getAlerts({
  status = '',
  severity = '',
  deviceId = '',
  limit = 200,
} = {}) {
  const params =
    new URLSearchParams()

  params.set(
    'limit',
    String(limit)
  )

  if (status) {
    params.set(
      'status',
      status
    )
  }

  if (severity) {
    params.set(
      'severity',
      severity
    )
  }

  if (deviceId) {
    params.set(
      'device_id',
      deviceId
    )
  }

  return apiGet(
    `/secure/alerts?${params.toString()}`
  )
}


export function acknowledgeAlert(
  alertId
) {
  return apiPost(
    `/secure/alerts/${alertId}/acknowledge`,
    {}
  )
}
