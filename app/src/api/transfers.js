import client from './client'
import { newIdempotencyKey } from '@/utils/idempotency'

export function createTransfer({ from_wallet_id, to_email, to_currency, amount }) {
  const payload = { from_wallet_id, to_email, amount }
  if (to_currency) payload.to_currency = to_currency
  return client
    .post('/transfers', payload, { headers: { 'Idempotency-Key': newIdempotencyKey() } })
    .then((r) => r.data)
}
