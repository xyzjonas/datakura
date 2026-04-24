<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
    <div class="flex justify-between">
      <q-breadcrumbs class="mb-5">
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el
          label="Vydané Objednávky"
          :to="{ name: 'orders', query: { tab: 'inbound' } }"
        />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <q-btn flat dense color="primary" icon="sym_o_query_stats" @click="auditDialog = true">
        <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
      </q-btn>
    </div>

    <div class="mb-2 flex justify-between items-start md:items-center flex-col md:flex-row gap-2">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">VYDANÁ OBJEDNÁVKA</span>
          <h1 class="text-primary mb-1 text-3xl md:text-5xl">{{ order.code }}</h1>
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
          label="Uzavřít"
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
          v-if="getInboundOrderStep(order) === 2 && !order.invoice"
          unelevated
          color="primary"
          label="Připojit fakturu"
          icon="sym_o_receipt_long"
          @click="attachInvoiceDialog = true"
        />
        <q-btn
          v-if="getInboundOrderStep(order) === 2 && !!order.invoice"
          unelevated
          color="positive"
          label="Potvrdit"
          icon="sym_o_check"
          @click="createWarehouseOrderDialog = true"
        />
      </div>
    </div>
    <div class="flex gap-2 flex-col md:flex-row">
      <InboundOrderDetailsListCard :order="order" />
      <CustomerCard :customer="order.supplier" title="DODAVATEL" class="flex-1" />
      <LinkedEntitiesCard
        show-warehouse-order
        :warehouse-orders="order.warehouse_orders"
        show-credit-note
        :credit-note="order.credit_note"
        show-invoice
        :invoice="order.invoice"
      />
    </div>

    <ForegroundPanel v-if="$q.screen.gt.md">
      <InboundOrderTimeline :state="order.state" />
    </ForegroundPanel>

    <div class="flex items-center justify-between gap-2 mt-5">
      <div class="flex items-center gap-2">
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
        <TotalWeight :order="order" />
      </div>
      <TotalPrice :order="order" />
    </div>
    <div>
      <ProductsList
        v-model:items="order.items"
        :currency="order.currency"
        :readonly="getInboundOrderStep(order) > 1"
        :order-code="order.code"
        order-type="inbound"
        @dissolve-item="removeItem"
        @reorder-items="reorderItems"
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
        >objednávka přejde do stavu <InboundOrderStateBadge state="submitted" /> a nebude možné ji
        dále editovat!</span
      >
    </ConfirmDialog>
    <ConfirmDialog
      v-model:show="cancelDialog"
      title="Uzavřít vydanou objednávku?"
      @confirm="cancel"
    >
      <span
        >objednávka bude označena jako <InboundOrderStateBadge state="cancelled" /> a bude
        archivována - zmizí z výpisu objednávek.</span
      >
    </ConfirmDialog>
    <InboundOrderPutawayDialog
      v-model:show="createWarehouseOrderDialog"
      @confirm="createWarehouseOrder"
    />
    <InvoiceUpsertDialog
      v-model:show="attachInvoiceDialog"
      v-model="invoiceForm"
      :default-customer="selfCustomer"
      :default-supplier="order.supplier"
      lock-customer
      title="Připojit fakturu"
      submit-label="Uložit fakturu"
      :loading="invoiceLoading"
      @submit="attachInvoice"
    />
    <AuditLogDialog
      v-model:show="auditDialog"
      source="inbound-order"
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
  type CustomerSchema,
  type GetCustomerResponse,
  warehouseApiRoutesInboundOrdersAddItemToInboundOrder,
  warehouseApiRoutesInboundOrdersGetInboundOrder,
  warehouseApiRoutesInboundOrdersGetInboundOrderPdf,
  warehouseApiRoutesInboundOrdersRemoveItemsFromInboundOrder,
  warehouseApiRoutesInboundOrdersTransitionInboundOrder,
  warehouseApiRoutesInboundOrdersUpdateInboundOrder,
  warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder,
  warehouseApiRoutesWarehouseCreateInboundWarehouseOrder,
  type GetInboundOrderResponse,
  type InboundOrderCreateOrUpdateSchema,
  type InboundOrderItemCreateSchema,
  type InboundOrderSchema,
  type InvoiceStoreSchema,
} from '@/client'
import { formDataBodySerializer } from '@/client/client'
import { client } from '@/client/client.gen'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import InboundOrderDetailsListCard from '@/components/order/InboundOrderDetailsListCard.vue'
import InboundOrderPutawayDialog from '@/components/order/InboundOrderPutawayDialog.vue'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import InboundOrderTimeline from '@/components/order/InboundOrderTimeline.vue'
import InboundOrderUpdateOrCreateDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import InvoiceUpsertDialog from '@/components/order/InvoiceUpsertDialog.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import NewOrderItemDialog from '@/components/order/NewOrderItemDialog.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import PrintDropdownButton from '@/components/PrintDropdownButton.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { getInboundOrderStep } from '@/constants/inbound-order'
import type { InvoiceUpsertSubmitPayload } from '@/components/order/invoice-upload'
import { toInvoiceMultipartBody } from '@/components/order/invoice-upload'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'

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

