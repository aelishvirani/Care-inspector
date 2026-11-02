import { apiGet, apiPost } from './client'

const pathFor = deviceId =>
  `/secure/management/devices/${encodeURIComponent(deviceId)}/commands`

export const getPrinterCommands = deviceId => apiGet(pathFor(deviceId))

export const addPrinterCommand = (deviceId, payload) =>
  apiPost(pathFor(deviceId), payload)

export async function deletePrinterCommand(deviceId, commandId) {
  const token = localStorage.getItem('care_inspector_token')
  const response = await fetch(
    `/api${pathFor(deviceId)}/${encodeURIComponent(commandId)}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${token || ''}` } }
  )
  if (!response.ok) {
    let detail = 'Unable to delete command'
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch { /* Response did not include JSON. */ }
    throw new Error(detail)
  }
  return response.json()
}
