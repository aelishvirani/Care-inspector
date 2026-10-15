import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  apiGet,
  apiPut,
} from '../api/client'

import {
  usePrinters,
} from '../hooks/usePrinters'

import '../styles/printer-configuration.css'


function printerLabel(printer) {
  const name =
    printer.display_name
    || printer.device_id

  const serial =
    printer.serial_number
      ? `SN ${printer.serial_number}`
      : 'No serial number'

  return `${name} · ${serial}`
}


export default function ConfigurationPage() {
  const {
    printers,
    loading: printersLoading,
    error: printersError,
  } = usePrinters()

  const [
    selectedDeviceId,
    setSelectedDeviceId,
  ] = useState('')

  const [
    configuration,
    setConfiguration,
  ] = useState(null)

  const [
    loading,
    setLoading,
  ] = useState(false)

  const [
    saving,
    setSaving,
  ] = useState(false)

  const [
    error,
    setError,
  ] = useState('')

  const [
    saved,
    setSaved,
  ] = useState(false)


  useEffect(() => {
    if (
      !selectedDeviceId
      && printers.length > 0
    ) {
      setSelectedDeviceId(
        printers[0].device_id
      )
    }
  }, [
    printers,
    selectedDeviceId,
  ])


  useEffect(() => {
    if (!selectedDeviceId) {
      return
    }

    async function loadConfiguration() {
      try {
        setLoading(true)
        setError('')
        setSaved(false)

        const data =
          await apiGet(
            `/secure/devices/${encodeURIComponent(
              selectedDeviceId
            )}/configuration`
          )

        setConfiguration(data)

      } catch (err) {
        console.error(err)

        setError(
          err.message
          || 'Unable to load printer configuration'
        )

      } finally {
        setLoading(false)
      }
    }

    loadConfiguration()
  }, [selectedDeviceId])


  const selectedPrinter =
    useMemo(
      () =>
        printers.find(
          printer =>
            printer.device_id
            === selectedDeviceId
        ) || null,
      [
        printers,
        selectedDeviceId,
      ]
    )


  function updateField(
    field,
    value
  ) {
    setSaved(false)

    setConfiguration(
      current => ({
        ...current,
        [field]: value,
      })
    )
  }


  async function saveConfiguration() {
    if (
      !selectedDeviceId
      || !configuration
    ) {
      return
    }

    try {
      setSaving(true)
      setError('')
      setSaved(false)

      const payload = {
        collector_interval_seconds:
          Number(
            configuration
              .collector_interval_seconds
          ),

        offline_timeout_seconds:
          Number(
            configuration
              .offline_timeout_seconds
          ),

        temperature_high:
          Number(
            configuration
              .temperature_high
          ),

        pressure_low:
          Number(
            configuration
              .pressure_low
          ),

        pressure_high:
          Number(
            configuration
              .pressure_high
          ),

        ink_low:
          Number(
            configuration.ink_low
          ),

        makeup_low:
          Number(
            configuration.makeup_low
          ),
      }

      const data =
        await apiPut(
          `/secure/devices/${encodeURIComponent(
            selectedDeviceId
          )}/configuration`,
          payload
        )

      setConfiguration(data)
      setSaved(true)

    } catch (err) {
      console.error(err)

      setError(
        err.message
        || 'Unable to save configuration'
      )

    } finally {
      setSaving(false)
    }
  }


  if (printersLoading) {
    return (
      <div className="loading-panel">
        Loading printers...
      </div>
    )
  }


  return (
    <div className="page printer-config-page">

      <div className="page-heading">

        <div>
          <h1>
            Printer Configuration
          </h1>

          <p>
            Individual monitoring and
            alert settings for each printer
          </p>
        </div>

      </div>


      {(error || printersError) && (
        <div className="error-banner">
          {error || printersError}
        </div>
      )}


      {saved && (
        <div className="success-banner">
          Configuration saved for{' '}
          <strong>
            {
              selectedPrinter
                ?.display_name
              || selectedDeviceId
            }
          </strong>.
        </div>
      )}


      <section className="printer-selector-panel">

        <div className="printer-selector-heading">

          <div>
            <span className="config-eyebrow">
              SELECT PRINTER
            </span>

            <h2>
              Printer configuration
            </h2>

            <p>
              Select a printer to view
              or change its individual settings.
            </p>
          </div>

        </div>


        <div className="printer-selector-row">

          <div className="printer-select-control">

            <label>
              Printer
            </label>

            <select
              value={selectedDeviceId}
              onChange={
                event =>
                  setSelectedDeviceId(
                    event.target.value
                  )
              }
            >
              {
                printers.map(
                  printer => (
                    <option
                      key={
                        printer.device_id
                      }
                      value={
                        printer.device_id
                      }
                    >
                      {
                        printerLabel(
                          printer
                        )
                      }
                    </option>
                  )
                )
              }
            </select>

          </div>


          {
            selectedPrinter
            && (
              <div className="selected-printer-summary">

                <div>
                  <span>
                    Printer name
                  </span>

                  <strong>
                    {
                      selectedPrinter
                        .display_name
                      || selectedPrinter
                        .device_id
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Serial number
                  </span>

                  <strong>
                    {
                      selectedPrinter
                        .serial_number
                      || '—'
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Model
                  </span>

                  <strong>
                    {
                      selectedPrinter
                        .model_name
                      || '—'
                    }
                  </strong>
                </div>

                <div>
                  <span>
                    Location
                  </span>

                  <strong>
                    {
                      selectedPrinter
                        .location
                      || '—'
                    }
                  </strong>
                </div>

              </div>
            )
          }

        </div>

      </section>


      {
        configuration
        && !loading
        && (
          <div className="configuration-status-row">

            <span
              className={
                configuration.inherited
                  ? 'configuration-status default'
                  : 'configuration-status custom'
              }
            >
              {
                configuration.inherited
                  ? 'Default configuration'
                  : 'Custom configuration'
              }
            </span>

            <span className="configuration-status-help">
              {
                configuration.inherited
                  ? 'Using system default monitoring thresholds'
                  : 'Individual settings are active for this printer'
              }
            </span>

          </div>
        )
      }


      {
        loading
          ? (
            <div className="loading-panel">
              Loading printer configuration...
            </div>
          )
          : configuration
            ? (
              <>

                {
                  configuration.inherited
                  && (
                    <div className="config-default-note">
                      This printer currently uses
                      the system default settings.
                      Save once to create its own
                      individual configuration.
                    </div>
                  )
                }


                <div className="printer-config-grid">

                  <section className="config-section-card">

                    <div className="config-section-header">

                      <div>
                        <span className="config-section-number">
                          01
                        </span>

                        <div>
                          <h2>
                            Monitoring
                          </h2>

                          <p>
                            Data collection and
                            offline detection
                          </p>
                        </div>
                      </div>

                    </div>


                    <div className="config-fields">

                      <label>
                        <span>
                          Collector interval
                          <small>
                            Measurement collection frequency
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            min="1"
                            value={
                              configuration
                                .collector_interval_seconds
                            }
                            onChange={
                              event =>
                                updateField(
                                  'collector_interval_seconds',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            sec
                          </span>
                        </div>
                      </label>


                      <label>
                        <span>
                          Offline timeout
                          <small>
                            Mark printer offline after no data
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            min="5"
                            value={
                              configuration
                                .offline_timeout_seconds
                            }
                            onChange={
                              event =>
                                updateField(
                                  'offline_timeout_seconds',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            sec
                          </span>
                        </div>
                      </label>

                    </div>

                  </section>


                  <section className="config-section-card">

                    <div className="config-section-header">

                      <div>
                        <span className="config-section-number">
                          02
                        </span>

                        <div>
                          <h2>
                            Alert thresholds
                          </h2>

                          <p>
                            Individual limits for
                            this printer
                          </p>
                        </div>
                      </div>

                    </div>


                    <div className="config-fields">

                      <label>
                        <span>
                          Temperature high
                          <small>
                            Warning above this value
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            step="0.1"
                            value={
                              configuration
                                .temperature_high
                            }
                            onChange={
                              event =>
                                updateField(
                                  'temperature_high',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            °C
                          </span>
                        </div>
                      </label>


                      <label>
                        <span>
                          Pressure low
                          <small>
                            Warning below this value
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            step="0.001"
                            value={
                              configuration
                                .pressure_low
                            }
                            onChange={
                              event =>
                                updateField(
                                  'pressure_low',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            MPa
                          </span>
                        </div>
                      </label>


                      <label>
                        <span>
                          Pressure high
                          <small>
                            Warning above this value
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            step="0.001"
                            value={
                              configuration
                                .pressure_high
                            }
                            onChange={
                              event =>
                                updateField(
                                  'pressure_high',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            MPa
                          </span>
                        </div>
                      </label>


                      <label>
                        <span>
                          Ink low
                          <small>
                            Simulator percentage threshold
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={
                              configuration
                                .ink_low
                            }
                            onChange={
                              event =>
                                updateField(
                                  'ink_low',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            %
                          </span>
                        </div>
                      </label>


                      <label>
                        <span>
                          Makeup low
                          <small>
                            Simulator percentage threshold
                          </small>
                        </span>

                        <div className="config-input-unit">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={
                              configuration
                                .makeup_low
                            }
                            onChange={
                              event =>
                                updateField(
                                  'makeup_low',
                                  event.target.value
                                )
                            }
                          />

                          <span>
                            %
                          </span>
                        </div>
                      </label>

                    </div>

                  </section>

                </div>


                <div className="printer-config-actions">

                  <div>
                    <strong>
                      {
                        selectedPrinter
                          ?.display_name
                        || selectedDeviceId
                      }
                    </strong>

                    <span>
                      {' · '}
                      Serial{' '}
                      {
                        selectedPrinter
                          ?.serial_number
                        || '—'
                      }
                    </span>
                  </div>


                  <button
                    type="button"
                    className="primary-button"
                    onClick={
                      saveConfiguration
                    }
                    disabled={saving}
                  >
                    {
                      saving
                        ? 'Saving...'
                        : 'Save configuration'
                    }
                  </button>

                </div>

              </>
            )
            : (
              <div className="empty-state">
                Select a printer.
              </div>
            )
      }

    </div>
  )
}
