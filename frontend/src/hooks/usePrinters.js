import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  getPrinters,
} from '../services/printerService'


const REFRESH_INTERVAL = 5000


export function usePrinters() {
  const [printers, setPrinters] =
    useState([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState(null)


  const refresh = useCallback(
    async () => {
      try {
        const data =
          await getPrinters()

        setPrinters(data)
        setError(null)

      } catch (err) {
        console.error(err)

        setError(
          'Unable to load printers'
        )

      } finally {
        setLoading(false)
      }
    },
    []
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
    printers,
    loading,
    error,
    refresh,
  }
}
