<template>
  <div class="flex flex-col gap-2 min-w-80">
    <template v-if="showWarehouseOrders">
      <ForegroundPanel
        v-for="order in warehouseOrdersToRender"
        :key="order.code"
        class="flex-1 flex justify-center items-center"
      >
        <OutboundWarehouseOrderBadge :order="order" />
      </ForegroundPanel>
      <ForegroundPanel
        v-if="warehouseOrdersToRender.length === 0"
        class="flex-1 flex justify-center items-center"
      >
        <span class="text-gray-5">Žádná Výdejka</span>
      </ForegroundPanel>
    </template>

    <ForegroundPanel v-if="showInvoice" class="flex-1 flex justify-center items-center">
      <div v-if="invoice" class="flex flex-col">
        <span class="text-gray-5 text-2xs uppercase">Faktura</span>
        <button class="link text-left" @click="goToInvoice(invoice.code)">
          {{ invoice.code }}
        </button>
      </div>
      <span v-else class="text-gray-5">Žádná Faktura</span>
    </ForegroundPanel>
  </div>
</template>

<script setup lang="ts">
import type { InvoiceSchema, OutboundWarehouseOrderBaseSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import type { Optional } from '@/utils/optional'
import { computed } from 'vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import OutboundWarehouseOrderBadge from '../putaway/OutboundWarehouseOrderBadge.vue'

const props = defineProps<{
  showWarehouseOrders?: boolean
  warehouseOrders?: Optional<OutboundWarehouseOrderBaseSchema[]>
  showInvoice?: boolean
  invoice?: InvoiceSchema | null
}>()

const warehouseOrdersToRender = computed(() => props.warehouseOrders ?? [])
const { goToInvoice } = useAppRouter()
</script>
