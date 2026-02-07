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
      </div>
    </div>
    <div class="flex gap-2">
      <ForegroundPanel class="flex-1">
        <span class="uppercase text-xs text-gray-5">Příjemka</span>
        <span class="flex gap-2 items-center">
          <h1 class="text-primary">{{ order.code }}</h1>
          <InboundWarehouseOrderStateBadge :state="order.state" />
        </span>
        <span class="uppercase text-xs text-gray-5">{{ order.code }}</span>
        <CopyToClipBoardButton :text="order.code" class="text-gray-5" />
        <h2 @click="goToOrderIn(order.order.code)" class="text-primary link mt-5 w-fit">
          {{ order.order.code }}
        </h2>
      </ForegroundPanel>
      <CustomerCard :customer="order.order.supplier" title="Dodavatel" class="flex-1" />
    </div>

    <InboundWarehouseOrderTimeline :order="order" class="mt-5" />

    <div class="flex items-center gap-2 my-5">
      <!-- <q-icon v-if="synced" name="sym_o_check_circle" size="20px" color="positive" class="ml-5" /> -->
      <!-- <Transition name="fade" mode="out-in">
        <q-btn
          v-if="!synced"
          unelevated
          flat
          color="primary"
          icon="sym_o_backup"
          label="uložit změny"
        ></q-btn>
      </Transition> -->
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
      @remove-item="dissolveItem"
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
import { useAppRouter } from '@/composables/use-app-router'
import { getInboundWarehouseOrderStep } from '@/constants/inbound-warehouse-order'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()

const { onResponse } = useApi()
const { goToOrderIn } = useAppRouter()

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
</script>

<style lang="scss" scoped></style>
