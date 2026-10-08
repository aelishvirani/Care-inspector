import {
  apiGet,
  apiPost,
} from './client'


const API_BASE = '/api'


function authHeaders() {
  const token =
    localStorage.getItem(
      'care_inspector_token'
    )

  return {
    'Content-Type':
      'application/json',

    Authorization:
      `Bearer ${token}`,
  }
}


async function request(
  path,
  options = {}
) {
  const response =
    await fetch(
      `${API_BASE}${path}`,
      {
        ...options,

        headers: {
          ...authHeaders(),
          ...(options.headers || {}),
        },
      }
    )

  let body = null

  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    throw new Error(
      body?.detail
      || `Request failed (${response.status})`
    )
  }

  return body
}


export function getAdminDashboard() {
  return apiGet(
    '/secure/admin/dashboard'
  )
}


export function getAdminUsers() {
  return apiGet(
    '/secure/admin/users'
  )
}


export function createAdminUser(
  payload
) {
  return apiPost(
    '/secure/admin/users',
    payload
  )
}


export function updateAdminUser(
  userId,
  payload
) {
  return request(
    `/secure/admin/users/${userId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(
        payload
      ),
    }
  )
}


export function getAuditLog() {
  return apiGet(
    '/secure/admin/audit-log'
  )
}


export function getSystemHealth() {
  return apiGet(
    '/secure/admin/system-health'
  )
}
