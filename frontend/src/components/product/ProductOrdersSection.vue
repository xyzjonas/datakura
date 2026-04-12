<template>
  <ForegroundPanel class="flex flex-col gap-2">
    <LargeTabs v-model:tab="activeOrdersTab" :items="orderTabs" flat />
    <q-separator />
    <ProductInboundOrdersWidget
      v-if="activeOrdersTab === 'inbound'"
      :product-code="productCode"
      class="min-w-[340px] flex-1"
      flat
      :force-grid="forceGrid"
    />
    <ProductOutboundOrdersWidget
      v-else
      :product-code="productCode"
      class="min-w-[340px] flex-1"
      flat
      :force-grid="forceGrid"
    />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LargeTabs from '@/components/LargeTabs.vue'
import { ref } from 'vue'
import ProductInboundOrdersWidget from './ProductInboundOrdersWidget.vue'
import ProductOutboundOrdersWidget from './ProductOutboundOrdersWidget.vue'

defineProps<{
  productCode: string
  forceGrid?: boolean
}>()

const activeOrdersTab = ref('outbound')

const orderTabs = [
  { key: 'outbound', icon: 'sym_o_call_made', title: 'Přijaté Objednávky' },
  { key: 'inbound', icon: 'sym_o_call_received', title: 'Vydané Objednávky' },
]
</script>
