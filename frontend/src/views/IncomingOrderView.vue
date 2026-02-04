<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
    <q-breadcrumbs class="mb-5">
      <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
      <q-breadcrumbs-el label="Vydané Objednávky" :to="{ name: 'incomingOrders' }" />
      <q-breadcrumbs-el :label="order.code" />
    </q-breadcrumbs>

    <div class="mb-2 flex justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">VYDANÁ OBJEDNÁVKA</span>
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <InboundOrderStateBadge :state="order.state" />
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="getInboundOrderStep(order) === 1"
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          @click="editOrderDialog = true"
        ></q-btn>
        <q-btn
          v-if="order.state !== 'cancelled'"
          unelevated
          color="negative"
          label="zrušit"
          icon="sym_o_scan_delete"
          @click="cancelDialog = true"
        />
        <PrintDropdownButton
          :items="[
            {
              label: 'PDF bez cen',
              onClick: openPdf,
            },
          ]"
        />
        <q-btn
          v-if="getInboundOrderStep(order) === 1"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          class="ml-auto"
          :disable="order.items?.length === 0"
        ></q-btn>
        <q-btn
          v-if="getInboundOrderStep(order) === 2"
          unelevated
          color="positive"
          label="Zboží dorazilo na příjem"
          icon="sym_o_check"
          @click="createWarehouseOrderDialog = true"
        />

        <div v-if="order.warehouse_order" class="flex flex-col ml-2 border py-2 px-5 rounded">
          <span class="text-gray-5 text-2xs">PŘÍJEMKA</span>
          <div class="flex items-center gap-2">
            <a class="link text-lg" @click="goToWarehouseOrderIn(order.warehouse_order.code)"
              >{{ order.warehouse_order.code }}
            </a>
            <InboundWarehouseOrderStateBadge
              :state="order.warehouse_order.state"
            ></InboundWarehouseOrderStateBadge>
          </div>
        </div>
      </div>
    </div>
    <div class="flex gap-2">
      <InboundOrderDetailsListCard :order="order" />
      <CustomerCard :customer="order.supplier" title="DODAVATEL" class="flex-1" />
    </div>

    <ForegroundPanel>
      <InboundOrderTimeline :state="order.state" />
    </ForegroundPanel>

    <div class="flex items-center gap-2 mt-5">
      <CurrencyDropdown v-model="order.currency" />
      <h2>Položky objednávky</h2>
      <q-btn
        v-if="getInboundOrderStep(order) === 1"
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
    <div>
      <ProductsList
        v-model:items="order.items"
        :currency="order.currency"
        :readonly="getInboundOrderStep(order) > 1"
        @remove-item="removeItem"
        @add-item="addItemDialog = true"
      />
    </div>
    <NewOrderItemDialog
      ref="addItemDialogComponent"
      v-model:show="addItemDialog"
      @add-item="addItem"
      :currency="order.currency"
    />
    <InboundOrderUpdateOrCreateDialog
      v-model:show="editOrderDialog"
      :order-in="order"
      submit-label="uložit"
      title="Upravit objednávku"
      @create-order="updateOrder"
    />
    <ConfirmDialog v-model="confirmDialog" title="Potvrdit vydanou objednávku?" @confirm="confirm">
      <span
        >objednávka přejde do stavu <strong class="text-primary">potvrzeno</strong> a nebude možné
        ji dále editovat!</span
      >
    </ConfirmDialog>
    <ConfirmDialog v-model:show="cancelDialog" title="Zrušit vydanou objednávku?" @confirm="cancel">
      <span
        >objednávka bude označena jako <strong class="text-red">zrušeno</strong> a bude archivována
        (zmizí z výpisu objednávek).</span
      >
    </ConfirmDialog>
    <InboundOrderPutawayDialog
      v-model:show="createWarehouseOrderDialog"
      @confirm="createWarehouseOrder"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> OBJEDNÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersAddItemToInboundOrder,
  warehouseApiRoutesInboundOrdersGetInboundOrder,
  warehouseApiRoutesInboundOrdersGetInboundOrderPdf,
  warehouseApiRoutesInboundOrdersRemoveItemsFromInboundOrder,
  warehouseApiRoutesInboundOrdersTransitionInboundOrder,
  warehouseApiRoutesInboundOrdersUpdateInboundOrder,
  warehouseApiRoutesWarehouseCreateInboundWarehouseOrder,
  type InboundOrderCreateOrUpdateSchema,
  type InboundOrderItemCreateSchema,
  type InboundOrderSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import CurrencyDropdown from '@/components/order/CurrencyDropdown.vue'
