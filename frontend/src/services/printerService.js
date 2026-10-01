import { apiGet } from '../api/client'


export function getPrinters() {
  return apiGet('/devices')
}


export async function getPrinter(deviceId) {
  const printers = await getPrinters()

  return (
    printers.find(
      printer =>
        printer.device_id === deviceId
    ) || null
  )
}


export async function getPrinterMeasurements(
  deviceId,
  limit = 100
) {
  return apiGet(
    `/measurements?device_id=${encodeURIComponent(
      deviceId
    )}&limit=${limit}`
  )
}


export async function getPrinterAlerts(
  deviceId
) {
  const alerts = await apiGet('/alerts')

  return alerts.filter(
    alert =>
      alert.device_id === deviceId
  )
}
