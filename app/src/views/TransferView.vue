<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import CurrencySelect from '@/components/CurrencySelect.vue'
import { formatMoney } from '@/utils/format'

const store = useStore()
const wallets = computed(() => store.state.wallets.wallets)
const rates = computed(() => store.state.wallets.exchangeRates)

const fromWalletId = ref(null)
const toEmail = ref('')
const toCurrency = ref(null)
const amount = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)

const walletOptions = computed(() =>
  wallets.value.map((w) => ({
    title: `${w.currency} — balance ${formatMoney(w.balance, w.currency)}`,
    value: w.wallet_id,
  })),
)

const fromWallet = computed(() => wallets.value.find((w) => w.wallet_id === fromWalletId.value))

function rateFor(code) {
  if (!rates.value || !code) return null
  if (code === rates.value.base_currency) return 1
  return rates.value.rates[code] ?? null
}

const estimatedAmount = computed(() => {
  if (!amount.value || !fromWallet.value || !toCurrency.value) return null
  const fromRate = rateFor(fromWallet.value.currency)
  const toRate = rateFor(toCurrency.value)
  if (!fromRate || !toRate) return null
  return ((amount.value * toRate) / fromRate).toFixed(4)
})

async function handleSubmit() {
  errorMessage.value = ''
  successMessage.value = ''
  if (!fromWalletId.value || !toEmail.value || !amount.value || amount.value <= 0) {
    errorMessage.value = 'Please fill in all required fields with a valid amount.'
    return
  }
  loading.value = true
  try {
    const result = await store.dispatch('wallets/createTransfer', {
      from_wallet_id: fromWalletId.value,
      to_email: toEmail.value,
      to_currency: toCurrency.value || undefined,
      amount: amount.value,
    })
    successMessage.value = `Transfer complete. Recipient received ${result.converted_amount} ${result.to_currency}.`
    amount.value = null
    toEmail.value = ''
    toCurrency.value = null
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Transfer failed. Please try again.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  store.dispatch('wallets/fetchWallets')
  store.dispatch('wallets/fetchExchangeRates')
})
</script>

<template>
  <v-row justify="center">
    <v-col cols="12" sm="9" md="7">
      <div class="mb-6">
        <h1 class="text-h5 font-weight-bold">Send money</h1>
        <p class="text-medium-emphasis">Transfer between your wallets or to another user</p>
      </div>

      <v-card>
        <v-card-text class="pa-6">
          <v-form @submit.prevent="handleSubmit">
            <v-select
              v-model="fromWalletId"
              :items="walletOptions"
              item-title="title"
              item-value="value"
              label="From wallet"
              prepend-inner-icon="mdi-wallet-outline"
              required
            />
            <v-text-field
              v-model="toEmail"
              label="Recipient email"
              type="email"
              prepend-inner-icon="mdi-account-arrow-right-outline"
              hint="Enter the recipient's account email."
              persistent-hint
              required
              class="mb-2"
            />
            <CurrencySelect v-model="toCurrency" label="Recipient currency (optional)" clearable class="mt-4" />
            <v-text-field
              v-model.number="amount"
              label="Amount"
              type="number"
              min="0"
              step="0.01"
              prepend-inner-icon="mdi-cash"
              required
              class="mt-2"
            />

            <v-alert v-if="estimatedAmount" type="info" density="compact" variant="tonal" class="mb-4">
              <v-icon icon="mdi-swap-horizontal" size="small" class="mr-1" />
              Estimated received amount: ~{{ estimatedAmount }} {{ toCurrency }}
              <span class="text-caption d-block">(approximate — final rate is resolved by the server at submission time)</span>
            </v-alert>

            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">{{ errorMessage }}</v-alert>
            <v-alert v-if="successMessage" type="success" density="compact" class="mb-4">{{ successMessage }}</v-alert>

            <v-btn type="submit" color="primary" size="large" prepend-icon="mdi-send" :loading="loading">Send</v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
