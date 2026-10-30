import { apiGet, apiPost } from './client'

const BASE = '/secure/management/device-groups'

async function apiDelete(path) {
  const token = localStorage.getItem('care_inspector_token')
  const response = await fetch(`/api${path}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

export const listDeviceGroups = customerId =>
  apiGet(`${BASE}?customer_id=${encodeURIComponent(customerId)}`)

export const createDeviceGroup = (customerId, name) =>
  apiPost(BASE, { customer_id: customerId, name })

export const getGroupDevices = groupId =>
  apiGet(`${BASE}/${groupId}/devices`)

export const addGroupDevice = (groupId, deviceId) =>
  apiPost(`${BASE}/${groupId}/devices/${encodeURIComponent(deviceId)}`, {})

export const removeGroupDevice = (groupId, deviceId) =>
  apiDelete(`${BASE}/${groupId}/devices/${encodeURIComponent(deviceId)}`)

export const getGroupUsers = groupId =>
  apiGet(`${BASE}/${groupId}/users`)

export const addGroupUser = (groupId, userId) =>
  apiPost(`${BASE}/${groupId}/users/${userId}`, {})

export const removeGroupUser = (groupId, userId) =>
  apiDelete(`${BASE}/${groupId}/users/${userId}`)
