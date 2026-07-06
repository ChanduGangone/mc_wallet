const CURRENCY_FLAGS = {
  USD: '🇺🇸', EUR: '🇪🇺', GBP: '🇬🇧', INR: '🇮🇳', JPY: '🇯🇵',
  AUD: '🇦🇺', CAD: '🇨🇦', CHF: '🇨🇭', CNY: '🇨🇳', SGD: '🇸🇬',
  AED: '🇦🇪', ZAR: '🇿🇦', NZD: '🇳🇿', SEK: '🇸🇪', NOK: '🇳🇴',
  DKK: '🇩🇰', HKD: '🇭🇰', KRW: '🇰🇷', MXN: '🇲🇽', BRL: '🇧🇷',
}

export function currencyFlag(code) {
  return CURRENCY_FLAGS[code] || '💱'
}

export function formatMoney(value, currency) {
  const n = Number(value)
  if (Number.isNaN(n)) return value
  try {
    // Pinned to 'en-US' rather than the browser locale: some locales render
    // USD as "US$1,234.56" (redundant next to the currency chip already
    // shown alongside it); 'en-US' consistently gives the plain "$1,234.56".
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(n)
  } catch {
    return n.toFixed(2)
  }
}

export function formatDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(d)
}

export const TRANSACTION_TYPE_COLORS = {
  credit: 'success',
  debit: 'warning',
  transfer: 'info',
}

export const TRANSACTION_STATUS_COLORS = {
  completed: 'success',
  pending: 'warning',
  failed: 'error',
}
