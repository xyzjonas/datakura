<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled vydaných objednávek</h1>
        <h5 class="text-gray-5 mt-2">Správa nákupních objednávek směřujících k dodavatelům</h5>
      </div>
      <q-btn
        color="primary"
        unelevated
        label="vytvořit"
        icon="sym_o_add"
        @click="newOrderDialog = true"
      />
    </div>
    <OrdersBaseTable :fetch-orders="fetchOrders" />
    <!-- <q-table
      :rows="orders"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné vydané objednávky nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat objednávku"
          clearable
          :debounce="300"
        ></SearchInput>
      </template>
      <template #body-cell-code="props">
        <q-td>
          <a
            @click="
              $router.push({
                name: 'incomingOrderDetail',
                params: { code: props.row.code },
              })
            "
            class="link"
            >{{ props.row.code }}</a
          >
        </q-td>
      </template>
      <template #body-cell-state="props">
        <q-td>
          <InboundOrderStateBadge :state="props.row.state" />
        </q-td>
      </template>
      <template #body-cell-warehouseOrder="props">
        <q-td>
          <a
            v-if="props.row.warehouse_order?.code"
            class="link"
            @click="
              $router.push({
                name: 'warehouseInboundOrderDetail',
                params: { code: props.row.warehouse_order.code },
              })
            "
            >{{ props.row.warehouse_order.code }}
            <InboundWarehouseOrderStateBadge :state="props.row.warehouse_order.state" class="ml-1"
          /></a>
        </q-td>
      </template>
    </q-table> -->
    <NewOrderDialog
      v-model="newOrderDialog"
      @create-order="createOrder"
      ref="newOrderDialogComponent"
    ></NewOrderDialog>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersCreateInboundOrder,
  warehouseApiRoutesInboundOrdersGetInboundOrders,
  type InboundOrderCreateOrUpdateSchema,
} from '@/client'
import NewOrderDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { useQuasar } from 'quasar'
import { ref, type Ref } from 'vue'
import OrdersBaseTable, { type Pagination } from './OrdersBaseTable.vue'

const { onResponse } = useApi()
const { page, pageSize, search } = useQueryProducts()

// const pagination = ref<NonNullable<QTableProps['pagination']>>({
//   rowsPerPage: pageSize.value,
//   page: page.value,
//   rowsNumber: pageSize.value,
// })

// const orders = ref<InboundOrderSchema[]>([])
// const loading = ref(false)
const fetchOrders = async (pagination: Ref<Pagination>, loading: Ref<boolean>) => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesInboundOrdersGetInboundOrders({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
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

// onMounted(fetchOrders)

// const shouldNotFetch = () => {
//   return pagination.value.rowsPerPage === pageSize.value && pagination.value.page === page.value
// }

// const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
//   if (!requestProp.pagination) {
//     return
//   }
//   pagination.value = requestProp.pagination
//   if (shouldNotFetch()) {
//     return
//   }
//   page.value = Number(pagination.value.page)
//   setTimeout(() => (pageSize.value = Number(pagination.value.rowsPerPage)), 1)
//   setTimeout(() => fetchOrders(), 2)
// }

// const { currentRoute } = useRouter()
// watch(currentRoute, () => {
//   if (!shouldNotFetch()) {
//     fetchOrders()
//   }
// })

// watch(search, fetchOrders)

// const columns: QTableColumn[] = [
//   {
//     name: 'code',
//     field: 'code',
//     label: 'Kód',
//     align: 'left',
//   },
//   {
//     name: 'state',
//     field: 'state',
//     label: 'Stav',
//     align: 'left',
//   },
//   {
//     name: 'warehouseOrder',
//     field: (order: InboundOrderSchema) => order.warehouse_order_code,
//     label: 'Příjemka',
//     align: 'left',
//   },
//   {
//     name: 'created',
//     field: 'created',
//     label: 'Datum vytvoření',
//     format: (val: string) =>
//       `${new Date(val).toLocaleDateString()} - ${new Date(val).toLocaleTimeString()}`,
//     align: 'left',
//   },
//   {
//     name: 'externalCode',
//     field: 'external_code',
//     label: 'Externí kód',
//     align: 'left',
//   },
//   {
//     name: 'itemsCount',
//     field: (order: InboundOrderSchema) => order.items?.length ?? 0,
//     label: 'Počet položek',
//     align: 'left',
//   },
//   {
//     name: 'supplier',
//     field: (order: InboundOrderSchema) => order.supplier.name,
//     label: 'Dodavatel',
//     align: 'left',
//   },
// ]

const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
const $q = useQuasar()
const createOrder = async (params: InboundOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesInboundOrdersCreateInboundOrder({ body: params })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `vydaná objednávka úspěšně vytvořena: ${data.data.code}`,
    })
    router.push({ name: 'incomingOrderDetail', params: { code: data.data.code } })
  }
}
</script>

<style lang="scss" scoped></style>
