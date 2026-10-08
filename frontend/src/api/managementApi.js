const API_BASE = '/api'


function getToken() {
  return localStorage.getItem(
    'care_inspector_token'
  )
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
          'Content-Type':
            'application/json',

          Authorization:
            `Bearer ${getToken()}`,

          ...(options.headers || {}),
        },
      }
    )


  let data = null

  try {
    data =
      await response.json()
  } catch {
    data = null
  }


  if (!response.ok) {
    throw new Error(
      data?.detail
      || `Request failed (${response.status})`
    )
  }


  return data
}


export function getCustomers() {
  return request(
    '/secure/management/customers'
  )
}


export function getCustomer(
  customerId
) {
  return request(
    `/secure/management/customers/${customerId}`
  )
}


export function createCustomer(
  payload
) {
  return request(
    '/secure/management/customers',
    {
      method: 'POST',

      body: JSON.stringify(
        payload
      ),
    }
  )
}


export function updateCustomer(
  customerId,
  payload
) {
  return request(
    `/secure/management/customers/${customerId}`,
    {
      method: 'PATCH',

      body: JSON.stringify(
        payload
      ),
    }
  )
}


export function getManagedDevices() {
  return request(
    '/secure/management/devices'
  )
}


export function registerDevice(
  payload
) {
  return request(
    '/secure/management/devices',
    {
      method: 'POST',

      body: JSON.stringify(
        payload
      ),
    }
  )
}


export function updateDevice(
  deviceId,
  payload
) {
  return request(
    `/secure/management/devices/${encodeURIComponent(
      deviceId
    )}`,
    {
      method: 'PATCH',

      body: JSON.stringify(
        payload
      ),
    }
  )
}
