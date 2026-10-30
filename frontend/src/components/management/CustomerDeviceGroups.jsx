import { useCallback, useEffect, useState } from 'react'
import {
  listDeviceGroups, createDeviceGroup,
  getGroupDevices, addGroupDevice, removeGroupDevice,
  getGroupUsers, addGroupUser, removeGroupUser,
} from '../../api/deviceGroupsApi'
import '../../styles/device-groups.css'

export default function CustomerDeviceGroups({ customerId, printers = [] }) {
  const [groups, setGroups] = useState([])
  const [name, setName] = useState('')
  const [selections, setSelections] = useState({})
  const [userIds, setUserIds] = useState({})
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const reload = useCallback(async () => {
    const basic = await listDeviceGroups(customerId)
    const complete = await Promise.all(basic.map(async group => {
      const [devices, users] = await Promise.all([
        getGroupDevices(group.id), getGroupUsers(group.id),
      ])
      return { ...group, devices, users }
    }))
    setGroups(complete)
  }, [customerId])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    async function load() {
      try {
        const basic = await listDeviceGroups(customerId)
        const complete = await Promise.all(basic.map(async group => {
          const [devices, users] = await Promise.all([
            getGroupDevices(group.id), getGroupUsers(group.id),
          ])
          return { ...group, devices, users }
        }))
        if (active) setGroups(complete)
      } catch (err) {
        if (active) setError(err.message)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [customerId])

  async function perform(action, success) {
    if (busy) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      await reload()
      setNotice(success)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function create(event) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    perform(async () => {
      await createDeviceGroup(customerId, trimmed)
      setName('')
    }, 'Device group created.')
  }

  return (
    <section className="role-section device-groups-section">
      <div className="role-section-header">
        <div>
          <h2>Device Groups</h2>
          <p>Organize this customer’s printers and control user visibility.</p>
        </div>
        <div className="role-section-count">{groups.length}</div>
      </div>

      <form className="device-groups-create" onSubmit={create}>
        <label htmlFor="new-device-group">New group name</label>
        <input id="new-device-group" value={name} maxLength={120}
          placeholder="e.g. Production Hall A" required
          onChange={event => setName(event.target.value)} />
        <button className="management-primary-button" disabled={busy || !name.trim()} type="submit">
          + Create Group
        </button>
      </form>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {notice && <p className="device-groups-notice" role="status">{notice}</p>}
      {loading && <div className="empty-state">Loading device groups...</div>}
      {!loading && groups.length === 0 && (
        <div className="empty-state">No device groups yet. Create the first group above.</div>
      )}
      <div className="device-groups-grid">
        {groups.map(group => {
          const assignedIds = new Set(group.devices.map(device => device.device_id))
          const available = printers.filter(device => !assignedIds.has(device.device_id))
          return (
            <article key={group.id} className="device-group-card">
              <div className="device-group-heading">
                <h3>{group.name}</h3>
                <span>{group.devices.length} printers · {group.users.length} users</span>
              </div>
              <h4>Assigned printers</h4>
              {group.devices.length === 0 && <p className="device-group-muted">No printers assigned.</p>}
              {group.devices.map(device => (
                <div className="device-group-entry" key={device.device_id}>
                  <span><strong>{device.display_name || device.device_id}</strong><small>{device.device_id}</small></span>
                  <button className="secondary-button" type="button" disabled={busy}
                    onClick={() => perform(() => removeGroupDevice(group.id, device.device_id), 'Printer removed from group.')}>
                    Remove
                  </button>
                </div>
              ))}
              <div className="device-group-add-row">
                <select aria-label={`Printer to add to ${group.name}`}
                  value={selections[group.id] || ''}
                  onChange={event => setSelections(previous => ({ ...previous, [group.id]: event.target.value }))}>
                  <option value="">Select customer printer</option>
                  {available.map(device => <option key={device.device_id} value={device.device_id}>
                    {device.display_name || device.device_id}
                  </option>)}
                </select>
                <button type="button" className="management-primary-button" disabled={busy || !selections[group.id]}
                  onClick={() => perform(async () => {
                    await addGroupDevice(group.id, selections[group.id])
                    setSelections(previous => ({ ...previous, [group.id]: '' }))
                  }, 'Printer assigned to group.')}>
                  Add Printer
                </button>
              </div>

              <h4>Users with access</h4>
              {group.users.length === 0 && <p className="device-group-muted">No users assigned. This group is not visible to customers.</p>}
              {group.users.map(user => (
                <div className="device-group-entry" key={user.id}>
                  <span><strong>{user.email}</strong><small>User ID: {user.id}</small></span>
                  <button className="secondary-button" type="button" disabled={busy}
                    onClick={() => perform(() => removeGroupUser(group.id, user.id), 'User access removed.')}>
                    Remove
                  </button>
                </div>
              ))}
              <div className="device-group-add-row">
                <input type="number" min="1" step="1" aria-label={`Customer user ID for ${group.name}`}
                  placeholder="Customer user ID" value={userIds[group.id] || ''}
                  onChange={event => setUserIds(previous => ({ ...previous, [group.id]: event.target.value }))} />
                <button type="button" className="management-primary-button"
                  disabled={busy || !Number.isSafeInteger(Number(userIds[group.id])) || Number(userIds[group.id]) < 1}
                  onClick={() => perform(async () => {
                    await addGroupUser(group.id, Number(userIds[group.id]))
                    setUserIds(previous => ({ ...previous, [group.id]: '' }))
                  }, 'Customer user assigned to group.')}>
                  Add User
                </button>
              </div>
              <p className="device-group-muted">Only active users belonging to this customer can be assigned. User selection by name can be added next.</p>
            </article>
          )
        })}
      </div>
    </section>
  )
}
