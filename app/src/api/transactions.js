import client from './client'

export function getTransactions(filters = {}) {
  const params = {}
  if (filters.type) params.type = filters.type
  if (filters.currency) params.currency = filters.currency
  if (filters.start_date) params.start_date = filters.start_date
  if (filters.end_date) params.end_date = filters.end_date
  params.limit = filters.limit ?? 20
  params.offset = filters.offset ?? 0
  return client.get('/transactions', { params }).then((r) => r.data)
}
