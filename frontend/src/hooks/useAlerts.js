import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getAlerts,
} from '../services/alertService'


export function useAlerts(filters) {
  const [alerts, setAlerts] =
    useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  const refresh = useCallback(
    async () => {
      try {
        const data =
          await getAlerts(filters)

        setAlerts(data)
        setError(null)

      } catch (err) {
        console.error(err)

        setError(
          'Unable to load alerts'
        )

      } finally {
        setLoading(false)
      }
    },
    [
      filters.status,
      filters.severity,
      filters.deviceId,
    ]
  )


  useEffect(() => {
    setLoading(true)
    refresh()
  }, [refresh])


  return {
    alerts,
    loading,
    error,
    refresh,
  }
}
