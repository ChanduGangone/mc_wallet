<script setup>
import { ref, watch } from 'vue'
import { useStore } from 'vuex'
import CurrencySelect from '@/components/CurrencySelect.vue'
import { formatMoney } from '@/utils/format'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  wallet: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'credited'])

const store = useStore()
const amount = ref(null)
const currency = ref(null)
const errorMessage = ref('')
const loading = ref(false)

watch(
  () => props.wallet,
  (wallet) => {
    if (wallet) currency.value = wallet.currency
  },
)

function close() {
  amount.value = null
  errorMessage.value = ''
  emit('update:modelValue', false)
}

async function handleSubmit() {
  errorMessage.value = ''
  if (!amount.value || amount.value <= 0) {
    errorMessage.value = 'Amount must be greater than 0.'
    return
  }
  loading.value = true
  try {
    const result = await store.dispatch('wallets/creditWallet', {
      walletId: props.wallet.wallet_id,
      amount: amount.value,
      currency: currency.value,
    })
    emit('credited', result)
    close()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not add funds. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="440" @update:model-value="$emit('update:modelValue', $event)">
    <v-card v-if="wallet">
      <v-card-title class="d-flex align-center pa-5">
        <v-icon icon="mdi-cash-plus" color="primary" class="mr-2" />
        Add funds to {{ wallet.currency }} wallet
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-5">
        <p class="text-caption text-medium-emphasis mb-4">
          Current balance: {{ formatMoney(wallet.balance, wallet.currency) }}
        </p>
        <v-text-field
          v-model.number="amount"
          label="Amount"
          type="number"
          min="0"
          step="0.01"
          prepend-inner-icon="mdi-cash"
          autofocus
        />
        <CurrencySelect v-model="currency" label="Currency (converted if different from wallet)" />
        <v-alert v-if="errorMessage" type="error" density="compact">{{ errorMessage }}</v-alert>
      </v-card-text>
      <v-divider />
      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn color="primary" :loading="loading" @click="handleSubmit">Add funds</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
