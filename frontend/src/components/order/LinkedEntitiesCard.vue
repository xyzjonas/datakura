<template>
  <div class="flex flex-col gap-2 min-w-80">
    <ForegroundPanel v-if="showWarehouseOrder" class="flex-1 flex justify-center items-center">
      <InboundWarehouseOrderBadge v-if="warehouseOrder" :order="warehouseOrder" />
      <span v-else class="text-gray-5">Žádná Příjemka</span>
    </ForegroundPanel>
    <ForegroundPanel v-if="showInboundOrder" class="flex-1 flex justify-center items-center">
      <InboundOrderBadge v-if="inboundOrder" :order="inboundOrder" />
      <span v-else class="text-gray-5">Žádná Příchozí Objednávka</span>
    </ForegroundPanel>
    <ForegroundPanel v-if="showInvoice" class="flex-1 flex justify-center items-center">
      <span v-if="invoice">FAKTURA #123</span>
      <span class="text-gray-5">Žádná Faktura</span>
    </ForegroundPanel>
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
import CreditNoteBadge from '../credit/CreditNoteBadge.vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import InboundWarehouseOrderBadge from '../putaway/InboundWarehouseOrderBadge.vue'
import type { Optional } from '@/utils/optional'
import InboundOrderBadge from './InboundOrderBadge.vue'

defineProps<{
  showCreditNote?: boolean
  creditNote?: Optional<CreditNoteBaseSchema>
  showWarehouseOrder?: boolean
  warehouseOrder?: Optional<InboundWarehouseOrderBaseSchema>
  showInboundOrder?: boolean
  inboundOrder?: InboundOrderSchema
  showInvoice?: boolean
  invoice?: unknown
}>()
</script>

<style lang="scss" scoped></style>
