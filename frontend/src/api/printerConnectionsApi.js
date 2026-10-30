import {
  apiGet,
  apiPut,
} from './client'

function connectionPath(deviceId) {
  return `/secure/management/devices/${encodeURIComponent(deviceId)}/connection`
}

export function getPrinterConnection(deviceId) {
  return apiGet(connectionPath(deviceId))
}

export function savePrinterConnection(deviceId, settings) {
  return apiPut(connectionPath(deviceId), settings)
}
