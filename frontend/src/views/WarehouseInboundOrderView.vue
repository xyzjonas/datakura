<template>
  <div v-if="warehouseOrder" class="flex flex-col gap-2 flex-1">
    <div class="flex gap-2">
      <ForegroundPanel class="flex-1">
        <span class="uppercase text-xs text-gray-5">Příjemka</span>
        <span class="flex gap-2 items-center">
          <h1 class="text-primary">{{ warehouseOrder.code }}</h1>
          <InboundWarehouseOrderStateBadge :state="warehouseOrder.state" />
        </span>
        <span class="uppercase text-xs text-gray-5">{{ warehouseOrder.code }}</span>
        <CopyToClipBoardButton :text="warehouseOrder.code" class="text-gray-5" />
        <h2 @click="goToOrderIn(warehouseOrder.order.code)" class="text-primary link mt-5 w-fit">
          {{ warehouseOrder.order.code }}
        </h2>
      </ForegroundPanel>
      <CustomerCard :customer="warehouseOrder.order.supplier" title="Dodavatel" class="flex-1" />
    </div>

    <InboundWarehouseOrderTimeline :order="warehouseOrder" class="mt-5" />

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
      v-model:items="warehouseOrder.items"
      :readonly="warehouseOrder.state !== 'draft'"
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

const warehouseOrder = ref<InboundWarehouseOrderSchema>()
if (data) {
  warehouseOrder.value = data.data
}

const step = computed(() => getInboundWarehouseOrderStep(warehouseOrder.value))

const updateOrderItems = async (item: WarehouseItemSchema, toBeAdded: WarehouseItemSchema[]) => {
  if (!warehouseOrder.value) {
    return
  }
  const response = await warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem({
    path: {
      code: warehouseOrder.value.code,
      item_code: item.code,
    },
    body: {
      to_be_added: toBeAdded,
    },
  })
  const data = onResponse(response)
  if (data) {
    warehouseOrder.value = data.data
  }
}

const confirmDialog = ref(false)
const transitionToPending = async () => {
  if (!warehouseOrder.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseUpdateInboundWarehouseOrder({
      path: { code: warehouseOrder.value.code },
      body: {
        state: 'pending',
      },
    }),
  )
  if (data) {
    warehouseOrder.value = data.data
  }
}

const dissolveItem = async (itemCode: string) => {
  if (!warehouseOrder.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem({
      path: {
        code: warehouseOrder.value.code,
        item_code: itemCode,
      },
    }),
  )
  if (data) {
    warehouseOrder.value = data.data
  }
}
</script>

<style lang="scss" scoped></style>
