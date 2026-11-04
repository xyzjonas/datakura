<template>
  <div v-if="totals.length" class="flex flex-col">
    <span
      v-for="row in totals"
      :key="row.currency"
      :class="['text-xl font-semibold', toneClass(row.value)]"
    >
      {{ signed && Number(row.value) > 0 ? '+' : '' }}{{ formatMoney(row.value, row.currency) }}
    </span>
  </div>
  <span v-else class="text-xl font-semibold text-muted">{{ emptyLabel }}</span>
</template>

<script setup lang="ts">
import type { InventorySnapshotCurrencyTotal } from '@/client'
import { formatCurrency } from '@/utils/format-number'

const props = withDefaults(
  defineProps<{
    totals: InventorySnapshotCurrencyTotal[]
    /** colour by sign (green positive / red negative) and prefix positives with '+' */
    signed?: boolean
    emptyLabel?: string
  }>(),
  { signed: false, emptyLabel: '—' },
)

const formatMoney = (value: string, currency: string) => formatCurrency(value, currency)

const toneClass = (value: string) => {
  if (!props.signed) {
    return 'text-primary'
  }
  const amount = Number(value)
  if (amount > 0) return 'text-positive'
  if (amount < 0) return 'text-negative'
  return ''
}
</script>
