<template>
  <div class="flex flex-col gap-2">
    <q-btn-toggle
      v-model="valuationMode"
      unelevated
      no-caps
      toggle-color="primary"
      :options="[
        { label: 'Cena při uložení', value: 'purchase', icon: 'sym_o_sell' },
        { label: 'Cena při příjmu', value: 'receipt', icon: 'sym_o_inventory_2' },
      ]"
      class="self-start border"
    />
    <div class="text-sm text-gray-6">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { InventorySnapshotValuationMode } from '@/views/inventory-snapshot'

const valuationMode = defineModel<InventorySnapshotValuationMode>('mode', { required: true })

const hint = computed(() =>
  valuationMode.value === 'purchase'
    ? 'Položky jsou oceněny aktuální nákupní cenou skladové karty v okamžiku uložení stavu skladu.'
    : 'Položky jsou oceněny historickou cenou z příjmové řádky, za kterou byly původně naskladněny. Položky bez příjmové řádky oceněny nejsou.',
)
</script>
