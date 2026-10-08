import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  useNavigate,
} from 'react-router-dom'

import {
  createCustomer,
  getCustomers,
  getManagedDevices,
} from '../api/managementApi'

import '../styles/management.css'


const EMPTY_FORM = {
  name: '',
  address: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
}


export default function CustomersPage() {
  const navigate =
    useNavigate()

  const [
    customers,
    setCustomers,
  ] = useState([])

  const [
    devices,
    setDevices,
  ] = useState([])

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    showForm,
    setShowForm,
  ] = useState(false)

  const [
    form,
    setForm,
  ] = useState(
    EMPTY_FORM
  )

  const [
    loading,
    setLoading,
  ] = useState(true)

  const [
    saving,
    setSaving,
  ] = useState(false)

  const [
    error,
    setError,
  ] = useState(null)


  async function refresh() {
    try {
      const [
        customerRows,
        deviceRows,
      ] = await Promise.all([
        getCustomers(),
        getManagedDevices(),
      ])

      setCustomers(
        customerRows
      )

      setDevices(
        deviceRows
      )

      setError(null)

    } catch (err) {
      console.error(err)
      setError(err.message)

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    refresh()
  }, [])


  const filtered =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        if (!term) {
          return customers
        }

        return customers.filter(
          customer =>
            [
              customer.name,
              customer.address,
              customer.contact_name,
              customer.contact_email,
              customer.contact_phone,
            ]
              .filter(Boolean)
              .some(
                value =>
                  String(value)
                    .toLowerCase()
                    .includes(term)
              )
        )
      },
      [
        customers,
        search,
      ]
    )


  function updateForm(
    field,
    value
  ) {
    setForm(
      previous => ({
        ...previous,
        [field]: value,
      })
    )
  }


  async function submit(
    event
  ) {
    event.preventDefault()

    try {
      setSaving(true)

      const customer =
        await createCustomer({
          ...form,
          active: true,
        })

      setForm(
        EMPTY_FORM
      )

      setShowForm(false)

      await refresh()

      navigate(
        `/customers/${customer.id}`
      )

    } catch (err) {
      setError(err.message)

    } finally {
      setSaving(false)
    }
  }


  if (loading) {
    return (
      <div className="loading-panel">
        Loading customers...
      </div>
    )
  }


  return (
    <div className="role-dashboard">

      <div className="role-dashboard-header">

        <div>
          <span className="role-dashboard-eyebrow">
            Customer Management
          </span>

          <h1>
            Customers
          </h1>

          <p>
            Manage companies,
            contacts and installed
            printers.
          </p>
        </div>


        <button
          className="management-primary-button"
          onClick={() =>
            setShowForm(
              value => !value
            )
          }
        >
          {
            showForm
              ? 'Cancel'
              : '+ Add Customer'
          }
        </button>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {
        showForm
        && (
          <section className="management-form-card">

            <div className="management-section-title">
              <h2>
                Add Customer
              </h2>

              <p>
                Create the company
                before assigning printers.
              </p>
            </div>


            <form
              className="management-form-grid"
              onSubmit={submit}
            >

              <label>
                Company Name *
                <input
                  required
                  value={form.name}
                  onChange={
                    event =>
                      updateForm(
                        'name',
                        event.target.value
                      )
                  }
                />
              </label>


              <label>
                Address
                <input
                  value={form.address}
                  onChange={
                    event =>
                      updateForm(
                        'address',
                        event.target.value
                      )
                  }
                />
              </label>


              <label>
                Contact Person
                <input
                  value={
                    form.contact_name
                  }
                  onChange={
                    event =>
                      updateForm(
                        'contact_name',
                        event.target.value
                      )
                  }
                />
              </label>


              <label>
                Email
                <input
                  type="email"
                  value={
                    form.contact_email
                  }
                  onChange={
                    event =>
                      updateForm(
                        'contact_email',
                        event.target.value
                      )
                  }
                />
              </label>


              <label>
                Phone
                <input
                  value={
                    form.contact_phone
                  }
                  onChange={
                    event =>
                      updateForm(
                        'contact_phone',
                        event.target.value
                      )
                  }
                />
              </label>


              <div className="management-form-actions">

                <button
                  className="management-primary-button"
                  disabled={saving}
                  type="submit"
                >
                  {
                    saving
                      ? 'Saving...'
                      : 'Create Customer'
                  }
                </button>

              </div>

            </form>

          </section>
        )
      }


      <div className="role-toolbar">

        <input
          className="role-search"
          type="search"
          placeholder={
            'Search company, contact, email, address...'
          }
          value={search}
          onChange={
            event =>
              setSearch(
                event.target.value
              )
          }
        />

      </div>


      <section className="role-section">

        <div className="role-section-header">

          <div>
            <h2>
              Companies
            </h2>

            <p>
              Click a company to manage
              its printers.
            </p>
          </div>

          <div className="role-section-count">
            {filtered.length}
          </div>

        </div>


        <div className="management-customer-list">

          {
            filtered.map(
              customer => {

                const printerCount =
                  devices.filter(
                    device =>
                      device.customer_id
                      === customer.id
                  ).length

                return (
                  <button
                    key={customer.id}
                    className="management-customer-row"
                    onClick={() =>
                      navigate(
                        `/customers/${customer.id}`
                      )
                    }
                  >

                    <div>
                      <strong>
                        {customer.name}
                      </strong>

                      <span>
                        {
                          customer.address
                          || 'No address'
                        }
                      </span>
                    </div>


                    <div>
                      <span>
                        Contact
                      </span>

                      <strong>
                        {
                          customer.contact_name
                          || '—'
                        }
                      </strong>
                    </div>


                    <div>
                      <span>
                        Printers
                      </span>

                      <strong>
                        {printerCount}
                      </strong>
                    </div>


                    <div>
                      <span
                        className={
                          customer.active
                            ? 'management-active'
                            : 'management-inactive'
                        }
                      >
                        {
                          customer.active
                            ? 'Active'
                            : 'Inactive'
                        }
                      </span>
                    </div>

                  </button>
                )
              }
            )
          }

        </div>

      </section>

    </div>
  )
}
