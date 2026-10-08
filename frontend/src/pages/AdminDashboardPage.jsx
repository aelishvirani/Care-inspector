import {
  useEffect,
  useState,
} from 'react'

import {
  getAdminDashboard,
} from '../api/adminApi'


export default function AdminDashboardPage() {
  const [
    data,
    setData,
  ] = useState(null)

  const [
    loading,
    setLoading,
  ] = useState(true)

  const [
    error,
    setError,
  ] = useState(null)


  async function load() {
    try {
      setLoading(true)
      setError(null)

      setData(
        await getAdminDashboard()
      )

    } catch (err) {
      setError(
        err.message
      )

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    load()
  }, [])


  if (loading) {
    return (
      <div className="loading-panel">
        Loading admin dashboard...
      </div>
    )
  }


  return (
    <div className="page">

      <div className="page-header">

        <div>
          <h1>
            Admin Dashboard
          </h1>

          <p>
            Care-Inspector system
            administration and fleet overview
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
        >
          Refresh
        </button>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      {data && (
        <div className="printer-summary-grid">

          <div className="summary-card">
            <span>Customers</span>
            <strong>{data.customers}</strong>
          </div>

          <div className="summary-card">
            <span>Users</span>
            <strong>{data.users}</strong>
          </div>

          <div className="summary-card">
            <span>Printers</span>
            <strong>{data.printers}</strong>
          </div>

          <div className="summary-card">
            <span>Online</span>
            <strong>{data.online}</strong>
          </div>

          <div className="summary-card">
            <span>Offline</span>
            <strong>{data.offline}</strong>
          </div>

          <div className="summary-card">
            <span>Unassigned</span>
            <strong>{data.unassigned}</strong>
          </div>

          <div className="summary-card">
            <span>Active Alerts</span>
            <strong>{data.active_alerts}</strong>
          </div>

          <div className="summary-card">
            <span>Critical Alerts</span>
            <strong>{data.critical_alerts}</strong>
          </div>

        </div>
      )}

    </div>
  )
}
