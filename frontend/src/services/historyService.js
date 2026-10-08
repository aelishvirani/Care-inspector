import {
  apiGet,
} from '../api/client'


export function getMeasurementHistory({
  deviceId = '',
  fromTime = '',
  toTime = '',
  limit = 1000,
} = {}) {
  const params =
    new URLSearchParams()

  params.set(
    'limit',
    String(limit)
  )

  if (deviceId) {
    params.set(
      'device_id',
      deviceId
    )
  }

  if (fromTime) {
    params.set(
      'from_time',
      fromTime
    )
  }

  if (toTime) {
    params.set(
      'to_time',
      toTime
    )
  }

  return apiGet(
    `/secure/measurements?${params.toString()}`
  )
}
