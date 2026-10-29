import {
  apiGet,
  apiPut,
} from '../api/client'


export function getConfiguration() {
  return apiGet('/configuration')
}


export function updateConfiguration(
  configuration
) {
  return apiPut(
    '/configuration',
    configuration
  )
}
