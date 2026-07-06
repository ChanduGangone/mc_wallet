<script setup>
import { computed } from 'vue'
import { currencyFlag, formatMoney } from '@/utils/format'

const props = defineProps({
  wallet: { type: Object, required: true },
})
defineEmits(['add-funds'])

const formattedBalance = computed(() => formatMoney(props.wallet.balance, props.wallet.currency))
</script>

<template>
  <v-card class="wallet-card" rounded="xl">
    <v-card-text class="pa-5 pb-3">
      <v-chip color="primary" variant="tonal" size="small" class="font-weight-medium mb-3">
        {{ currencyFlag(wallet.currency) }}&nbsp;{{ wallet.currency }}
      </v-chip>
      <div class="text-h4 font-weight-bold">{{ formattedBalance }}</div>
      <div class="text-caption text-medium-emphasis mt-1">Available balance</div>
    </v-card-text>
    <v-card-actions class="px-5 pb-4 pt-0">
      <v-btn
        color="primary"
        variant="tonal"
        size="small"
        prepend-icon="mdi-plus-circle-outline"
        @click="$emit('add-funds', wallet)"
      >
        Add funds
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.wallet-card {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.wallet-card:hover {
  transform: translateY(-2px);
}
</style>
