<template>
  <div v-if="order" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-between">
      <q-breadcrumbs class="flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Výdejky" :to="{ name: 'warehouseOutboundOrders' }" />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <!-- <OrderProgress :order="order" class="flex-1 h-6 w-full" /> -->
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
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
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

    <div class="flex gap-2">
      <CustomerCard :customer="order.order.customer" title="Odběratel" class="flex-[3]" />
      <ForegroundPanel class="flex-1 flex flex-col justify-center items-center gap-2">
        <span class="text-gray-5 text-2xs uppercase">Objednávka</span>
        <a
          class="link text-lg"
          @click="$router.push({ name: 'outboundOrderDetail', params: { code: order.order.code } })"
        >
          {{ order.order.code }}
        </a>
      </ForegroundPanel>
      <ForegroundPanel class="flex-1 flex flex-col gap-2 justify-center">
        <span class="text-gray-5 text-2xs uppercase">Vazby</span>
        <a
          v-if="order.parent_order"
          class="link"
          @click="
            $router.push({
              name: 'warehouseOutboundOrderDetail',
              params: { code: order.parent_order.code },
            })
          "
        >
          Nadřazená: {{ order.parent_order.code }}
        </a>
        <a
          v-for="child in order.child_orders"
          :key="child.code"
          class="link"
          @click="
            $router.push({ name: 'warehouseOutboundOrderDetail', params: { code: child.code } })
          "
        >
          Podřízená: {{ child.code }}
        </a>
        <span
          v-if="!order.parent_order && (order.child_orders?.length ?? 0) === 0"
          class="text-gray-5"
        >
          Bez návazných výdejek
        </span>
      </ForegroundPanel>
    </div>

    <div class="flex items-center justify-between mb-1 mt-3">
      <div>
        <span class="text-gray-5 text-xs">Položky k vychystání</span>
        <div class="text-sm text-gray-6 mt-1">
          Hotovo {{ doneItems.length }} / {{ order.order_items.length }}
        </div>
      </div>
      <q-badge color="primary">Zbývá {{ order.remaining_amount }}</q-badge>
    </div>

    <LargeTabs
      v-model:tab="activeTabKey"
      :items="[
        {
          key: 'todo',
          icon: 'sym_o_playlist_add_check',
          title: `${todoItems.length} položky k vychystání`,
        },
        { key: 'done', icon: 'sym_o_task_alt', title: `${doneItems.length} přiřazené položky` },
      ]"
      class="my-5"
    />

    <OutboundWarehouseOrderItemsList
      v-if="activeTabKey === 'todo'"
      :items="todoItems"
      :warehouse-order-code="order.code"
      @updated="replaceOrder"
    />

    <OutboundWarehouseOrderItemsList
      v-if="activeTabKey === 'done'"
      :items="doneItems"
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
import LargeTabs from '@/components/LargeTabs.vue'
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

const activeTabKey = ref('todo')

const pendingOrderItems = computed(() =>
  (order.value?.order_items ?? []).filter((item) => item.pending),
)

const todoItems = computed(() => pendingOrderItems.value)

const doneItems = computed(() => (order.value?.order_items ?? []).filter((item) => !item.pending))

const replaceOrder = (nextOrder: OutboundWarehouseOrderSchema) => {
  order.value = nextOrder
}

const auditDialog = ref(false)
</script>
