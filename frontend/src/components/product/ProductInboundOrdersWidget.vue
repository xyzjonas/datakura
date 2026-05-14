<template>
  <ForegroundPanel no-padding class="flex flex-col flex-1" :flat="flat">
    <div class="mb-2">
      <h2>Objednávky s tímto produktem</h2>
      <span class="text-gray-5"
        >Vydané objednávky obsahující <strong>{{ productCode }}</strong></span
      >
    </div>
    <SimpleInboundOrdersTable
      :stock-product-code="productCode"
      hide-search
      class="flex-1"
      :force-grid="forceGrid"
    />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import SimpleInboundOrdersTable from '@/components/order/SimpleInboundOrdersTable.vue'

defineProps<{
  productCode: string
  flat?: boolean
  forceGrid?: boolean
}>()
</script>