import InboundOrderDetailsListCard from '@/components/order/InboundOrderDetailsListCard.vue'
import InboundOrderPutawayDialog from '@/components/order/InboundOrderPutawayDialog.vue'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import InboundOrderUpdateOrCreateDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import NewOrderItemDialog from '@/components/order/NewOrderItemDialog.vue'
import InboundOrderTimeline from '@/components/order/InboundOrderTimeline.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import PrintDropdownButton from '@/components/PrintDropdownButton.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { getInboundOrderStep } from '@/constants/inbound-order'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const props = defineProps<{ code: string }>()
const order = ref<InboundOrderSchema>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesInboundOrdersGetInboundOrder({
  path: { order_code: props.code },
})
const data = onResponse(response)
if (data) {
  order.value = data.data
}

const addItemDialog = ref(false)
const addItemDialogComponent = ref<InstanceType<typeof NewOrderItemDialog>>()
const addItem = async (item: InboundOrderItemCreateSchema) => {
  if (!order.value) {
    return
  }
  const addResponse = await warehouseApiRoutesInboundOrdersAddItemToInboundOrder({
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
  const result = await warehouseApiRoutesInboundOrdersRemoveItemsFromInboundOrder({
    path: { order_code: order.value.code, product_code },
  })
  const data = onResponse(result)
  if (data) {
    order.value.items = order.value.items?.filter((it) => it.product.code !== product_code)
  }
}

const editOrderDialog = ref(false)
const updateOrder = async (body: InboundOrderCreateOrUpdateSchema) => {
  if (!order.value) {
    return
  }
  const result = await warehouseApiRoutesInboundOrdersUpdateInboundOrder({
    body: body,
    path: { order_code: order.value.code },
  })
  const data = onResponse(result)
  if (data) {
    order.value = data.data
    editOrderDialog.value = false
  }
}

const confirmDialog = ref(false)
const confirm = async () => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesInboundOrdersTransitionInboundOrder({
    path: { order_code: order.value.code },
    body: { state: 'submitted' },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
    confirmDialog.value = false
  }
}

const cancelDialog = ref(false)
const cancel = async () => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesInboundOrdersTransitionInboundOrder({
    path: { order_code: order.value.code },
    body: { state: 'cancelled' },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
    cancelDialog.value = false
  }
}

const $q = useQuasar()
const { goToWarehouseOrderIn } = useAppRouter()
const createWarehouseOrderDialog = ref(false)
const createWarehouseOrder = async (locationCode: string) => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesWarehouseCreateInboundWarehouseOrder({
    body: { purchase_order_code: order.value.code, location_code: locationCode },
  })
  const data = onResponse(response)
  if (data) {
    createWarehouseOrderDialog.value = false
    $q.notify({
      type: 'positive',
      message: `Příjemka úspěšně vytvořena: ${data.data.code}`,
    })
    goToWarehouseOrderIn(data.data.code)
  }
}

const openPdf = async () => {
  const resonse = await warehouseApiRoutesInboundOrdersGetInboundOrderPdf({
    path: { order_code: props.code },
  })
  if (!resonse.error) {
    const blobUrl = URL.createObjectURL(resonse.data as unknown as Blob)
    window.open(blobUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(blobUrl), 100)
  }
}
</script>

<style lang="scss" scoped></style>
