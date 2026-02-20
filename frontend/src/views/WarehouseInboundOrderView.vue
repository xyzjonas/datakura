<template>
  <div v-if="order" class="flex flex-col gap-2 flex-1">
    <q-breadcrumbs class="mb-5">
      <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
      <q-breadcrumbs-el label="Vydané Objednávky" :to="{ name: 'orders' }" />
      <q-breadcrumbs-el
        :label="order.order.code"
        :to="{ name: 'incomingOrderDetail', params: { code: order.order.code } }"
      />
      <q-breadcrumbs-el :label="order.code" />
    </q-breadcrumbs>

    <div class="mb-2 flex justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">PŘÍJEMKA</span>
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <InboundWarehouseOrderStateBadge :state="order.state" />
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="step === 1"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          class="ml-auto"
        />
        <q-btn
          v-if="step === 2"
          unelevated
          color="primary"
          icon="sym_o_restart_alt"
          label="editovat"
          @click="resetDialog = true"
          class="ml-auto"
        />
      </div>
    </div>
    <div class="flex gap-2">
      <CustomerCard :customer="order.order.supplier" title="Dodavatel" class="flex-1" />
      <LinkedEntitiesCard
        show-inbound-order
        :inbound-order="order.order"
        show-invoice
        show-credit-note
        :credit-note="order.credit_note"
      />
    </div>

    <ForegroundPanel>
      <InboundWarehouseOrderTimeline :order="order" />
    </ForegroundPanel>

    <LargeTabs
      v-model:tab="activeTabKey"
      :items="[
        { key: 'todo', icon: 'sym_o_call_received', title: 'Neuzavřené' },
        { key: 'outbound', icon: 'sym_o_call_made', title: 'Uzavřené' },
      ]"
      class="my-5"
    />

    <InboundWarehouseOrderItemsList
      v-model:items="order.items"
      :readonly="order.state !== 'draft'"
      :allow-move="order.state === 'pending' || order.state === 'started'"
      @packaged="updateOrderItems"
      @dissolve-item="dissolveItem"
      @remove-item="removeItem"
      @moved="moveItem"
    ></InboundWarehouseOrderItemsList>
    <ConfirmDialog
      v-model:show="confirmDialog"
      title="Potvrdit příjemku"
      @confirm="transitionOrder('pending')"
    >
      <span>
        Příjemka bude označena jako <InboundWarehouseOrderStateBadge state="pending" /> a pracovník
        na příjmu může začít s přesunem zboží. Po tomto kroku již nebude možné příjemku upravovat.
      </span>
    </ConfirmDialog>
    <ConfirmDialog
      v-model:show="resetDialog"
      title="Resetovat příjemku"
      @confirm="transitionOrder('draft')"
    >
      <span>
        Příjemka bude zpátky označena jako <InboundWarehouseOrderStateBadge state="draft" /> a bude
        možné ji opět editovat. Pracovník na příjmu nebude schopen pokračovat s přesunem zboží.<br /><small
          >Není možné vrátit rozpracovanou příjemku.</small
        >
      </span>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import {
  type InboundWarehouseOrderSchema,
  warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseGetInboundWarehouseOrder,
  warehouseApiRoutesWarehousePutawayInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote,
  warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseTransitionInboundWarehouseOrder,
  type WarehouseItemSchema,
  type WarehouseLocationSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LargeTabs from '@/components/LargeTabs.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import InboundWarehouseOrderItemsList from '@/components/putaway/InboundWarehouseOrderItemsList.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import InboundWarehouseOrderTimeline from '@/components/putaway/InboundWarehouseOrderTimeline.vue'
import { useApi } from '@/composables/use-api'
import { getInboundWarehouseOrderStep } from '@/constants/inbound-warehouse-order'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()

const { onResponse } = useApi()
const $q = useQuasar()

const activeTabKey = ref('todo')

const response = await warehouseApiRoutesWarehouseGetInboundWarehouseOrder({
  path: { code: props.code },
})
const data = onResponse(response)

const order = ref<InboundWarehouseOrderSchema>()
if (data) {
  order.value = data.data
}

const step = computed(() => getInboundWarehouseOrderStep(order.value))

const updateOrderItems = async (item: WarehouseItemSchema, toBeAdded: WarehouseItemSchema[]) => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem({
    path: {
      code: order.value.code,
      item_code: item.product.code,
    },
    body: {
      to_be_added: toBeAdded,
    },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
  }
}

const confirmDialog = ref(false)
const resetDialog = ref(false)
const transitionOrder = async (state: 'pending' | 'draft') => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseTransitionInboundWarehouseOrder({
      path: { code: order.value.code },
      body: {
        state: state,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: 'Nový stav zaznamenán',
    caption: `Příjemka ${order.value.code}`,
  })
}

const dissolveItem = async (itemId: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem({
      path: {
        code: order.value.code,
        item_id: itemId,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
}

const removeItem = async (itemId: number, amount: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote({
      path: {
        code: order.value.code,
      },
      body: {
        item_id: itemId,
        amount: amount,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: `${amount} MJ odstraněno z příjemky`,
    caption: `Evidováno v dobropisu ${order.value.credit_note?.code ?? 'N/A'}`,
  })
}

const moveItem = async (itemCode: number, location: WarehouseLocationSchema) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehousePutawayInboundWarehouseOrderItem({
      path: {
        code: order.value.code,
        item_id: itemCode,
      },
      body: {
        new_location_code: location.code,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: `Položka úspěšně přesunuta`,
    caption: `'${itemCode}' se nyní nachází na skladovém místě ${location.code}`,
  })
}
</script>

<style lang="scss" scoped></style>
