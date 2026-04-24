<template>
  <div class="flex-1">
    <div class="mb-2 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="min-w-0">
        <h1>Přehled objednávek</h1>
        <h5 class="mt-2 text-gray-5">Správa příchozích objednávek od zákazníků</h5>
        <div v-if="invoiceMode && selectedOrders.length" class="mt-3 text-sm text-gray-6">
          Vybráno {{ selectedOrders.length }} objednávek pro odběratele
          <span class="font-semibold text-primary">{{ selectedOrders[0].customer.name }}</span>
          v měně {{ selectedOrders[0].currency }}.
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <q-btn
          unelevated
          :color="invoiceMode ? 'grey-8' : 'secondary'"
          :icon="invoiceMode ? 'sym_o_close' : 'sym_o_receipt_long'"
          :label="invoiceMode ? 'ukončit výběr' : 'fakturace'"
          @click="toggleInvoiceMode"
        />
        <q-btn
          v-if="invoiceMode && selectedOrders.length"
          unelevated
          color="positive"
          icon="sym_o_post_add"
          label="vytvořit fakturu"
          @click="invoiceDialog = true"
        />
        <q-btn
          color="primary"
          unelevated
          label="vytvořit"
          icon="sym_o_add"
          @click="newOrderDialog = true"
        />
      </div>
    </div>

    <OutboundOrdersTable v-model:selected-orders="selectedOrders" :invoice-mode="invoiceMode" />

    <NewOrderDialog
      v-model="newOrderDialog"
      ref="newOrderDialogComponent"
      @create-order="createOrder"
    />

    <OutboundInvoiceCreateDialog
      v-model:show="invoiceDialog"
      :selected-orders="selectedOrders"
      :self-supplier="selfCustomer"
      :loading="invoiceLoading"
      @submit="createInvoice"
    />
  </div>
</template>

<script setup lang="ts">
import {
  type CustomerSchema,
  type GetCustomerResponse,
  warehouseApiRoutesInvoicesCreateOutboundInvoice,
  warehouseApiRoutesOutboundOrdersCreateOutboundOrder,
  type OutboundInvoiceCreateSchema,
  type OutboundOrderCreateOrUpdateSchema,
  type OutboundOrderSchema,
} from '@/client'
import { client } from '@/client/client.gen'
import OutboundInvoiceCreateDialog from '@/components/order/OutboundInvoiceCreateDialog.vue'
import NewOrderDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { useQuasar } from 'quasar'
import { ref } from 'vue'
import OutboundOrdersTable from './OutboundOrdersTable.vue'

const { onResponse } = useApi()

const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
const selectedOrders = ref<OutboundOrderSchema[]>([])
const invoiceMode = ref(false)
const invoiceDialog = ref(false)
const invoiceLoading = ref(false)
const selfCustomer = ref<CustomerSchema>()
const $q = useQuasar()

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

const toggleInvoiceMode = () => {
  invoiceMode.value = !invoiceMode.value
  if (!invoiceMode.value) {
    selectedOrders.value = []
    invoiceDialog.value = false
  }
}

const createOrder = async (params: OutboundOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesOutboundOrdersCreateOutboundOrder({ body: params })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `vydaná objednávka úspěšně vytvořena: ${data.data.code}`,
    })
    router.push({ name: 'outboundOrderDetail', params: { code: data.data.code } })
  }
}

const createInvoice = async (body: OutboundInvoiceCreateSchema) => {
  invoiceLoading.value = true
  try {
    const response = await warehouseApiRoutesInvoicesCreateOutboundInvoice({ body })
    const data = onResponse(response)
    if (!data?.data) {
      return
    }

    selectedOrders.value = []
    invoiceDialog.value = false
    invoiceMode.value = false
    $q.notify({
      type: 'positive',
      message: `Faktura byla vytvořena: ${data.data.code}`,
    })
    router.push({ name: 'invoiceDetail', params: { code: data.data.code } })
  } finally {
    invoiceLoading.value = false
  }
}
</script>

<style lang="scss" scoped></style>
