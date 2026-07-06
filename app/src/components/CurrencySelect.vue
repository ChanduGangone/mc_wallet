<script setup>
import { SUPPORTED_CURRENCIES } from '@/constants/currencies'

defineProps({
  modelValue: { type: String, default: null },
  label: { type: String, default: 'Currency' },
  clearable: { type: Boolean, default: false },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <v-select
    :model-value="modelValue"
    :items="SUPPORTED_CURRENCIES"
    :label="label"
    :clearable="clearable"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>
