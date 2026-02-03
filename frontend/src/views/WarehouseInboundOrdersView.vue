<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Příjemky</h1>
        <h5 class="text-gray-5 mt-2">Soupis aktivních příjemek</h5>
      </div>
      <!-- <q-btn color="primary" unelevated label="vytvořit" icon="sym_o_add" disable /> -->
    </div>
    <q-table
      :rows="orders"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné příjemky nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat příjemku"
          clearable
          :debounce="300"
        ></SearchInput>
      </template>
      <template #body-cell-code="props">
        <q-td>
          <a
            @click="
              $router.push({
                name: 'warehouseInboundOrderDetail',
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
          <InboundWarehouseOrderStateBadge :state="props.row.state" />
        </q-td>
      </template>
      <template #body-cell-order="props">
        <q-td>
          <a
            class="link"
            @click="
              $router.push({
                name: 'incomingOrderDetail',
                params: { code: props.row.order.code },
              })
            "
            >{{ props.row.order.code }}</a
          >
        </q-td>
      </template>
      <template #body-cell-completedCount="props">
        <q-td>
          <q-badge>
            {{ props.row.completed_items_count }} / {{ props.row.items?.length ?? 0 }}
          </q-badge>
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetInboundWarehouseOrders,
  type InboundWarehouseOrderSchema,
} from '@/client'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search } = useQueryProducts()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const orders = ref<InboundWarehouseOrderSchema[]>([])
const loading = ref(false)
const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesWarehouseGetInboundWarehouseOrders({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      orders.value = res.data.data
      pagination.value.rowsNumber = res.data.count
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchOrders)

const shouldNotFetch = () => {
  return pagination.value.rowsPerPage === pageSize.value && pagination.value.page === page.value
}

const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
  if (!requestProp.pagination) {
    return
  }
  pagination.value = requestProp.pagination
  if (shouldNotFetch()) {
    return
  }
  page.value = Number(pagination.value.page)
  setTimeout(() => (pageSize.value = Number(pagination.value.rowsPerPage)), 1)
  setTimeout(() => fetchOrders(), 2)
}

const { currentRoute } = useRouter()
watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetchOrders()
  }
})

watch(search, fetchOrders)

const columns: QTableColumn[] = [
  {
    name: 'code',
    field: 'code',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'state',
    field: 'state',
    label: 'Stav',
    align: 'left',
  },
  {
    name: 'order',
    field: (order: InboundWarehouseOrderSchema) => order.order.code,
    label: 'Objednávka',
    align: 'left',
  },
  {
    name: 'created',
    field: 'created',
    label: 'Datum vytvoření',
    format: (val: string) =>
      `${new Date(val).toLocaleDateString()} - ${new Date(val).toLocaleTimeString()}`,
    align: 'left',
  },
  {
    name: 'itemsCount',
    field: (order: InboundWarehouseOrderSchema) => order.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'completedCount',
    field: (order: InboundWarehouseOrderSchema) => order.completed_items_count,
    label: 'Provedené pohyby',
    align: 'left',
  },
  {
    name: 'supplier',
    field: (order: InboundWarehouseOrderSchema) => order.order.supplier.name,
    label: 'Dodavatel',
    align: 'left',
  },
]

// const { onResponse } = useApi()
// const newOrderDialog = ref(false)
// const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
// const $q = useQuasar()
// const createOrder = async (params: InboundOrderCreateOrUpdateSchema) => {
//   const response = await warehouseApiRoutesOrdersCreateInboundOrder({ body: params })
//   const data = onResponse(response)
//   if (data && newOrderDialogComponent.value) {
//     newOrderDialogComponent.value.reset()
//     $q.notify({
//       type: 'positive',
//       message: `Objednávka úspěšně vytvořena: ${data.data.code}`,
//     })
//     router.push({ name: 'incomingOrderDetail', params: { code: data.data.code } })
//   }
// }
</script>

<style lang="scss" scoped></style>
