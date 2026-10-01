import { apiGet } from '../api/client'

export function getDevices() {
  return apiGet('/devices')
}

export function getActiveAlerts() {
  return apiGet('/alerts/active')
}

export function getMeasurements(limit = 100) {
  return apiGet(
    `/measurements/latest?limit=${limit}`
  )
}

export async function getDashboardData() {
  const [
    devices,
    alerts,
    measurements,
  ] = await Promise.all([
    getDevices(),
    getActiveAlerts(),
    getMeasurements(),
  ])

  return {
    devices,
    alerts,
    measurements,
  }
}
