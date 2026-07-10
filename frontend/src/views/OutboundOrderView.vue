<template>
  <div v-if="order" class="w-full flex flex-col gap-5">
    <div class="flex justify-between">
      <q-breadcrumbs class="mb-5">
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el
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
          <span class="text-gray-5 flex items-center gap-1">PŘIJATÁ OBJEDNÁVKA</span>
          <h1 class="h1 mb-1">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
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
        <q-btn
          v-if="canConfirm"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          :disable="!order.items?.length"
        />
        <q-btn
          unelevated
          color="secondary"
          icon="sym_o_content_copy"
          label="duplikovat"
          :loading="duplicating"
          @click="duplicateOrder"
        />
        <q-btn
          v-if="canCancel"
          unelevated
          color="negative"
          label="Uzavřít"
          icon="sym_o_scan_delete"
          @click="cancelDialog = true"
        />
      </div>
    </div>

    <div class="flex gap-5">
      <OutboundOrderDetailsListCard :order="order" class="flex-[2]" />
      <CustomerCard :customer="order.customer" title="ODBĚRATEL" class="flex-1" />
      <LinkedEntitiesCard
        show-outbound-warehouse-orders
        :outbound-warehouse-orders="order.warehouse_orders"
        show-invoice
        :invoice="order.invoice"
        class="flex-1"
      />
    </div>

    <CommentCard v-if="order.note">{{ order.note }}</CommentCard>

    <OutboundOrderTimeline :order="order" />

    <div class="flex items-center justify-center gap-2 sm:gap-5 mt-5">
      <h2>Položky objednávky</h2>
      <div
        class="flex items-center justify-center sm:justify-end flex-1 gap-3 min-w-300px flex-row-reverse sm:flex-row"
      >
        <TotalWeight :order="order" />
        <TotalPrice :order="order" />
      </div>
    </div>
    <q-btn
      v-if="isEditable"
      flat
      dense
      color="primary"
      icon="sym_o_add"
      label="přidat položku"
      @click="addItemDialog = true"
    ></q-btn>
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
      title="Upravit objednávku"
      @create-order="updateOrder"
    />

    <ConfirmDialog
      v-model:show="confirmDialog"
      title="Potvrdit přijatou objednávku?"
      @confirm="confirmOrder"
    >
      <span>
        Objednávka přejde do stavu <OutboundOrderStateBadge state="picking" /> a bude vytvořena
        výdejka.
      </span>
    </ConfirmDialog>

    <ConfirmDialog
      v-model:show="cancelDialog"
      title="Uzavřít přijatou objednávku?"
      @confirm="cancel"
    >
      <span>objednávka bude označena jako <OutboundOrderStateBadge state="cancelled" />.</span>
    </ConfirmDialog>

    <AuditLogDialog
      v-model:show="auditDialog"
      source="outbound-order"
      :code="order.code"
      title="Historie změn objednávky"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> OBJEDNÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersAddItemToOutboundOrder,
  warehouseApiRoutesOutboundOrdersDuplicateOutboundOrder,
  warehouseApiRoutesOutboundOrdersGetOutboundOrder,
  warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder,
  warehouseApiRoutesOutboundOrdersReorderItemInOutboundOrder,
  warehouseApiRoutesOutboundOrdersTransitionOutboundOrder,
  warehouseApiRoutesOutboundOrdersUpdateOutboundOrder,
  type OutboundOrderCreateOrUpdateSchema,
  type OutboundOrderItemCreateSchema,
  type OutboundOrderSchema,
} from '@/client'
import CommentCard from '@/components/CommentCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import NewOutboundOrderItemDialog from '@/components/order/NewOutboundOrderItemDialog.vue'
import OutboundOrderDetailsListCard from '@/components/order/OutboundOrderDetailsListCard.vue'
import OutboundOrderProductsList from '@/components/order/OutboundOrderProductsList.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import OutboundOrderTimeline from '@/components/order/OutboundOrderTimeline.vue'
import OutboundOrderUpdateOrCreateDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()
const order = ref<OutboundOrderSchema>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesOutboundOrdersGetOutboundOrder({
  path: { order_code: props.code },
})
const data = onResponse(response)
if (data) {
  order.value = data.data
}

const isEditable = computed(() => {
  if (!order.value) {
    return false
  }

  return !['cancelled', 'completed', 'invoiced', 'waiting_for_payment', 'completed_paid'].includes(
    order.value.state,
  )
})

const canConfirm = computed(() =>
  ['draft', 'calculation', 'submitted'].includes(order.value?.state ?? ''),
)
const canCancel = computed(() => isEditable.value)

const addItemDialog = ref(false)
const addItemDialogComponent = ref<InstanceType<typeof NewOutboundOrderItemDialog>>()
const addItem = async (item: OutboundOrderItemCreateSchema) => {
  if (!order.value) {
    return
  }
  const addResponse = await warehouseApiRoutesOutboundOrdersAddItemToOutboundOrder({
    path: { order_code: order.value.code },
    body: item,
  })
  const itemData = onResponse(addResponse)

  if (itemData) {
    order.value.items?.push(itemData.data)
    if (addItemDialogComponent.value) {
      addItemDialogComponent.value.reset()
    }
  }
}

const removeItem = async (item_index: number) => {
  if (!order.value) {
    return
  }
  const result = await warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder({
    path: { order_code: order.value.code, item_index },
  })
  const data = onResponse(result)
  if (data) {
    order.value.items = order.value.items?.filter((it) => it.index !== item_index)
  }
}

const reorderItem = async (itemIndex: number, newIndex: number) => {
  if (!order.value) {
    return
  }
  const res = await warehouseApiRoutesOutboundOrdersReorderItemInOutboundOrder({
    path: { order_code: order.value.code, item_index: itemIndex },
    body: { new_index: newIndex },
  })
  const data = onResponse(res)
  if (data) {
    order.value = data.data
  }
}

const editOrderDialog = ref(false)
const updateOrder = async (body: OutboundOrderCreateOrUpdateSchema) => {
  if (!order.value) {
    return
  }
  const result = await warehouseApiRoutesOutboundOrdersUpdateOutboundOrder({
    body: body,
    path: { order_code: order.value.code },
  })
  const data = onResponse(result)
  if (data) {
    order.value = data.data
    editOrderDialog.value = false
  }
}

const cancelDialog = ref(false)
const cancel = async () => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesOutboundOrdersTransitionOutboundOrder({
    path: { order_code: order.value.code },
    body: { action: 'cancel' },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
    cancelDialog.value = false
  }
}

const auditDialog = ref(false)

const { goToOrderOut } = useAppRouter()
const duplicating = ref(false)
const duplicateOrder = async () => {
  if (!order.value) return
  duplicating.value = true
  try {
    const result = await warehouseApiRoutesOutboundOrdersDuplicateOutboundOrder({
      path: { order_code: order.value.code },
    })
    const data = onResponse(result)
    if (data) {
      goToOrderOut(data.data.code)
    }
  } finally {
    duplicating.value = false
  }
}

const confirmDialog = ref(false)
const confirmOrder = async () => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesOutboundOrdersTransitionOutboundOrder({
    path: { order_code: order.value.code },
    body: { action: 'next' },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
    confirmDialog.value = false
  }
}
</script>
