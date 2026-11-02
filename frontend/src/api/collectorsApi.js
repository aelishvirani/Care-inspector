import { apiGet, apiPost } from './client'

export const getCollectors = () =>
  apiGet('/secure/management/collectors')

export const registerCollector = payload =>
  apiPost('/secure/management/collectors', payload)

export const getCollectorCustomers = () =>
  apiGet('/secure/management/customers')
