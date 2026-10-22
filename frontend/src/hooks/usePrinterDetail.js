import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getPrinter,
  getPrinterAlerts,
  getPrinterMeasurements,
} from '../services/printerService'


const REFRESH_INTERVAL = 5000


export function usePrinterDetail(
  deviceId
) {
  const [printer, setPrinter] =
    useState(null)

  const [
    measurements,
    setMeasurements,
  ] = useState([])

  const [alerts, setAlerts] =
    useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  const refresh = useCallback(
    async () => {
      try {
        const [
          printerData,
          measurementData,
          alertData,
        ] = await Promise.all([
          getPrinter(deviceId),

          getPrinterMeasurements(
            deviceId,
            100
          ),

          getPrinterAlerts(
            deviceId
          ),
        ])

        setPrinter(printerData)

        setMeasurements(
          measurementData
        )

        setAlerts(alertData)

        setError(null)

      } catch (err) {
        console.error(err)

        setError(
          'Unable to load printer details'
        )

      } finally {
        setLoading(false)
      }
    },
    [deviceId]
  )


  useEffect(() => {
    refresh()

    const interval = setInterval(
      refresh,
      REFRESH_INTERVAL
    )

    return () =>
      clearInterval(interval)

  }, [refresh])


  return {
    printer,
    measurements,
    alerts,
    loading,
    error,
    refresh,
  }
}
