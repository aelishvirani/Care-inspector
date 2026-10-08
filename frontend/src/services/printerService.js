import {
  apiGet,
} from '../api/client'


export function getPrinters() {
  return apiGet(
    '/secure/devices'
  )
}


export function getPrinter(
  deviceId
) {
  return apiGet(
    `/secure/devices/${encodeURIComponent(
      deviceId
    )}`
  )
}


export function getPrinterMeasurements(
  deviceId,
  limit = 100
) {
  const params =
    new URLSearchParams()

  params.set(
    'device_id',
    deviceId
  )

  params.set(
    'limit',
    String(limit)
  )

  return apiGet(
    `/secure/measurements?${params.toString()}`
  )
}


export function getPrinterAlerts(
  deviceId,
  limit = 100
) {
  const params =
    new URLSearchParams()

  params.set(
    'device_id',
    deviceId
  )

  params.set(
    'limit',
    String(limit)
  )

  return apiGet(
    `/secure/alerts?${params.toString()}`
  )
}
