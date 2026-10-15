export function printerStatus(
  printer
) {
  if (!printer) {
    return {
      label: 'Unknown',
      className: 'offline',
    }
  }

  if (!printer.online) {
    return {
      label: 'Offline',
      className: 'offline',
    }
  }

  if (
    printer.status === 'fault'
  ) {
    return {
      label: 'Fault',
      className: 'fault',
    }
  }

  if (
    printer.status === 'warning'
  ) {
    return {
      label: 'Warning',
      className: 'warning',
    }
  }

  if (
    printer.status === 'stopped'
  ) {
    return {
      label: 'Stopped',
      className: 'stopped',
    }
  }

  return {
    label:
      printer.status
        ?.replaceAll('_', ' ')
        ?.toUpperCase()
      || 'Online',

    className: 'online',
  }
}


export function relativeLastSeen(
  value
) {
  if (!value) {
    return 'never seen'
  }

  const timestamp =
    new Date(value)

  const seconds = Math.max(
    0,
    Math.floor(
      (
        Date.now()
        - timestamp.getTime()
      ) / 1000
    )
  )

  if (seconds < 60) {
    return `${seconds}s ago`
  }

  const minutes =
    Math.floor(
      seconds / 60
    )

  if (minutes < 60) {
    return `${minutes}m ago`
  }

  const hours =
    Math.floor(
      minutes / 60
    )

  if (hours < 24) {
    return `${hours}h ago`
  }

  const days =
    Math.floor(
      hours / 24
    )

  return `${days}d ago`
}


export function offlineReason(
  printer
) {
  if (
    !printer
    || printer.online
  ) {
    return ''
  }

  return (
    `Last measurement `
    + relativeLastSeen(
        printer.last_seen
      )
  )
}
