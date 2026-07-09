<template>
  <div v-if="order" class="flex flex-col gap-5 flex-1">
    <div class="flex justify-between">
      <q-breadcrumbs class="flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Výdejky" :to="{ name: 'warehouseOutboundOrders' }" />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <div class="flex flex-col items-end gap-3 flex-1">
        <OrderProgress :order="order" class="h-6 w-full" />
        <q-btn flat color="primary" icon-right="sym_o_query_stats" @click="auditDialog = true">
          <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
        </q-btn>
      </div>
    </div>

    <div class="mb-2 flex gap-2 justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">VÝDEJKA</span>
          <h1 class="h1 mb-1">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <div class="min-w-xs flex flex-col gap-2 items-start">
          <OutboundWarehouseOrderStateBadge :state="order.state" />
        </div>
      </div>
    </div>

    <div class="flex gap-5">
      <CustomerCard :customer="order.order.customer" title="Odběratel" class="flex-1" />

      <LinkedEntitiesCard
        :show-outbound-order="true"
        :outbound-order="order.order"
        :warehouse-orders="order.child_orders"
        :show-child-outbound-warehouse-orders="order.child_orders && order.child_orders.length > 0"
        :child-outbound-warehouse-orders="order.child_orders"
        :show-parent-outbound-warehouse-order="!!order.parent_order"
        :parent-outbound-warehouse-order="order.parent_order"
        class="flex-1"
      />
    </div>

    <div class="flex items-center justify-between mb-1 mt-3">
      <div>
        <span class="text-gray-5 text-xs">Položky k vychystání</span>
        <div class="text-sm text-gray-6 mt-1">
          Hotovo {{ doneItems.length }} / {{ order.order_items.length }}
        </div>
      </div>
      <div class="flex flex-col items-end gap-1">
        <span v-if="order.total_price_at_shipment" class="text-sm text-gray-6">
          Celková cena výdeje:
          <strong class="text-lg text-primary"
            >{{ Number(order.total_price_at_shipment).toFixed(2) }} CZK</strong
          >
        </span>
      </div>
    </div>

    <div class="flex gap-2 my-1">
      <q-btn
        :outline="!showPending"
        :color="showPending ? 'primary' : 'gray-5'"
        :label="`K vychystání (${todoItems.length})`"
        icon="sym_o_playlist_add_check"
        no-caps
        @click="showPending = !showPending"
      />
      <q-btn
        :outline="!showAssigned"
        :color="showAssigned ? 'positive' : 'gray-5'"
        :label="`Přiřazeno (${doneItems.length})`"
        icon="sym_o_task_alt"
        no-caps
        @click="showAssigned = !showAssigned"
      />
    </div>

    <OutboundWarehouseOrderItemsList
      :items="visibleItems"
      :warehouse-order-code="order.code"
      @updated="replaceOrder"
    />

    <AuditLogDialog
      v-model:show="auditDialog"
      source="warehouse-outbound-order"
      :code="order.code"
      title="Historie stavu výdejky"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> VÝDEJKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type OutboundWarehouseOrderSchema,
  warehouseApiRoutesWarehouseGetOutboundWarehouseOrder,
} from '@/client'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import OrderProgress from '@/components/OrderProgress.vue'
import OutboundWarehouseOrderItemsList from '@/components/putaway/OutboundWarehouseOrderItemsList.vue'
import OutboundWarehouseOrderStateBadge from '@/components/putaway/OutboundWarehouseOrderStateBadge.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()
const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetOutboundWarehouseOrder({
  path: { code: props.code },
})
const data = onResponse(response)

const order = ref<OutboundWarehouseOrderSchema>()
if (data) {
  order.value = data.data
}

const showPending = ref(true)
const showAssigned = ref(true)

const todoItems = computed(() => (order.value?.order_items ?? []).filter((item) => item.pending))

const doneItems = computed(() =>
  (order.value?.order_items ?? [])
    .filter((item) => !item.pending)
    .sort((a, b) => new Date(a.changed).getTime() - new Date(b.changed).getTime()),
)

const visibleItems = computed(() => [
  ...(showPending.value ? todoItems.value : []),
  ...(showAssigned.value ? doneItems.value : []),
])

const replaceOrder = (nextOrder: OutboundWarehouseOrderSchema) => {
  order.value = nextOrder
}

const auditDialog = ref(false)
</script>
