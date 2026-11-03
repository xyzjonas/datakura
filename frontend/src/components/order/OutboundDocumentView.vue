<template>
  <div v-if="order" class="w-full flex flex-col gap-5">
    <div class="flex justify-between">
      <q-breadcrumbs class="mb-5">
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el
          v-if="isCalculation"
          label="Kalkulace"
          :to="{ name: 'outboundCalculations' }"
        />
        <q-breadcrumbs-el
          v-else
          label="Přijaté Objednávky"
          :to="{ name: 'orders', query: { tab: 'outbound' } }"
        />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <q-btn flat dense color="primary" icon="sym_o_query_stats" @click="auditDialog = true">
        <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
      </q-btn>
    </div>

    <div class="mb-2 flex justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">{{
            isCalculation ? 'KALKULACE' : 'PŘIJATÁ OBJEDNÁVKA'
          }}</span>
          <h1 class="h1 mb-1">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
          <router-link
            v-if="linkedCalculationCode"
            :to="{ name: 'outboundCalculationDetail', params: { code: linkedCalculationCode } }"
            class="link text-sm flex items-center gap-1"
            data-test="calculation-code"
          >
            <q-icon name="sym_o_calculate" />
            Kalkulace {{ linkedCalculationCode }}
          </router-link>
          <router-link
            v-if="linkedOrderCode"
            :to="{ name: 'outboundOrderDetail', params: { code: linkedOrderCode } }"
            class="link text-sm flex items-center gap-1"
            data-test="order-code"
          >
            <q-icon name="sym_o_receipt" />
            Objednávka {{ linkedOrderCode }}
          </router-link>
        </div>
        <OutboundOrderStateBadge :state="order.state" />
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="isEditable"
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          @click="editOrderDialog = true"
        ></q-btn>
        <OutboundCalculationActions
          v-if="calculation"
          v-model:calculation="calculation"
          :editable="isEditable"
        />
        <OutboundOrderActions
          v-else-if="orderDocument"
          v-model:order="orderDocument"
          :editable="isEditable"
        />
        <q-btn
          unelevated
          color="secondary"
          icon="sym_o_content_copy"
          label="duplikovat"
          :loading="duplicating"
          @click="duplicateOrder"
        />
      </div>
    </div>

    <div class="flex gap-5">
      <OutboundOrderDetailsListCard :order="order" class="flex-[2]" />
      <CustomerCard
        :customer="order.customer"
        v-model:contact="contact"
        :editable-contact="isEditable"
        title="ODBĚRATEL"
        class="flex-1"
      />
      <LinkedEntitiesCard
        v-if="orderDocument"
        show-outbound-warehouse-orders
        :outbound-warehouse-orders="orderDocument.warehouse_orders"
        show-invoice
        :invoice="orderDocument.invoice"
        class="flex-1"
      />
    </div>

    <CommentCard v-if="order.note">{{ order.note }}</CommentCard>

    <OutboundOrderTimeline v-if="orderDocument" :order="orderDocument" />

    <div class="border rounded shadow-md mb-5">
      <div class="flex items-center justify-between p-4">
        <div>
          <h2>{{ isCalculation ? 'Položky kalkulace' : 'Položky objednávky' }}</h2>
        </div>
        <q-btn
          unelevated
          color="primary"
          icon="sym_o_add"
          label="přidat položku"
          :disable="!isEditable"
          @click="addItemDialog = true"
        ></q-btn>
      </div>
      <q-separator />
      <OrderTotalsHeader :order="order" />
    </div>

    <OutboundOrderProductsList
      v-model:items="order.items"
      :currency="order.currency"
      :readonly="!isEditable"
      :order-code="order.code"
      :customer-code="order.customer.code"
      @remove-item="removeItem"
      @reorder-item="reorderItem"
      @add-item="addItemDialog = true"
    />

    <NewOutboundOrderItemDialog
      ref="addItemDialogComponent"
      v-model:show="addItemDialog"
      @add-item="addItem"
      :currency="order.currency"
      :customer-code="order.customer.code"
    />

    <OutboundOrderUpdateOrCreateDialog
      v-model:show="editOrderDialog"
      :order-out="order"
      submit-label="uložit"
      :title="isCalculation ? 'Upravit kalkulaci' : 'Upravit objednávku'"
      @create-order="updateOrder"
    />

    <AuditLogDialog
      v-model:show="auditDialog"
      :source="isCalculation ? 'outbound-calculation' : 'outbound-order'"
      :code="order.code"
      :title="isCalculation ? 'Historie změn kalkulace' : 'Historie změn objednávky'"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">
      {{ isCalculation ? 'KALKULACE NENALEZENA' : 'OBJEDNÁVKA NENALEZENA' }}
    </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type {
  OutboundCalculationCreateOrUpdateSchema,
  OutboundCalculationSchema,
  OutboundOrderItemCreateSchema,
  OutboundOrderSchema,
} from '@/client'
import CommentCard from '@/components/CommentCard.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import NewOutboundOrderItemDialog from '@/components/order/NewOutboundOrderItemDialog.vue'
import OrderTotalsHeader from '@/components/order/OrderTotalsHeader.vue'
import OutboundCalculationActions from '@/components/order/OutboundCalculationActions.vue'
import OutboundOrderActions from '@/components/order/OutboundOrderActions.vue'
import OutboundOrderDetailsListCard from '@/components/order/OutboundOrderDetailsListCard.vue'
import OutboundOrderProductsList from '@/components/order/OutboundOrderProductsList.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import OutboundOrderTimeline from '@/components/order/OutboundOrderTimeline.vue'
import OutboundOrderUpdateOrCreateDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import {
  provideOutboundDocumentKind,
  useOutboundDocumentApi,
  type OutboundDocument,
  type OutboundDocumentKind,
} from '@/composables/use-outbound-document-api'
import { contactFullName } from '@/utils/contact-name'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'

