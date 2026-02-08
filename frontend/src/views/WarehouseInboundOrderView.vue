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

        <InboundOrderBadge :order="order.order" />
        {{ order.credit_note?.code ?? 'NO CREDIT' }}
      </div>
    </div>
    <div class="flex gap-2">
      <CustomerCard :customer="order.order.supplier" title="Dodavatel" class="flex-1" />
    </div>

    <ForegroundPanel>
      <InboundWarehouseOrderTimeline :order="order" />
    </ForegroundPanel>

    <div class="flex items-center gap-2 my-5">
      <div class="ml-auto">
        <q-btn
          v-if="step === 1"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          class="ml-auto"
        />
      </div>
    </div>

    <InboundWarehouseOrderItemsList
      v-model:items="order.items"
      :readonly="order.state !== 'draft'"
      @packaged="updateOrderItems"
      @dissolve-item="dissolveItem"
      @remove-item="removeItem"
    ></InboundWarehouseOrderItemsList>
    <ConfirmDialog
      v-model:show="confirmDialog"
      title="Potvrdit příjemku"
      @confirm="transitionToPending"
    >
      <span>
        Příjemka bude označena jako <strong class="text-primary">připravená</strong> a zobrazí se
        pracovníkovi na příjmu. Po tomto kroku již nebude možné ji upravovat.
      </span>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import {
  type InboundWarehouseOrderSchema,
  warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseGetInboundWarehouseOrder,
  warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote,
  warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseUpdateInboundWarehouseOrder,
  type WarehouseItemSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InboundOrderBadge from '@/components/order/InboundOrderBadge.vue'
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
      item_code: item.code,
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
const transitionToPending = async () => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseUpdateInboundWarehouseOrder({
      path: { code: order.value.code },
      body: {
        state: 'pending',
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
}

const dissolveItem = async (itemCode: string) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem({
      path: {
        code: order.value.code,
        item_code: itemCode,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
}

const removeItem = async (itemCode: string, amount: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote({
      path: {
        code: order.value.code,
      },
      body: {
        item_code: itemCode,
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
</script>

<style lang="scss" scoped></style>
