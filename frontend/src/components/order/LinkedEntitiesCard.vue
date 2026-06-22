<template>
  <ForegroundPanel class="flex flex-col gap-2 min-w-80">
    <template #header>
      <span class="text-xs text-muted">SOUVISEJÍCÍ DOKLADY</span>
    </template>

    <template v-if="showInboundOrder">
      <h3 class="text-xs uppercase mb-1">
        {{ inboundOrder?.type === 'Manufacturing' ? 'Výrobní' : 'Vydaná' }} objednávka
      </h3>
      <div v-if="inboundOrder" class="flex items-center justify-between">
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_receipt" color="primary" />
          <router-link
            v-if="inboundOrder.type === 'Inbound'"
            :to="{ name: 'inboundOrderDetail', params: { code: inboundOrder.code } }"
            class="link"
            >{{ inboundOrder.code }}</router-link
          >
          <router-link
            v-else-if="inboundOrder.type === 'Manufacturing'"
            :to="{ name: 'manufacturingOrderDetail', params: { code: inboundOrder.code } }"
            class="link"
            >{{ inboundOrder.code }}</router-link
          >
        </span>
        <ManufacturingOrderStateBadge
          :state="inboundOrder.state"
          v-if="inboundOrder.type === 'Manufacturing'"
        />
        <InboundOrderStateBadge :state="inboundOrder.state" v-else />
      </div>
      <span v-else class="text-gray-5">Žádná Příchozí Objednávka</span>
    </template>

    <template v-if="showOutboundOrder">
      <h3 class="text-xs uppercase mb-1">
        {{ outboundOrder?.type === 'Manufacturing' ? 'Výrobní' : 'Přijatá' }} objednávka
      </h3>
      <div
        v-if="outboundOrder"
        :key="outboundOrder.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_receipt" size="16px" color="primary" />
          <router-link
            v-if="outboundOrder.type === 'Outbound'"
            :to="{ name: 'outboundOrderDetail', params: { code: outboundOrder.code } }"
            class="link"
            >{{ outboundOrder.code }}</router-link
          >
          <router-link
            v-else-if="outboundOrder.type === 'Manufacturing'"
            :to="{ name: 'manufacturingOrderDetail', params: { code: outboundOrder.code } }"
            class="link"
            >{{ outboundOrder.code }}</router-link
          >
        </span>
        <OutboundOrderStateBadge :state="outboundOrder.state" />
      </div>
      <span v-else class="text-gray-5">Žádná objednávka</span>
    </template>

    <template v-if="showInboundWarehouseOrders">
      <q-separator v-if="showInboundOrder || showOutboundOrder" class="my-2" />
      <h3 class="text-xs uppercase mb-1">Příjemky</h3>
      <div
        v-for="order in inboundWarehouseOrdersToRender"
        :key="order.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_output" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderIn(order.code)">{{ order.code }}</a>
        </span>
        <InboundWarehouseOrderStateBadge :state="order.state"></InboundWarehouseOrderStateBadge>
      </div>
      <span v-if="inboundWarehouseOrdersToRender.length === 0" class="text-gray-5"
        >Žádná Příjemka</span
      >
    </template>

    <template v-if="showParentInboundWarehouseOrder">
      <q-separator
        v-if="showInboundWarehouseOrders || showInboundOrder || showOutboundOrder"
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Nadřazená příjemka</h3>
      <div
        v-if="parentInboundWarehouseOrder"
        :key="parentInboundWarehouseOrder.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_input" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderIn(parentInboundWarehouseOrder.code)">{{
            parentInboundWarehouseOrder.code
          }}</a>
        </span>
        <InboundWarehouseOrderStateBadge
          :state="parentInboundWarehouseOrder.state"
        ></InboundWarehouseOrderStateBadge>
      </div>
      <span v-else class="text-gray-5">Žádná nadřazená příjemka</span>
    </template>

    <template v-if="showChildInboundWarehouseOrders">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showInboundOrder ||
          showOutboundOrder
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Podřízené příjemky</h3>
      <div
        v-for="order in childInboundWarehouseOrdersToRender"
        :key="order.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_input" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderIn(order.code)">{{ order.code }}</a>
        </span>
        <InboundWarehouseOrderStateBadge :state="order.state"></InboundWarehouseOrderStateBadge>
      </div>
      <span v-if="childInboundWarehouseOrdersToRender.length === 0" class="text-gray-5"
        >Žádné podřízené příjemky</span
      >
    </template>

    <template v-if="showOutboundWarehouseOrders">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showChildInboundWarehouseOrders ||
          showInboundOrder ||
          showOutboundOrder
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Výdejky</h3>
      <div
        v-for="order in outboundWarehouseOrdersToRender"
        :key="order.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_output" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderOut(order.code)">{{ order.code }}</a>
        </span>
        <OutboundWarehouseOrderStateBadge :state="order.state" />
      </div>
      <span v-if="outboundWarehouseOrdersToRender.length === 0" class="text-gray-5"
        >Žádná Výdejka</span
      >
    </template>

    <template v-if="showParentOutboundWarehouseOrder">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showChildInboundWarehouseOrders ||
          showOutboundWarehouseOrders ||
          showInboundOrder ||
          showOutboundOrder
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Nadřazená výdejka</h3>
      <div
        v-if="parentOutboundWarehouseOrder"
        :key="parentOutboundWarehouseOrder.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_output" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderOut(parentOutboundWarehouseOrder.code)">{{
            parentOutboundWarehouseOrder.code
          }}</a>
        </span>
        <OutboundWarehouseOrderStateBadge :state="parentOutboundWarehouseOrder.state" />
      </div>
      <span v-else class="text-gray-5">Žádná nadřazená výdejka</span>
    </template>

    <template v-if="showChildOutboundWarehouseOrders">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showChildInboundWarehouseOrders ||
          showOutboundWarehouseOrders ||
          showParentOutboundWarehouseOrder ||
          showInboundOrder ||
          showOutboundOrder
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Podřízené výdejky</h3>
      <div
        v-for="order in childOutboundWarehouseOrdersToRender"
        :key="order.code"
        class="flex items-center justify-between py-1"
      >
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_output" size="16px" color="primary" />
          <a class="link" @click="goToWarehouseOrderOut(order.code)">{{ order.code }}</a>
        </span>
        <OutboundWarehouseOrderStateBadge :state="order.state" />
      </div>
      <span v-if="childOutboundWarehouseOrdersToRender.length === 0" class="text-gray-5"
        >Žádné podřízené výdejky</span
      >
    </template>

    <template v-if="showInvoice">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showChildInboundWarehouseOrders ||
          showOutboundWarehouseOrders ||
          showParentOutboundWarehouseOrder ||
          showChildOutboundWarehouseOrders ||
          showInboundOrder ||
          showOutboundOrder
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Faktura</h3>
      <div v-if="invoice" class="flex items-center justify-between">
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_receipt_long" size="16px" color="primary" />
          <a class="link" @click="goToInvoice(invoice.code)">{{ invoice.code }}</a>
        </span>
        <span class="text-xs font-600" :class="invoice.paid_date ? 'text-green-600' : 'text-muted'">
          {{ invoice.paid_date ? 'Zaplaceno' : 'Nezaplaceno' }}
        </span>
      </div>
      <span v-else class="text-gray-5">Žádná Faktura</span>
    </template>

    <template v-if="showCreditNote">
      <q-separator
        v-if="
          showInboundWarehouseOrders ||
          showParentInboundWarehouseOrder ||
          showChildInboundWarehouseOrders ||
          showOutboundWarehouseOrders ||
          showParentOutboundWarehouseOrder ||
          showChildOutboundWarehouseOrders ||
          showInboundOrder ||
          showOutboundOrder ||
          showInvoice
        "
        class="my-2"
      />
      <h3 class="text-xs uppercase mb-1">Dobropis</h3>
      <div v-if="creditNote" class="flex items-center justify-between">
        <span class="flex items-center gap-1">
          <q-icon name="sym_o_receipt_long" size="16px" color="primary" />
          <a class="link" @click="goToCreditNote(creditNote.code)">{{ creditNote.code }}</a>
        </span>
        <GenericStateBadge :state="creditNote.state" />
      </div>
      <span v-else class="text-gray-5">Žádný Dobropis</span>
    </template>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type {
  BaseOrder,
  CreditNoteBaseSchema,
  InboundWarehouseOrderBaseSchema,
  InvoiceSchema,
  OutboundWarehouseOrderBaseSchema,
} from '@/client'
import { useAppRouter } from '@/composables/use-app-router'
import type { Optional } from '@/utils/optional'
import { computed } from 'vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import GenericStateBadge from '../GenericStateBadge.vue'
import ManufacturingOrderStateBadge from '../manufacturing/ManufacturingOrderStateBadge.vue'
import InboundWarehouseOrderStateBadge from '../putaway/InboundWarehouseOrderStateBadge.vue'
import OutboundWarehouseOrderStateBadge from '../putaway/OutboundWarehouseOrderStateBadge.vue'
import InboundOrderStateBadge from './InboundOrderStateBadge.vue'
import OutboundOrderStateBadge from './OutboundOrderStateBadge.vue'

