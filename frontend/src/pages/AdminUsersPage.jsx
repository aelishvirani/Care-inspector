import {
  useEffect,
  useState,
} from 'react'

import {
  createAdminUser,
  getAdminUsers,
  updateAdminUser,
} from '../api/adminApi'

import {
  getCustomers,
} from '../api/managementApi'


export default function AdminUsersPage() {
  const [
    users,
    setUsers,
  ] = useState([])

  const [
    customers,
    setCustomers,
  ] = useState([])

  const [
    error,
    setError,
  ] = useState(null)

  const [
    form,
    setForm,
  ] = useState({
    email: '',
    password: '',
    role: 'CUSTOMER',
    customer_id: '',
  })


  async function load() {
    try {
      setError(null)

      const [
        userRows,
        customerRows,
      ] = await Promise.all([
        getAdminUsers(),
        getCustomers(),
      ])

      setUsers(userRows)
      setCustomers(customerRows)

    } catch (err) {
      setError(err.message)
    }
  }


  useEffect(() => {
    load()
  }, [])


  async function createUser(
    event
  ) {
    event.preventDefault()

    try {
      await createAdminUser({
        email: form.email,
        password: form.password,
        role: form.role,

        customer_id:
          form.role === 'CUSTOMER'
            ? Number(
                form.customer_id
              )
            : null,
      })

      setForm({
        email: '',
        password: '',
        role: 'CUSTOMER',
        customer_id: '',
      })

      await load()

    } catch (err) {
      setError(err.message)
    }
  }


  async function toggleActive(
    row
  ) {
    try {
      await updateAdminUser(
        row.id,
        {
          active: !row.active,
        }
      )

      await load()

    } catch (err) {
      setError(err.message)
    }
  }


  return (
    <div className="page">

      <div className="page-header">
        <div>
          <h1>
            Users
          </h1>

          <p>
            Manage Care-Inspector accounts
            and roles
          </p>
        </div>
      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <section className="panel">

        <h2>Create User</h2>

        <form
          onSubmit={createUser}
          className="filter-toolbar"
        >

          <div className="filter-group">
            <label>Email</label>

            <input
              required
              type="email"
              value={form.email}
              onChange={
                event =>
                  setForm({
                    ...form,
                    email:
                      event.target.value,
                  })
              }
            />
          </div>


          <div className="filter-group">
            <label>Password</label>

            <input
              required
              type="password"
              minLength="8"
              value={form.password}
              onChange={
                event =>
                  setForm({
                    ...form,
                    password:
                      event.target.value,
                  })
              }
            />
          </div>


          <div className="filter-group">
            <label>Role</label>

            <select
              value={form.role}
              onChange={
                event =>
                  setForm({
                    ...form,
                    role:
                      event.target.value,
                    customer_id: '',
                  })
              }
            >
              <option value="CUSTOMER">
                Customer
              </option>

              <option value="TECHNICIAN">
                Technician
              </option>

              <option value="ADMIN">
                Admin
              </option>
            </select>
          </div>


          {
            form.role === 'CUSTOMER'
            && (
              <div className="filter-group">
                <label>
                  Customer
                </label>

                <select
                  required
                  value={
                    form.customer_id
                  }
                  onChange={
                    event =>
                      setForm({
                        ...form,
                        customer_id:
                          event.target.value,
                      })
                  }
                >
                  <option value="">
                    Select customer
                  </option>

                  {
                    customers.map(
                      customer => (
                        <option
                          key={
                            customer.id
                          }
                          value={
                            customer.id
                          }
                        >
                          {customer.name}
                        </option>
                      )
                    )
                  }
                </select>
              </div>
            )
          }


          <button
            className="secondary-button"
            type="submit"
          >
            Create User
          </button>

        </form>

      </section>


      <section className="panel">

        <div className="alert-table-wrapper">

          <table className="alert-table">

            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Customer ID</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>

              {
                users.map(
                  row => (
                    <tr key={row.id}>

                      <td>{row.email}</td>

                      <td>{row.role}</td>

                      <td>
                        {
                          row.customer_id
                          ?? '—'
                        }
                      </td>

                      <td>
                        {
                          row.active
                            ? 'Active'
                            : 'Inactive'
                        }
                      </td>

                      <td>
                        <button
                          className="secondary-button"
                          onClick={() =>
                            toggleActive(
                              row
                            )
                          }
                        >
                          {
                            row.active
                              ? 'Deactivate'
                              : 'Activate'
                          }
                        </button>
                      </td>

                    </tr>
                  )
                )
              }

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}
