<template>
  <ForegroundPanel class="flex flex-col flex-1">
    <div class="mb-2">
      <h2>Historie vydaných objednávek</h2>
      <span class="text-gray-5">Všechny vydané objednávky tomuto dodavateli ve všech stavech</span>
    </div>
    <SimpleInboundOrdersTable :supplier-code="customerCode" include-all class="flex-1" />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import SimpleInboundOrdersTable from '@/components/order/SimpleInboundOrdersTable.vue'

defineProps<{
  customerCode: string
}>()
</script>