const props = defineProps<{
  showInboundWarehouseOrders?: boolean
  inboundWarehouseOrder?: Optional<InboundWarehouseOrderBaseSchema>
  inboundWarehouseOrders?: Optional<InboundWarehouseOrderBaseSchema[]>
  showParentInboundWarehouseOrder?: boolean
  parentInboundWarehouseOrder?: Optional<InboundWarehouseOrderBaseSchema>
  showChildInboundWarehouseOrders?: boolean
  childInboundWarehouseOrders?: Optional<InboundWarehouseOrderBaseSchema[]>
  showOutboundWarehouseOrders?: boolean
  outboundWarehouseOrders?: Optional<OutboundWarehouseOrderBaseSchema[]>
  showParentOutboundWarehouseOrder?: boolean
  parentOutboundWarehouseOrder?: Optional<OutboundWarehouseOrderBaseSchema>
  showChildOutboundWarehouseOrders?: boolean
  childOutboundWarehouseOrders?: Optional<OutboundWarehouseOrderBaseSchema[]>
  showInboundOrder?: boolean
  inboundOrder?: BaseOrder | null
  showOutboundOrder?: boolean
  outboundOrder?: BaseOrder | null
  showInvoice?: boolean
  invoice?: InvoiceSchema | null
  showCreditNote?: boolean
  creditNote?: Optional<CreditNoteBaseSchema>
}>()

const { goToInvoice, goToWarehouseOrderOut, goToWarehouseOrderIn, goToCreditNote } = useAppRouter()

const inboundWarehouseOrdersToRender = computed(() => {
  if (props.inboundWarehouseOrders && props.inboundWarehouseOrders.length > 0) {
    return props.inboundWarehouseOrders
  }
  return props.inboundWarehouseOrder ? [props.inboundWarehouseOrder] : []
})

const childInboundWarehouseOrdersToRender = computed(() => props.childInboundWarehouseOrders ?? [])
const outboundWarehouseOrdersToRender = computed(() => props.outboundWarehouseOrders ?? [])
const childOutboundWarehouseOrdersToRender = computed(
  () => props.childOutboundWarehouseOrders ?? [],
)
</script>
