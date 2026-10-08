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
    useState(false)

  const [error, setError] =
    useState(null)


  const refresh = useCallback(
    async () => {

      /*
       * History is always printer-specific.
       * Never request mixed measurements
       * without a device_id.
       */
      if (!filters.deviceId) {
        setMeasurements([])
        setLoading(false)
        setError(null)
        return
      }

      try {
        setLoading(true)

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

    if (!filters.deviceId) {
      setMeasurements([])
      setLoading(false)
      return
    }

    refresh()

    const interval =
      setInterval(
        refresh,
        REFRESH_INTERVAL
      )

    return () => {
      clearInterval(interval)
    }

  }, [refresh, filters.deviceId])


  return {
    measurements,
    loading,
    error,
    refresh,
  }
}