const selfCustomer = ref<CustomerSchema>()

const loadSelfCustomer = async () => {
  const response = await client.get<{ 200: GetCustomerResponse }>({
    security: [
      {
        in: 'cookie',
        name: 'sessionid',
        type: 'apiKey',
      },
    ],
    url: '/api/v1/customers/self',
  })
  const data = onResponse(response)
  if (data?.data) {
    selfCustomer.value = data.data
  }
}

await loadSelfCustomer()

const addItemDialog = ref(false)
const auditDialog = ref(false)
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

const reorderItems = async (items: NonNullable<InboundOrderSchema['items']>) => {
  if (!order.value) {
    return
  }

  const indexedItems = items.map((it, index) => ({ ...it, index }))
  order.value.items = indexedItems

  let hasError = false
  await Promise.all(
    indexedItems.map(async (item) => {
      const res = await warehouseApiRoutesInboundOrdersUpdateItemInInboundOrder({
        path: { order_code: order.value!.code },
        body: {
          product_code: item.product.code,
          product_name: item.product.name,
          amount: item.amount,
          total_price: item.total_price,
          unit_price: item.unit_price,
          index: item.index,
        },
      })
      const data = onResponse(res)
      if (!data?.data) {
        hasError = true
      }
    }),
  )

  if (hasError) {
    const refreshResponse = await warehouseApiRoutesInboundOrdersGetInboundOrder({
      path: { order_code: order.value.code },
    })
    const refreshData = onResponse(refreshResponse)
    if (refreshData?.data) {
      order.value = refreshData.data
    }
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
    body: { action: 'next' },
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
    body: { action: 'cancel' },
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
const createWarehouseOrder = async () => {
  if (!order.value) {
    return
  }

  const stateResponse = await warehouseApiRoutesInboundOrdersTransitionInboundOrder({
    path: { order_code: order.value.code },
    body: { action: 'next' },
  })
  const stateData = onResponse(stateResponse)
  if (!stateData?.data) {
    return
  }

  order.value = stateData.data

  const response = await warehouseApiRoutesWarehouseCreateInboundWarehouseOrder({
    body: { purchase_order_code: order.value.code },
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

const attachInvoiceDialog = ref(false)
const invoiceLoading = ref(false)

const createDefaultInvoiceForm = (): InvoiceStoreSchema => ({
  code: '',
  issued_date: new Date().toISOString().split('T')[0],
  due_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  taxable_supply_date: new Date().toISOString().split('T')[0],
  payment_method_name: '',
  currency: order.value?.currency ?? 'CZK',
  customer_code: selfCustomer.value?.code,
  supplier_code: order.value?.supplier.code,
  external_code: undefined,
  paid_date: undefined,
  note: undefined,
})

const invoiceForm = ref<InvoiceStoreSchema>(createDefaultInvoiceForm())

watch(attachInvoiceDialog, (isOpen) => {
  if (isOpen) {
    invoiceForm.value = createDefaultInvoiceForm()
  }
})

const attachInvoice = async (payload: InvoiceUpsertSubmitPayload) => {
  if (!order.value) {
    return
  }

  invoiceLoading.value = true
  try {
    const response = await client.post<{ 200: GetInboundOrderResponse }>({
      ...formDataBodySerializer,
      security: [
        {
          in: 'cookie',
          name: 'sessionid',
          type: 'apiKey',
        },
      ],
      headers: { 'Content-Type': null },
      url: '/api/v1/orders/{order_code}/invoice',
      path: { order_code: order.value.code },
      body: toInvoiceMultipartBody(payload),
    })
    const data = onResponse(response)
    if (data?.data) {
      order.value = data.data
      attachInvoiceDialog.value = false
      $q.notify({
        type: 'positive',
        message: 'Faktura byla připojena k objednávce.',
      })
    }
  } finally {
    invoiceLoading.value = false
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
