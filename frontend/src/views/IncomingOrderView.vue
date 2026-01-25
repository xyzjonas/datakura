<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[400px] flex-[2]">
        <span class="text-gray-5 flex items-center gap-1">POPTÁVKA</span>
        <h1 class="text-primary mb-1">{{ order.code }}</h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ order.code }}</h5>
          <CopyToClipBoardButton v-if="order.code" :text="order.code" />
        </span>

        <q-list dense class="mt-2" separator>
          <q-item>
            <q-item-section>Číslo dokladu</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.code }}
                <CopyToClipBoardButton v-if="order.code" :text="order.code" />
              </span>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Externí číslo</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.external_code }}
                <CopyToClipBoardButton v-if="order.external_code" :text="order.external_code" />
              </span>
            </q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-[2]">
        <q-list dense separator>
          <q-item>
            <q-item-section>Požadovaný termín dodání</q-item-section>
            <q-item-section avatar>{{ formatDateLong(order.created) }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Datum zrušení</q-item-section>
            <q-item-section avatar>{{ formatDateLong(order.created) }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Zboží přijato</q-item-section>
            <q-item-section avatar>{{ formatDateLong(order.created) }}</q-item-section>
          </q-item>
        </q-list>
        <!-- <q-list dense class="mt-auto">
          <q-item>
            <q-item-section>
              <span class="text-xs text-gray-5">Číslo příjemky</span>
              <a
                v-if="order.warehouse_order_code"
                class="link"
                @click="goToWarehouseOrderIn(order.warehouse_order_code)"
                >{{ order.warehouse_order_code }}</a
              >
            </q-item-section>
            <q-item-section avatar></q-item-section>
          </q-item>
        </q-list> -->
      </ForegroundPanel>
      <CustomerCard :customer="order.supplier" title="DODAVATEL" class="flex-1" />
    </div>

    <OrderTimeline :state="order.state" />

    <div class="flex items-center gap-2 my-5">
      <div v-if="getInboundOrderStep(order) === 1" class="flex items-center gap-2">
        <q-btn
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          @click="editOrderDialog = true"
        ></q-btn>
        <q-btn
          outline
          color="primary"
          icon="sym_o_add"
          label="přidat položku"
          @click="addItemDialog = true"
        ></q-btn>
      </div>
      <div class="ml-auto">
        <!-- DRAFT -->
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
        <!-- IN TRANSIT -->
        <q-btn
          v-if="getInboundOrderStep(order) === 2"
          unelevated
          color="positive"
          label="Zboží je na příjmu"
          icon="sym_o_check"
          @click="createWarehouseOrderDialog = true"
        />
        <div v-if="order.warehouse_order" class="flex items-center gap-2">
          <a class="link text-lg" @click="goToWarehouseOrderIn(order.warehouse_order.code)"
            >{{ order.warehouse_order.code }}
          </a>
          <InboundWarehouseOrderStateBadge
            :state="order.warehouse_order.state"
          ></InboundWarehouseOrderStateBadge>
        </div>
        <q-btn
          v-if="getInboundOrderStep(order) === 3 && order.warehouse_order_code"
          unelevated
          flat
          :color="order.warehouse_order_code ? 'positive' : 'gray'"
          :label="`příjemka ${order.warehouse_order_code ?? ''}`"
          icon="sym_o_input"
          @click="goToWarehouseOrderIn(order.warehouse_order_code)"
        />
      </div>
    </div>

    <div class="flex items-center gap-2">
      <CurrencyDropdown v-model="order.currency" />
      <h2>Položky poptávky</h2>
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
      title="Upravit poptávku"
      @create-order="updateOrder"
    />
    <ConfirmDialog v-model="confirmDialog" title="Potvrdit poptávku?" @confirm="confirm">
      <span
        >poptávka přejde do stavu <strong class="text-primary">potvrzeno</strong> a nebude možné ji
        dále editovat!</span
      >
    </ConfirmDialog>
    <InboundOrderPutawayDialog
      v-model:show="createWarehouseOrderDialog"
      @confirm="createWarehouseOrder"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> POPTÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOrdersAddItemToInboundOrder,
  warehouseApiRoutesOrdersGetInboundOrder,
  warehouseApiRoutesOrdersRemoveItemsFromInboundOrder,
  warehouseApiRoutesOrdersTransitionInboundOrder,
  warehouseApiRoutesOrdersUpdateInboundOrder,
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
import InboundOrderPutawayDialog from '@/components/order/InboundOrderPutawayDialog.vue'
import InboundOrderUpdateOrCreateDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import NewOrderItemDialog from '@/components/order/NewOrderItemDialog.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { getInboundOrderStep } from '@/constants/inbound-order'
import { formatDateLong } from '@/utils/date'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const props = defineProps<{ code: string }>()
const order = ref<InboundOrderSchema>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesOrdersGetInboundOrder({
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
  const addResponse = await warehouseApiRoutesOrdersAddItemToInboundOrder({
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
  const result = await warehouseApiRoutesOrdersRemoveItemsFromInboundOrder({
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
  const result = await warehouseApiRoutesOrdersUpdateInboundOrder({
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
  const response = await warehouseApiRoutesOrdersTransitionInboundOrder({
    path: { order_code: order.value.code },
    body: { state: 'submitted' },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
    confirmDialog.value = false
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
</script>

<style lang="scss" scoped></style>
