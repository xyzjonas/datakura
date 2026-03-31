<template>
  <div class="flex flex-col gap-2 min-w-80">
    <template v-if="showWarehouseOrder">
      <ForegroundPanel
        v-for="order in warehouseOrdersToRender"
        :key="order.code"
        class="flex-1 flex justify-center items-center"
      >
        <InboundWarehouseOrderBadge :order="order" />
      </ForegroundPanel>
      <ForegroundPanel
        v-if="warehouseOrdersToRender.length === 0"
        class="flex-1 flex justify-center items-center"
      >
        <span class="text-gray-5">Žádná Příjemka</span>
      </ForegroundPanel>
    </template>

    <ForegroundPanel
      v-if="showParentWarehouseOrder"
      class="flex-1 flex flex-col justify-center items-center gap-2"
    >
      <InboundWarehouseOrderBadge
        v-if="parentWarehouseOrder"
        :order="parentWarehouseOrder"
        label="Nadřazená příjemka"
      />
      <span v-else class="text-gray-5">Žádná nadřazená příjemka</span>
    </ForegroundPanel>

    <template v-if="showChildWarehouseOrders">
      <ForegroundPanel
        v-for="order in childWarehouseOrdersToRender"
        :key="`child-${order.code}`"
        class="flex-1 flex flex-col justify-center items-center gap-2"
      >
        <InboundWarehouseOrderBadge :order="order" label="Podřízená příjemka" />
      </ForegroundPanel>
      <ForegroundPanel
        v-if="childWarehouseOrdersToRender.length === 0"
        class="flex-1 flex justify-center items-center"
      >
        <span class="text-gray-5">Žádné podřízené příjemky</span>
      </ForegroundPanel>
    </template>

    <ForegroundPanel v-if="showInboundOrder" class="flex-1 flex justify-center items-center">
      <InboundOrderBadge v-if="inboundOrder" :order="inboundOrder" />
      <span v-else class="text-gray-5">Žádná Příchozí Objednávka</span>
    </ForegroundPanel>
    <MissingMarker v-if="showInvoice">
      <ForegroundPanel v-if="showInvoice" class="flex-1 flex justify-center items-center">
        <span v-if="invoice">FAKTURA #123</span>
        <span class="text-gray-5">Žádná Faktura</span>
      </ForegroundPanel>
    </MissingMarker>
    <ForegroundPanel v-if="showCreditNote" class="flex-1 flex justify-center items-center">
      <CreditNoteBadge v-if="creditNote" :note="creditNote" />
      <span v-else class="text-gray-5">Žádný Dopbropis</span>
    </ForegroundPanel>
  </div>
</template>

<script setup lang="ts">
import type {
  CreditNoteBaseSchema,
  InboundOrderSchema,
  InboundWarehouseOrderBaseSchema,
} from '@/client'
import { computed } from 'vue'
import CreditNoteBadge from '../credit/CreditNoteBadge.vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import InboundWarehouseOrderBadge from '../putaway/InboundWarehouseOrderBadge.vue'
import type { Optional } from '@/utils/optional'
import InboundOrderBadge from './InboundOrderBadge.vue'
import MissingMarker from '../MissingMarker.vue'

const props = defineProps<{
  showCreditNote?: boolean
  creditNote?: Optional<CreditNoteBaseSchema>
  showWarehouseOrder?: boolean
  warehouseOrder?: Optional<InboundWarehouseOrderBaseSchema>
  warehouseOrders?: Optional<InboundWarehouseOrderBaseSchema[]>
  showParentWarehouseOrder?: boolean
  parentWarehouseOrder?: Optional<InboundWarehouseOrderBaseSchema>
  showChildWarehouseOrders?: boolean
  childWarehouseOrders?: Optional<InboundWarehouseOrderBaseSchema[]>
  showInboundOrder?: boolean
  inboundOrder?: InboundOrderSchema
  showInvoice?: boolean
  invoice?: unknown
}>()

const warehouseOrdersToRender = computed(() => {
  if (props.warehouseOrders && props.warehouseOrders.length > 0) {
    return props.warehouseOrders
  }
  return props.warehouseOrder ? [props.warehouseOrder] : []
})

const childWarehouseOrdersToRender = computed(() => props.childWarehouseOrders ?? [])
</script>

<style lang="scss" scoped></style>
