<template>
  <LargeTabs
    v-model:tab="valuationMode"
    :items="[
      {
        key: 'purchase',
        icon: 'sym_o_sell',
        title: 'Cena při snapshotu',
      },
      {
        key: 'receipt',
        icon: 'sym_o_inventory_2',
        title: 'Cena při příjmu',
      },
    ]"
  />
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import type { InventorySnapshotValuationMode } from '@/views/inventory-snapshot'

const valuationMode = defineModel<InventorySnapshotValuationMode>('mode', {
  required: true,
})
</script>
