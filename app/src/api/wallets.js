import client from './client'
import { newIdempotencyKey } from '@/utils/idempotency'

export function getWallets() {
  return client.get('/wallets').then((r) => r.data)
}

export function credit(walletId, { amount, currency }) {
  return client
    .post(
      `/wallets/${walletId}/credit`,
      { amount, currency },
      { headers: { 'Idempotency-Key': newIdempotencyKey() } },
    )
    .then((r) => r.data)
}
