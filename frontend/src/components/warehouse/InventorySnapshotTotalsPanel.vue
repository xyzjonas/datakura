<template>
  <ForegroundPanel class="flex min-w-[12rem] flex-col gap-3 justify-between">
    <div>
      <div class="text-xs uppercase tracking-wide text-muted">{{ title }}</div>
      <div v-if="caption" class="mt-1 text-sm">{{ caption }}</div>
    </div>

    <div v-if="totals.length" class="flex flex-col gap-2">
      <div v-for="row in totals" :key="row.currency" class="flex items-end justify-between gap-3">
        <span class="text-sm uppercase tracking-[0.12em] text-gray-5">{{ row.currency }}</span>
        <span class="text-lg font-semibold text-primary">{{ formatMoney(row.value) }}</span>
      </div>
    </div>

    <div v-else class="text-sm text-muted">{{ emptyLabel }}</div>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { InventorySnapshotCurrencyTotal } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { formatMoney } from '@/views/inventory-snapshot'

withDefaults(
  defineProps<{
    title: string
    totals: InventorySnapshotCurrencyTotal[]
    caption?: string
    emptyLabel?: string
  }>(),
  {
    caption: undefined,
    emptyLabel: 'Žádné hodnoty',
  },
)
</script>
