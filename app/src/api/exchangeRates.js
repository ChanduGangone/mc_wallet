import client from './client'

export function getLatestRates() {
  return client.get('/exchange-rates/latest').then((r) => r.data)
}
