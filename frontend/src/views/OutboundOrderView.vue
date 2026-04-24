<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
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
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <OutboundOrderStateBadge :state="order.state" />
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="isDraft"
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          @click="editOrderDialog = true"
        ></q-btn>
        <q-btn
          v-if="isDraft"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          :disable="!order.items?.length"
        />
        <q-btn
          v-if="order.state !== 'cancelled'"
          unelevated
          color="negative"
          label="Uzavřít"
          icon="sym_o_scan_delete"
          @click="cancelDialog = true"
        />
      </div>
    </div>

    <div class="flex gap-2">
      <OutboundOrderDetailsListCard :order="order" />
      <CustomerCard :customer="order.customer" title="ODBĚRATEL" class="flex-1" />
      <OutboundLinkedEntitiesCard
        show-warehouse-orders
        :warehouse-orders="order.warehouse_orders"
        show-invoice
        :invoice="order.invoice"
      />
    </div>

    <ForegroundPanel v-if="$q.screen.gt.md">
      <OutboundOrderTimeline :state="order.state" />
    </ForegroundPanel>

    <div class="flex items-center gap-2 mt-5">
      <h2>Položky objednávky</h2>
      <q-btn
        v-if="isDraft"
        flat
        color="primary"
        icon="sym_o_add"
        label="přidat položku"
        @click="addItemDialog = true"
        class="ml-5"
      ></q-btn>
      <TotalWeight :order="order" class="ml-auto mr-5" />
      <TotalPrice :order="order" />
    </div>
    <OutboundOrderProductsList
      v-model:items="order.items"
      :currency="order.currency"
      :readonly="!isDraft"
      :order-code="order.code"
      :customer-code="order.customer.code"
      @remove-item="removeItem"
      @reorder-items="reorderItems"
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
  warehouseApiRoutesOutboundOrdersGetOutboundOrder,
  warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder,
  warehouseApiRoutesOutboundOrdersTransitionOutboundOrder,
  warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder,
  warehouseApiRoutesOutboundOrdersUpdateOutboundOrder,
  type OutboundOrderCreateOrUpdateSchema,
  type OutboundOrderItemCreateSchema,
  type OutboundOrderSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import NewOutboundOrderItemDialog from '@/components/order/NewOutboundOrderItemDialog.vue'
import OutboundLinkedEntitiesCard from '@/components/order/OutboundLinkedEntitiesCard.vue'
import OutboundOrderTimeline from '@/components/order/OutboundOrderTimeline.vue'
import OutboundOrderDetailsListCard from '@/components/order/OutboundOrderDetailsListCard.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import OutboundOrderUpdateOrCreateDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import OutboundOrderProductsList from '@/components/order/OutboundOrderProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import { useApi } from '@/composables/use-api'
import { ref, computed } from 'vue'

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

const isDraft = computed(() => order.value?.state === 'draft')

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

const removeItem = async (product_code: string) => {
  if (!order.value) {
    return
  }
  const result = await warehouseApiRoutesOutboundOrdersRemoveItemsFromOutboundOrder({
    path: { order_code: order.value.code, product_code },
  })
  const data = onResponse(result)
  if (data) {
    order.value.items = order.value.items?.filter((it) => it.product.code !== product_code)
  }
}

const reorderItems = async (items: NonNullable<OutboundOrderSchema['items']>) => {
  if (!order.value) {
    return
  }

  const indexedItems = items.map((it, index) => ({ ...it, index }))
  order.value.items = indexedItems

  let hasError = false
  await Promise.all(
    indexedItems.map(async (item) => {
      const res = await warehouseApiRoutesOutboundOrdersUpdateItemInOutboundOrder({
        path: { order_code: order.value!.code },
        body: {
          product_code: item.product.code,
          product_name: item.product.name,
          amount: item.amount,
          total_price: item.total_price,
          unit_price: item.unit_price,
          index: item.index,
          desired_package_type_name: item.desired_package_type_name,
          desired_batch_code: item.desired_batch_code,
        },
      })
      const data = onResponse(res)
      if (!data?.data) {
        hasError = true
      }
    }),
  )

  if (hasError) {
    const refreshResponse = await warehouseApiRoutesOutboundOrdersGetOutboundOrder({
      path: { order_code: order.value.code },
    })
    const refreshData = onResponse(refreshResponse)
    if (refreshData?.data) {
      order.value = refreshData.data
    }
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
