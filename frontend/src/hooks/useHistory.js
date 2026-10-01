import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getMeasurementHistory,
} from '../services/historyService'


const REFRESH_INTERVAL = 5000


export function useHistory(filters) {
  const [
    measurements,
    setMeasurements,
  ] = useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  const refresh = useCallback(
    async () => {
      try {
        const data =
          await getMeasurementHistory(
            filters
          )

        setMeasurements(data)
        setError(null)

      } catch (err) {
        console.error(err)

        setError(
          'Unable to load measurement history'
        )

      } finally {
        setLoading(false)
      }
    },
    [
      filters.deviceId,
      filters.fromTime,
      filters.toTime,
    ]
  )


  useEffect(() => {

    setLoading(true)

    refresh()

    const interval =
      setInterval(
        refresh,
        REFRESH_INTERVAL
      )

    return () => {
      clearInterval(interval)
    }

  }, [refresh])


  return {
    measurements,
    loading,
    error,
    refresh,
  }
}
