import {
  useState,
} from 'react'

import {
  sendPrinterCommand,
} from '../../services/printerService'


function isStarted(
  status
) {
  return [
    'ready',
    'printing',
    'starting',
    'drop_adjust',
    'ink_heating',
    'service',
    'warning',
  ].includes(
    String(status || '')
      .toLowerCase()
  )
}


export default function PrinterControlButtons({
  printer,
  onChanged,
  compact = false,
}) {
  const [
    pending,
    setPending,
  ] = useState(null)

  const [
    error,
    setError,
  ] = useState('')

  const [
    commandStatus,
    setCommandStatus,
  ] = useState(null)

  const status =
    String(
      commandStatus
      || printer?.status
      || ''
    ).toLowerCase()

  const online =
    Boolean(
      printer?.online
    )

  const started =
    isStarted(
      status
    )

  const startDisabled =
    !online
    || pending !== null
    || started
    || status !== 'stopped'

  const stopDisabled =
    !online
    || pending !== null
    || status === 'stopped'
    || status === 'offline'


  async function runCommand(
    command
  ) {
    const label =
      printer.display_name
      || printer.device_id

    const confirmed =
      window.confirm(
        command === 'start'
          ? `Start ${label}?`
          : `Stop ${label}?`
      )

    if (!confirmed) {
      return
    }

    setPending(command)
    setError('')

    try {
      const result =
        await sendPrinterCommand(
          printer.device_id,
          command
        )

      if (result.status) {
        setCommandStatus(
          result.status
        )
      }

      if (onChanged) {
        await onChanged()
      }

    } catch (err) {
      console.error(err)

      setError(
        err.message
        || 'Printer command failed'
      )

    } finally {
      setPending(null)
    }
  }


  return (
    <div
      className={
        compact
          ? 'printer-control printer-control-compact'
          : 'printer-control'
      }
      onClick={
        event =>
          event.stopPropagation()
      }
    >

      <div className="printer-control-buttons">

        <button
          type="button"
          className="printer-command-button start"
          disabled={startDisabled}
          onClick={() =>
            runCommand(
              'start'
            )
          }
          title={
            !online
              ? 'Printer is offline'
              : (
                  started
                    ? 'Printer is already started'
                    : (
                        status !== 'stopped'
                          ? 'Start is available when printer is stopped'
                          : 'Start printer'
                      )
                )
          }
        >
          {
            pending === 'start'
              ? 'Starting...'
              : '▶ Start'
          }
        </button>


        <button
          type="button"
          className="printer-command-button stop"
          disabled={stopDisabled}
          onClick={() =>
            runCommand(
              'stop'
            )
          }
          title={
            !online
              ? 'Printer is offline'
              : (
                  status === 'stopped'
                    ? 'Printer is already stopped'
                    : 'Stop printer'
                )
          }
        >
          {
            pending === 'stop'
              ? 'Stopping...'
              : '■ Stop'
          }
        </button>

      </div>


      {
        error
        && (
          <div className="printer-control-error">
            {error}
          </div>
        )
      }

    </div>
  )
}
