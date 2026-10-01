import {
  useConfiguration,
} from '../hooks/useConfiguration'


export default function ConfigurationPage() {

  const {
    configuration,
    setConfiguration,
    loading,
    saving,
    error,
    saved,
    save,
  } = useConfiguration()


  if (loading) {
    return (
      <div className="loading-panel">
        Loading configuration...
      </div>
    )
  }


  if (!configuration) {
    return (
      <div className="error-banner">
        Configuration unavailable.
      </div>
    )
  }


  function updateField(
    field,
    value
  ) {
    setConfiguration({
      ...configuration,
      [field]: value,
    })
  }


  return (
    <div className="page">

      <div className="page-heading">
        <div>
          <h1>
            Configuration
          </h1>

          <p>
            Printer connection,
            monitoring and alert settings
          </p>
        </div>
      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {saved && (
        <div className="success-banner">
          Configuration saved.
        </div>
      )}


      <div className="configuration-grid">


        <section className="panel">

          <div className="panel-header">
            <div>
              <h2>
                Monitoring
              </h2>

              <p>
                Collection and offline
                detection
              </p>
            </div>
          </div>


          <div className="config-form">

            <label>
              Collector Interval
              <span>seconds</span>
            </label>

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
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Offline Timeout
              <span>seconds</span>
            </label>

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
                    Number(
                      event.target.value
                    )
                  )
              }
            />

          </div>

        </section>


        <section className="panel">

          <div className="panel-header">
            <div>
              <h2>
                Alert Thresholds
              </h2>

              <p>
                Demo threshold values
              </p>
            </div>
          </div>


          <div className="config-form">

            <label>
              Temperature High
              <span>°C</span>
            </label>

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
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Pressure Low
              <span>MPa</span>
            </label>

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
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Pressure High
              <span>MPa</span>
            </label>

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
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Ink Low
              <span>%</span>
            </label>

            <input
              type="number"
              value={
                configuration
                  .ink_low
              }
              onChange={
                event =>
                  updateField(
                    'ink_low',
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Makeup Low
              <span>%</span>
            </label>

            <input
              type="number"
              value={
                configuration
                  .makeup_low
              }
              onChange={
                event =>
                  updateField(
                    'makeup_low',
                    Number(
                      event.target.value
                    )
                  )
              }
            />

          </div>

        </section>


        <section className="panel">

          <div className="panel-header">
            <div>
              <h2>
                Printer Connection
              </h2>

              <p>
                Simulator or physical
                Hitachi connection
              </p>
            </div>
          </div>


          <div className="config-form">

            <label>
              Printer Mode
            </label>

            <select
              value={
                configuration
                  .printer_mode
              }
              onChange={
                event =>
                  updateField(
                    'printer_mode',
                    event.target.value
                  )
              }
            >

              <option value="simulator">
                Simulator
              </option>

              <option value="hitachi_modbus">
                Hitachi Modbus
              </option>

            </select>


            <label>
              Host / IP
            </label>

            <input
              type="text"
              value={
                configuration
                  .printer_host
              }
              onChange={
                event =>
                  updateField(
                    'printer_host',
                    event.target.value
                  )
              }
            />


            <label>
              Port
            </label>

            <input
              type="number"
              value={
                configuration
                  .printer_port
              }
              onChange={
                event =>
                  updateField(
                    'printer_port',
                    Number(
                      event.target.value
                    )
                  )
              }
            />


            <label>
              Modbus Device ID
            </label>

            <input
              type="number"
              value={
                configuration
                  .device_id
              }
              onChange={
                event =>
                  updateField(
                    'device_id',
                    Number(
                      event.target.value
                    )
                  )
              }
            />

          </div>

        </section>

      </div>


      <div className="configuration-actions">

        <button
          className="primary-button"
          onClick={save}
          disabled={saving}
        >
          {
            saving
              ? 'Saving...'
              : 'Save Configuration'
          }
        </button>

      </div>

    </div>
  )
}
