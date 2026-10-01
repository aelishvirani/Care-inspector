import {
  useEffect,
  useState,
} from 'react'

import {
  getDashboardData,
} from '../services/dashboardService'


const REFRESH_INTERVAL = 5000


export function useDashboard() {
  const [devices, setDevices] = useState([])
  const [alerts, setAlerts] = useState([])
  const [measurements, setMeasurements] =
    useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  async function refresh() {
    try {
      const data =
        await getDashboardData()

      setDevices(data.devices)
      setAlerts(data.alerts)
      setMeasurements(
        data.measurements
      )

      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        'Backend connection unavailable'
      )

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()

    const interval = setInterval(
      refresh,
      REFRESH_INTERVAL
    )

    return () => {
      clearInterval(interval)
    }
  }, [])


  return {
    devices,
    alerts,
    measurements,
    loading,
    error,
    refresh,
  }
}
