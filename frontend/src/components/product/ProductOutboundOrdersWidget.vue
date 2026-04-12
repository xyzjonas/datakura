<template>
  <ForegroundPanel class="flex flex-col flex-1" :flat="flat">
    <div class="mb-2">
      <h2>Objednávky s tímto produktem</h2>
      <span class="text-gray-5"
        >Přijaté objednávky obsahující <strong>{{ productCode }}</strong></span
      >
    </div>
    <SimpleOutboundOrdersTable
      :stock-product-code="productCode"
      hide-search
      class="flex-1"
      :force-grid="forceGrid"
    />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import SimpleOutboundOrdersTable from '@/components/order/SimpleOutboundOrdersTable.vue'

defineProps<{
  productCode: string
  flat?: boolean
  forceGrid?: boolean
}>()
</script>
