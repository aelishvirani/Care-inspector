import { useEffect, useState } from 'react'
import { getPrinterConnection } from '../../api/printerConnectionsApi'

export default function PrinterConnectionStatus({
  deviceId,
  refreshKey = 0,
}) {
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false

    setStatus('loading')

    getPrinterConnection(deviceId)
      .then(data => {
        if (!cancelled) {
          setStatus(
            data.configured ? 'configured' : 'not-configured'
          )
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus('error')
        }
      })

    return () => {
      cancelled = true
    }
  }, [deviceId, refreshKey])

  const labels = {
    loading: 'Checking...',
    configured: 'Configured',
    'not-configured': 'Not Configured',
    error: 'Status Unavailable',
  }

  return (
    <span className={`printer-connection-status ${status}`}>
      {labels[status]}
    </span>
  )
}
