<script setup>
import { ref, onMounted, computed } from 'vue'
import { useStore } from 'vuex'
import WalletCard from '@/components/WalletCard.vue'
import AddFundsDialog from '@/components/AddFundsDialog.vue'
import { formatMoney } from '@/utils/format'

const store = useStore()
const wallets = computed(() => store.state.wallets.wallets)

const dialogOpen = ref(false)
const selectedWallet = ref(null)
const snackbar = ref('')

function openAddFunds(wallet) {
  selectedWallet.value = wallet
  dialogOpen.value = true
}

function onCredited(result) {
  const converted = result.converted_amount
  const balanceText = formatMoney(result.new_balance, selectedWallet.value?.currency)
  snackbar.value = `New balance: ${balanceText}` + (converted ? ` (credited ${converted})` : '')
}

onMounted(() => {
  store.dispatch('wallets/fetchWallets')
})
</script>

<template>
  <div class="d-flex align-center justify-space-between mb-6">
    <div>
      <h1 class="text-h5 font-weight-bold">Your wallets</h1>
      <p class="text-medium-emphasis">Balances across all your currencies</p>
    </div>
  </div>

  <v-alert v-if="wallets.length === 0" type="info" variant="tonal">No wallets yet.</v-alert>
  <v-row>
    <v-col v-for="wallet in wallets" :key="wallet.wallet_id" cols="12" sm="6" md="4">
      <WalletCard :wallet="wallet" @add-funds="openAddFunds" />
    </v-col>
  </v-row>

  <AddFundsDialog v-model="dialogOpen" :wallet="selectedWallet" @credited="onCredited" />

  <v-snackbar :model-value="!!snackbar" @update:model-value="snackbar = ''" timeout="4000" color="success">
    {{ snackbar }}
  </v-snackbar>
</template>
