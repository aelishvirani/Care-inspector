const API_BASE = '/api'


function authHeaders() {
  const token =
    localStorage.getItem(
      'care_inspector_token'
    )

  if (!token) {
    return {}
  }

  return {
    Authorization:
      `Bearer ${token}`,
  }
}


async function handleResponse(
  response
) {
  if (response.status === 401) {
    localStorage.removeItem(
      'care_inspector_token'
    )

    localStorage.removeItem(
      'care_inspector_user'
    )
  }

  if (!response.ok) {
    let message =
      `API request failed: ${response.status}`

    try {
      const body =
        await response.json()

      if (body.detail) {
        message = body.detail
      }

    } catch {
      // Keep default message.
    }

    throw new Error(message)
  }

  return response.json()
}


export async function apiGet(
  path,
  authenticated = true
) {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      headers:
        authenticated
          ? authHeaders()
          : {},
    }
  )

  return handleResponse(
    response
  )
}


export async function apiPost(
  path,
  data,
  authenticated = true
) {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      method: 'POST',

      headers: {
        'Content-Type':
          'application/json',

        ...(
          authenticated
            ? authHeaders()
            : {}
        ),
      },

      body: JSON.stringify(data),
    }
  )

  return handleResponse(
    response
  )
}


export async function apiPut(
  path,
  data,
  authenticated = true
) {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      method: 'PUT',

      headers: {
        'Content-Type':
          'application/json',

        ...(
          authenticated
            ? authHeaders()
            : {}
        ),
      },

      body: JSON.stringify(data),
    }
  )

  return handleResponse(
    response
  )
}
