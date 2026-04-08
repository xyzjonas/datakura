<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled objednávek</h1>
        <h5 class="text-gray-5 mt-2">Správa příchozích objednávek od zákazníků</h5>
      </div>
      <q-btn
        color="primary"
        unelevated
        label="vytvořit"
        icon="sym_o_add"
        @click="newOrderDialog = true"
      />
    </div>

    <OrdersBaseTable
      :fetch-orders="fetchOrders"
      order-type="outbound"
      detail-route-name="outgoingOrderDetail"
      warehouse-detail-route-name="warehouseOutboundOrderDetail"
      warehouse-label="Výdejka"
      partner-label="Odběratel"
      partner-field="customer"
    />

    <NewOrderDialog
      v-model="newOrderDialog"
      @create-order="createOrder"
      ref="newOrderDialogComponent"
    ></NewOrderDialog>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersCreateOutboundOrder,
  warehouseApiRoutesOutboundOrdersGetOutboundOrders,
  type OutboundOrderCreateOrUpdateSchema,
} from '@/client'
import NewOrderDialog from '@/components/order/OutboundOrderUpdateOrCreateDialog.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { useQuasar } from 'quasar'
import { ref, type Ref } from 'vue'
import OrdersBaseTable, { type Pagination } from './OrdersBaseTable.vue'

const { onResponse } = useApi()
const { page, pageSize, search, stockProductCode } = useQueryProducts()

const fetchOrders = async (pagination: Ref<Pagination>, loading: Ref<boolean>) => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesOutboundOrdersGetOutboundOrders({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
        stock_product_code: stockProductCode.value ?? undefined,
      },
    })
    const data = onResponse(res)
    if (data) {
      pagination.value.rowsNumber = data.count
      return data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }

  return []
}

const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
const $q = useQuasar()
const createOrder = async (params: OutboundOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesOutboundOrdersCreateOutboundOrder({ body: params })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `vydaná objednávka úspěšně vytvořena: ${data.data.code}`,
    })
    router.push({ name: 'outgoingOrderDetail', params: { code: data.data.code } })
  }
}
</script>

<style lang="scss" scoped></style>
