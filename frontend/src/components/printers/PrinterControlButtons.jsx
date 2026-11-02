import {
  useEffect,
  useState,
} from 'react'

import {
  sendPrinterCommand,
} from '../../services/printerService'

import {
  useAuth,
} from '../../auth/AuthContext'

import { getPrinterCommands, testPrinterCommand } from '../../api/printerCommandsApi'


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
  const {
    user,
  } = useAuth()

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

  const [customCommands, setCustomCommands] = useState([])
  const [selectedCustomCommand, setSelectedCustomCommand] = useState('')
  const [testResult, setTestResult] = useState('')

  useEffect(() => {
    if (!printer?.device_id || !['ADMIN', 'TECHNICIAN'].includes(user?.role)) {
      setCustomCommands([])
      return
    }
    let active = true
    setSelectedCustomCommand('')
    setTestResult('')
    getPrinterCommands(printer.device_id)
      .then(commands => { if (active) setCustomCommands(commands) })
      .catch(() => { if (active) setCustomCommands([]) })
    return () => { active = false }
  }, [printer?.device_id, user?.role])

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

  const canControl =
    user?.role === 'TECHNICIAN'
    || user?.role === 'ADMIN'

  if (!canControl) {
    return null
  }


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


  async function runTestCommand() {
    const command = customCommands.find(
      item => String(item.id) === selectedCustomCommand
    )
    if (!command || pending !== null || !online) return

    const confirmed = window.confirm(
      'Test "' + command.name + '" on ' +
      (printer.display_name || printer.device_id) +
      '? This is a DRY RUN. No command bytes will be sent.'
    )
    if (!confirmed) return

    setPending('test')
    setError('')
    setTestResult('')
    try {
      const result = await testPrinterCommand(printer.device_id, command.id)
      setTestResult(result.message || 'Dry-run completed without transmission.')
    } catch (err) {
      setError(err.message || 'Dry-run failed')
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

        <select
          aria-label={'Custom commands for ' + (printer?.display_name || printer?.device_id)}
          value={selectedCustomCommand}
          onChange={event => setSelectedCustomCommand(event.target.value)}
          onClick={event => event.stopPropagation()}
          style={{ maxWidth: compact ? 140 : 220 }}
          title="Select a command for a safe dry-run test"
        >
          <option value="">Commands...</option>
          {customCommands.map(command => (
            <option key={command.id} value={String(command.id)}>
              {command.name}
            </option>
          ))}
        </select>

        <button
          type="button"
          className="printer-command-button"
          disabled={!online || !selectedCustomCommand || pending !== null}
          onClick={runTestCommand}
          title="Audit-only test. No bytes are sent to any printer."
        >
          {pending === 'test' ? 'Testing...' : 'Test Execute'}
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

      {testResult && (
        <div role="status" className="printer-control-success">
          {testResult}
        </div>
      )}

    </div>
  )
}
