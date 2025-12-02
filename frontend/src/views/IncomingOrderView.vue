<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[400px] flex-1">
        <span class="text-gray-5 flex items-center gap-1">OBJEDNÁVKA</span>
        <h1 class="text-primary mb-1">{{ order.code }}</h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ order.code }}</h5>
          <q-btn flat round size="8px" icon="content_copy"></q-btn>
        </span>

        <q-list dense class="mt-2" separator>
          <q-item>
            <q-item-section>Číslo dokladu</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.code }}
                <q-btn flat round size="8px" icon="content_copy"></q-btn>
              </span>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Externí číslo</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.external_code }}
                <q-btn flat round size="8px" icon="content_copy"></q-btn>
              </span>
            </q-item-section>
          </q-item>
        </q-list>
        <div class="mt-auto flex flex-row-reverse">
          <q-btn outline color="primary" icon="edit" label="upravit" disable></q-btn>
        </div>
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
        <q-list dense class="mt-auto">
          <q-item>
            <q-item-section>
              <span class="text-xs text-gray-5">Číslo příjemky</span>
              <span>N/A</span>
            </q-item-section>
            <q-item-section avatar
              ><q-btn disable label="naskladnit" outline color="primary" icon="sym_o_input"
            /></q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <span class="text-gray-5 flex items-center justify-between gap-1">
          <span>DODAVATEL</span>
          <q-btn dense flat icon="sym_o_compare_arrows" size="10px" />
        </span>
        <h1 @click="goToCustomer(order.supplier.code)" class="text-primary mb-1 link">
          {{ order.supplier.name }}
        </h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ order.supplier.code }}</h5>
          <q-btn flat round size="8px" icon="content_copy"></q-btn>
        </span>
        <q-list dense separator>
          <q-item>
            <q-item-section>IČO</q-item-section>
            <q-item-section avatar>{{ order.supplier.identification }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>DIČ</q-item-section>
            <q-item-section avatar>{{ order.supplier.tax_identification }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Kontakt</q-item-section>
            <q-item-section avatar>{{ contact?.email }}</q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
    </div>

    <OrderTimeline />

    <div class="flex items-center gap-2 my-5">
      <q-btn
        unelevated
        color="primary"
        icon="sym_o_add"
        label="přidat položku"
        @click="addItemDialog = true"
      ></q-btn>
      <!-- <q-icon v-if="synced" name="sym_o_check_circle" size="20px" color="positive" class="ml-5" /> -->
      <Transition name="fade" mode="out-in">
        <q-btn
          v-if="!synced"
          unelevated
          flat
          color="primary"
          icon="sym_o_backup"
          label="uložit změny"
        ></q-btn>
      </Transition>
      <q-btn
        unelevated
        color="positive"
        icon="sym_o_order_approve"
        label="potvrdit"
        @click="addItemDialog = true"
        class="ml-auto"
        :disable="order.items?.length === 0"
      ></q-btn>
    </div>

    <div class="flex items-center gap-2">
      <CurrencyDropdown v-model="order.currency" />
      <h2>Položky objednávky</h2>
      <TotalWeight :order="order" class="ml-auto mr-5" />
      <TotalPrice :order="order" />
    </div>
    <div>
      <ProductsList
        v-model:items="order.items"
        :currency="order.currency"
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
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> OBJEDNÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOrdersAddItemToIncomingOrder,
  warehouseApiRoutesOrdersGetIncomingOrder,
  warehouseApiRoutesOrdersRemoveItemsFromIncomingOrder,
  type IncomingOrderItemCreateSchema,
  type IncomingOrderSchema,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import CurrencyDropdown from '@/components/order/CurrencyDropdown.vue'
import NewOrderItemDialog from '@/components/order/NewOrderItemDialog.vue'
import OrderTimeline from '@/components/order/OrderTimeline.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import { useApi } from '@/composables/use-api'
import { formatDateLong } from '@/utils/date'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ code: string }>()
const order = ref<IncomingOrderSchema>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesOrdersGetIncomingOrder({
  path: { order_code: props.code },
})
const data = onResponse(response)
if (data) {
  order.value = data.data
}

const contact = computed(() => {
  if (!order.value?.supplier.contacts) {
    return undefined
  }
  if (order.value.supplier.contacts.length <= 0) {
    return undefined
  }
  return order.value.supplier.contacts[0]
})

const router = useRouter()
const goToCustomer = (code: string) => {
  router.push({ name: 'customerDetail', params: { customerCode: code } })
}

const copyOnInit = JSON.parse(JSON.stringify(order.value)) as IncomingOrderSchema
const synced = computed(() => JSON.stringify(order.value) === JSON.stringify(copyOnInit))

const addItemDialog = ref(false)
const addItemDialogComponent = ref<InstanceType<typeof NewOrderItemDialog>>()
const addItem = async (item: IncomingOrderItemCreateSchema) => {
  if (!order.value) {
    return
  }
  const addResponse = await warehouseApiRoutesOrdersAddItemToIncomingOrder({
    path: { order_code: order.value.code },
    body: item,
  })

  if (!addResponse.error && addResponse.data?.success === true) {
    order.value.items?.push(addResponse.data.data)
    copyOnInit.items?.push(addResponse.data.data)
    if (addItemDialogComponent.value) {
      addItemDialogComponent.value.reset()
    }
  }
}

const removeItem = async (product_code: string) => {
  if (!order.value) {
    return
  }
  const result = await warehouseApiRoutesOrdersRemoveItemsFromIncomingOrder({
    path: { order_code: order.value.code, product_code },
  })
  const data = onResponse(result)
  if (data) {
    order.value.items = order.value.items?.filter((it) => it.product.code !== product_code)
    copyOnInit.items = copyOnInit.items?.filter((it) => it.product.code !== product_code)
  }
}
</script>

<style lang="scss" scoped></style>
