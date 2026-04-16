<template>
  <div class="flex flex-col gap-2 min-w-80 flex-1">
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
    <ForegroundPanel v-if="showInvoice" class="flex-1 flex justify-center items-center">
      <div v-if="invoice" class="flex flex-col">
        <span class="text-gray-5 text-2xs uppercase">Faktura</span>
        <div class="flex items-center gap-2">
          <a
            v-if="invoice.document?.url"
            class="link"
            :href="invoice.document.url"
            target="_blank"
            rel="noopener noreferrer"
            >{{ invoice.code }}</a
          >
          <span v-else class="text-gray-5 font-bold">{{ invoice.code }}</span>
          <q-btn
            v-if="showInvoiceEdit"
            dense
            flat
            round
            size="sm"
            icon="edit"
            color="primary"
            @click="emit('edit-invoice')"
          >
            <q-tooltip :offset="[0, 10]">Upravit fakturu</q-tooltip>
          </q-btn>
        </div>
      </div>
      <span v-else class="text-gray-5">Žádná Faktura</span>
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
  InvoiceSchema,
} from '@/client'
import type { Optional } from '@/utils/optional'
import { computed } from 'vue'
import CreditNoteBadge from '../credit/CreditNoteBadge.vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import InboundWarehouseOrderBadge from '../putaway/InboundWarehouseOrderBadge.vue'
import InboundOrderBadge from './InboundOrderBadge.vue'

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
  invoice?: InvoiceSchema | null
  showInvoiceEdit?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit-invoice'): void
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
