<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useStore } from 'vuex'
import CurrencySelect from '@/components/CurrencySelect.vue'
import {
  formatDateTime,
  formatMoney,
  TRANSACTION_TYPE_COLORS,
  TRANSACTION_STATUS_COLORS,
} from '@/utils/format'

const store = useStore()
const transactions = computed(() => store.state.wallets.transactions)
const meta = computed(() => store.state.wallets.transactionsMeta)

const typeFilter = ref(null)
const currencyFilter = ref(null)
const startDate = ref('')
const endDate = ref('')
const page = ref(1)
const loading = ref(false)

const headers = [
  { title: 'Date', key: 'created_at' },
  { title: 'Type', key: 'type' },
  { title: 'Amount', key: 'amount' },
  { title: 'Converted', key: 'converted_amount' },
  { title: 'Status', key: 'status' },
]

const pageCount = computed(() => Math.max(1, Math.ceil(meta.value.total / meta.value.limit)))

async function loadTransactions() {
  loading.value = true
  try {
    await store.dispatch('wallets/fetchTransactions', {
      type: typeFilter.value || undefined,
      currency: currencyFilter.value || undefined,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      limit: 20,
      offset: (page.value - 1) * 20,
    })
  } finally {
    loading.value = false
  }
}

watch([typeFilter, currencyFilter, startDate, endDate], () => {
  page.value = 1
  loadTransactions()
})
watch(page, loadTransactions)

onMounted(loadTransactions)
</script>

<template>
  <div class="mb-6">
    <h1 class="text-h5 font-weight-bold">Transaction history</h1>
    <p class="text-medium-emphasis">{{ meta.total }} transaction{{ meta.total === 1 ? '' : 's' }} across your wallets</p>
  </div>

  <v-card class="mb-4">
    <v-card-text class="pb-0">
      <v-row>
        <v-col cols="12" sm="3">
          <v-select v-model="typeFilter" :items="['credit', 'debit', 'transfer']" label="Type" prepend-inner-icon="mdi-filter-variant" clearable />
        </v-col>
        <v-col cols="12" sm="3">
          <CurrencySelect v-model="currencyFilter" label="Currency" clearable />
        </v-col>
        <v-col cols="12" sm="3">
          <v-text-field v-model="startDate" label="Start date" type="date" prepend-inner-icon="mdi-calendar-start" />
        </v-col>
        <v-col cols="12" sm="3">
          <v-text-field v-model="endDate" label="End date" type="date" prepend-inner-icon="mdi-calendar-end" />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>

  <v-card>
    <v-data-table
      :headers="headers"
      :items="transactions"
      :loading="loading"
      item-value="transaction_id"
      hide-default-footer
      :items-per-page="-1"
    >
      <template #item.created_at="{ item }">
        {{ formatDateTime(item.created_at) }}
      </template>
      <template #item.type="{ item }">
        <v-chip :color="TRANSACTION_TYPE_COLORS[item.type]" size="small" variant="tonal">
          {{ item.type }}
        </v-chip>
      </template>
      <template #item.amount="{ item }">
        {{ formatMoney(item.amount, item.from_currency) }}
      </template>
      <template #item.converted_amount="{ item }">
        <span v-if="item.converted_amount">{{ formatMoney(item.converted_amount, item.to_currency) }}</span>
        <span v-else class="text-medium-emphasis">—</span>
      </template>
      <template #item.status="{ item }">
        <v-chip :color="TRANSACTION_STATUS_COLORS[item.status]" size="small" variant="tonal">
          {{ item.status }}
        </v-chip>
      </template>
      <template #no-data>
        <div class="py-8 text-center text-medium-emphasis">No transactions found.</div>
      </template>
    </v-data-table>
  </v-card>

  <div class="d-flex justify-center mt-4">
    <v-pagination v-model="page" :length="pageCount" />
  </div>
</template>
