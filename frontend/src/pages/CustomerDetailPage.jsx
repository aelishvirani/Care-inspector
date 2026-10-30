import {
  useEffect,
  useState,
} from 'react'

import {
  Link,
  useParams,
} from 'react-router-dom'

import {
  getCustomer,
  getManagedDevices,
  registerDevice,
  updateCustomer,
  updateDevice,
} from '../api/managementApi'

import CustomerDeviceGroups from '../components/management/CustomerDeviceGroups'
import PrinterConnectionForm from '../components/management/PrinterConnectionForm'
import PrinterConnectionStatus from '../components/management/PrinterConnectionStatus'
import '../styles/printer-connection-status.css'
import '../styles/management.css'


const EMPTY_DEVICE = {
  device_id: '',
  display_name: '',
  location: '',
  model_name: '',
  serial_number: '',
  ink_name: '',
}


export default function CustomerDetailPage() {
  const {
    customerId,
  } = useParams()

  const [connectionDeviceId, setConnectionDeviceId] = useState(null)
  const [connectionRefreshKey, setConnectionRefreshKey] = useState(0)

  const numericCustomerId =
    Number(customerId)

  const [
    customer,
    setCustomer,
  ] = useState(null)

  const [
    allDevices,
    setAllDevices,
  ] = useState([])

  const [
    edit,
    setEdit,
  ] = useState({})

  const [
    newDevice,
    setNewDevice,
  ] = useState(
    EMPTY_DEVICE
  )

  const [
    showRegister,
    setShowRegister,
  ] = useState(false)

  const [
    loading,
    setLoading,
  ] = useState(true)

  const [
    error,
    setError,
  ] = useState(null)


  async function refresh() {
    try {
      const [
        customerData,
        devices,
      ] = await Promise.all([
        getCustomer(
          numericCustomerId
        ),

        getManagedDevices(),
      ])

      setCustomer(
        customerData
      )

      setEdit({
        name:
          customerData.name || '',

        address:
          customerData.address || '',

        contact_name:
          customerData.contact_name
          || '',

        contact_email:
          customerData.contact_email
          || '',

        contact_phone:
          customerData.contact_phone
          || '',

        active:
          customerData.active,
      })

      setAllDevices(
        devices
      )

      setError(null)

    } catch (err) {
      setError(err.message)

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()
  }, [customerId])


  async function saveCustomer(
    event
  ) {
    event.preventDefault()

    try {
      await updateCustomer(
        numericCustomerId,
        edit
      )

      await refresh()

    } catch (err) {
      setError(err.message)
    }
  }


  async function createPrinter(
    event
  ) {
    event.preventDefault()

    try {
      await registerDevice({
        ...newDevice,

        customer_id:
          numericCustomerId,

        serial_number:
          newDevice.serial_number
            ? Number(
                newDevice.serial_number
              )
            : null,
      })

      setNewDevice(
        EMPTY_DEVICE
      )

      setShowRegister(false)

      await refresh()

    } catch (err) {
      setError(err.message)
    }
  }


  async function assignPrinter(
    deviceId
  ) {
    try {
      await updateDevice(
        deviceId,
        {
          customer_id:
            numericCustomerId,
        }
      )

      await refresh()

    } catch (err) {
      setError(err.message)
    }
  }


  async function unassignPrinter(
    deviceId
  ) {
    try {
      await updateDevice(
        deviceId,
        {
          customer_id: null,
        }
      )

      await refresh()

    } catch (err) {
      setError(err.message)
    }
  }


  if (loading) {
    return (
      <div className="loading-panel">
        Loading customer...
      </div>
    )
  }


  if (!customer) {
    return (
      <div className="empty-state">
        Customer not found.
      </div>
    )
  }


  const unassignedDevices =
    allDevices.filter(
      device =>
        device.customer_id
        === null
        || device.customer_id
        === undefined
    )


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>

          <Link
            className="back-link"
            to="/customers"
          >
            ← Customers
          </Link>

          <span className="role-dashboard-eyebrow">
            Customer
          </span>

          <h1>
            {customer.name}
          </h1>

          <p>
            Company details and
            installed printer fleet.
          </p>

        </div>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <section className="management-form-card">

        <div className="management-section-title">
          <h2>
            Company Details
          </h2>

          <p>
            Technician-managed customer
            and service contact data.
          </p>
        </div>


        <form
          className="management-form-grid"
          onSubmit={saveCustomer}
        >

          {
            [
              [
                'name',
                'Company Name',
              ],
              [
                'address',
                'Address',
              ],
              [
                'contact_name',
                'Contact Person',
              ],
              [
                'contact_email',
                'Email',
              ],
              [
                'contact_phone',
                'Phone',
              ],
            ].map(
              ([field, label]) => (

                <label key={field}>
                  {label}

                  <input
                    value={
                      edit[field] || ''
                    }
                    onChange={
                      event =>
                        setEdit(
                          previous => ({
                            ...previous,

                            [field]:
                              event
                                .target
                                .value,
                          })
                        )
                    }
                  />
                </label>

              )
            )
          }


          <label className="management-checkbox">
            <input
              type="checkbox"
              checked={
                Boolean(
                  edit.active
                )
              }
              onChange={
                event =>
                  setEdit(
                    previous => ({
                      ...previous,
                      active:
                        event
                          .target
                          .checked,
                    })
                  )
              }
            />

            Customer active
          </label>


          <div className="management-form-actions">

            <button
              className="management-primary-button"
              type="submit"
            >
              Save Company
            </button>

          </div>

        </form>

      </section>


      <CustomerDeviceGroups
        customerId={numericCustomerId}
        printers={customer.printers || []}
      />

      {connectionDeviceId && (
        <PrinterConnectionForm
          deviceId={connectionDeviceId}
          onClose={() => {
            setConnectionDeviceId(null)
            setConnectionRefreshKey(value => value + 1)
          }}
        />
      )}

      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Installed Printers
            </h2>

            <p>
              Printers currently assigned
              to {customer.name}.
            </p>
          </div>


          <button
            className="management-primary-button"
            onClick={() =>
              setShowRegister(
                value => !value
              )
            }
          >
            {
              showRegister
                ? 'Cancel'
                : '+ Register Printer'
            }
          </button>

        </div>


        {
          showRegister
          && (
            <form
              className="management-form-grid management-inline-form"
              onSubmit={
                createPrinter
              }
            >

              <label>
                Device ID *
                <input
                  required
                  placeholder={
                    'e.g. hitachi-ux2-004'
                  }
                  value={
                    newDevice.device_id
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          device_id:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <label>
                Display Name
                <input
                  placeholder={
                    'Production Printer 04'
                  }
                  value={
                    newDevice
                      .display_name
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          display_name:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <label>
                Location
                <input
                  placeholder={
                    'Production Hall'
                  }
                  value={
                    newDevice.location
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          location:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <label>
                Model
                <input
                  placeholder={
                    'UX-D150W'
                  }
                  value={
                    newDevice.model_name
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          model_name:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <label>
                Serial Number
                <input
                  inputMode="numeric"
                  value={
                    newDevice
                      .serial_number
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          serial_number:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <label>
                Ink
                <input
                  placeholder="1072K"
                  value={
                    newDevice.ink_name
                  }
                  onChange={
                    event =>
                      setNewDevice(
                        previous => ({
                          ...previous,
                          ink_name:
                            event.target.value,
                        })
                      )
                  }
                />
              </label>


              <div className="management-form-actions">

                <button
                  className="management-primary-button"
                  type="submit"
                >
                  Register & Assign
                </button>

              </div>

            </form>
          )
        }


        <div className="management-printer-list">

          {
            customer.printers.length
              === 0
            ? (
              <div className="empty-state">
                No printers assigned.
              </div>
            )
            : customer.printers.map(
                printer => (

                  <div
                    key={
                      printer.device_id
                    }
                    className="management-printer-row"
                  >

                    <div>
                      <strong>
                        {
                          printer.display_name
                          || printer.device_id
                        }
                      </strong>

                      <span>
                        {
                          printer.model_name
                          || 'Unknown model'
                        }
                        {' · '}
                        {
                          printer.location
                          || 'No location'
                        }
                      </span>
                    </div>


                    <div>
                      <span>
                        Device ID
                      </span>

                      <strong>
                        {printer.device_id}
                      </strong>
                    </div>


                    <div>
                      <span>
                        Serial
                      </span>

                      <strong>
                        {
                          printer.serial_number
                          || '—'
                        }
                      </strong>
                    </div>


                    <div className="management-row-actions">

                      <Link
                        className="secondary-button"
                        to={
                          `/printers/${encodeURIComponent(
                            printer.device_id
                          )}`
                        }
                      >
                        Open
                      </Link>


                      <PrinterConnectionStatus
                        deviceId={printer.device_id}
                        refreshKey={connectionRefreshKey}
                      />

                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() =>
                          setConnectionDeviceId(printer.device_id)
                        }
                      >
                        Configure Connection
                      </button>

                      <button
                        className="secondary-button"
                        onClick={() =>
                          unassignPrinter(
                            printer.device_id
                          )
                        }
                      >
                        Unassign
                      </button>

                    </div>

                  </div>

                )
              )
          }

        </div>

      </section>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Unassigned Printers
            </h2>

            <p>
              Existing collectors/printers
              that are not yet linked
              to a company.
            </p>
          </div>

          <div className="role-section-count">
            {
              unassignedDevices.length
            }
          </div>

        </div>


        <div className="management-printer-list">

          {
            unassignedDevices.length
              === 0
            ? (
              <div className="empty-state">
                No unassigned printers.
              </div>
            )
            : unassignedDevices.map(
                printer => (

                  <div
                    key={
                      printer.device_id
                    }
                    className="management-printer-row"
                  >

                    <div>
                      <strong>
                        {
                          printer.display_name
                          || printer.device_id
                        }
                      </strong>

                      <span>
                        {
                          printer.model_name
                          || 'Unknown model'
                        }
                      </span>
                    </div>


                    <div>
                      <span>
                        Device ID
                      </span>

                      <strong>
                        {printer.device_id}
                      </strong>
                    </div>


                    <div className="management-row-actions">

                      <button
                        className="management-primary-button"
                        onClick={() =>
                          assignPrinter(
                            printer.device_id
                          )
                        }
                      >
                        Assign to Customer
                      </button>

                    </div>

                  </div>

                )
              )
          }

        </div>

      </section>

    </div>
  )
}