/**
 * Detail of an outbound order or calculation. They are 1:1 the same page, only
 * calculations have no timeline, warehouse orders nor invoice and different actions.
 */
const props = defineProps<{ code: string; kind: OutboundDocumentKind }>()
const order = ref<OutboundDocument>()

const $q = useQuasar()
const { onResponse } = useApi()
const api = useOutboundDocumentApi(() => props.kind)
provideOutboundDocumentKind(props.kind)
const isCalculation = computed(() => props.kind === 'calculation')

// kind specific views of the very same ref
const calculation = computed<OutboundCalculationSchema | undefined>({
  get: () => (isCalculation.value ? (order.value as OutboundCalculationSchema) : undefined),
  set: (value) => (order.value = value),
})
const orderDocument = computed<OutboundOrderSchema | undefined>({
  get: () => (isCalculation.value ? undefined : (order.value as OutboundOrderSchema)),
  set: (value) => (order.value = value),
})
const linkedCalculationCode = computed(() => orderDocument.value?.calculation_code)
const linkedOrderCode = computed(() => calculation.value?.order_code)

const response = await api.get(props.code)
const data = onResponse(response)
if (data) {
  order.value = data.data
}

const FINISHED_ORDER_STATES = [
  'cancelled',
  'completed',
  'invoiced',
  'waiting_for_payment',
  'completed_paid',
]
const isEditable = computed(() => {
  if (!order.value) {
    return false
  }
  return isCalculation.value
    ? order.value.state === 'open'
    : !FINISHED_ORDER_STATES.includes(order.value.state)
})

const addItemDialog = ref(false)
const addItemDialogComponent = ref<InstanceType<typeof NewOutboundOrderItemDialog>>()
const addItem = async (item: OutboundOrderItemCreateSchema, keepOpen = false) => {
  if (!order.value) {
    return
  }
  const addResponse = await api.addItem(order.value.code, item)
  const itemData = onResponse(addResponse)

  if (itemData) {
    order.value.items?.push(itemData.data)
    if (addItemDialogComponent.value) {
      addItemDialogComponent.value.reset(!keepOpen)
    }
  }
}

const removeItem = async (item_index: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(await api.removeItem(order.value.code, item_index))
  if (data) {
    order.value = data.data
  }
}

const reorderItem = async (itemIndex: number, newIndex: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(await api.reorderItem(order.value.code, itemIndex, newIndex))
  if (data) {
    order.value = data.data
  }
}

const editOrderDialog = ref(false)
const updateOrder = async (body: OutboundCalculationCreateOrUpdateSchema): Promise<boolean> => {
  if (!order.value) {
    return false
  }
  const data = onResponse(await api.update(order.value.code, body))
  if (data) {
    order.value = data.data
    editOrderDialog.value = false
  }
  return !!data
}

const contact = computed({
  get: () => order.value?.contact ?? null,
  set: async (newContact) => {
    if (!order.value || newContact?.id === order.value.contact?.id) {
      return
    }
    const saved = await updateOrder({
      currency: order.value.currency,
      customer_code: order.value.customer.code,
      customer_name: order.value.customer.name,
      external_code: order.value.external_code,
      description: order.value.description,
      note: order.value.note,
      requested_delivery_date: order.value.requested_delivery_date,
      contact_id: newContact?.id ?? null,
    })
    if (saved) {
      $q.notify({
        type: 'positive',
        message: newContact
          ? `Kontakt změněn: ${contactFullName(newContact)}`
          : 'Kontakt odebrán z objednávky',
      })
    }
  },
})

const auditDialog = ref(false)

const { goToOrderOut, goToCalculation } = useAppRouter()
const duplicating = ref(false)
const duplicateOrder = async () => {
  if (!order.value) return
  duplicating.value = true
  try {
    const data = onResponse(await api.duplicate(order.value.code))
    if (data) {
      ;(isCalculation.value ? goToCalculation : goToOrderOut)(data.data.code)
    }
  } finally {
    duplicating.value = false
  }
}
</script>
