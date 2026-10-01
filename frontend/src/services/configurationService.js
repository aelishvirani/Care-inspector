import {
  apiGet,
} from '../api/client'


export function getConfiguration() {
  return apiGet('/configuration')
}


export async function updateConfiguration(
  configuration
) {
  const response = await fetch(
    '/api/configuration',
    {
      method: 'PUT',

      headers: {
        'Content-Type':
          'application/json',
      },

      body: JSON.stringify(
        configuration
      ),
    }
  )

  if (!response.ok) {
    throw new Error(
      'Configuration update failed'
    )
  }

  return response.json()
}
