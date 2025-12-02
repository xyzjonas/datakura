<template>
  <div class="flex-1">
    <q-table
      :rows="orders"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné produkty nenalezeny"
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
      <template #top-right>
        <q-btn
          color="primary"
          outline
          label="Nová objednávka"
          icon="sym_o_add"
          @click="newOrderDialog = true"
        />
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
    </q-table>
    <NewOrderDialog
      v-model="newOrderDialog"
      @create-order="createOrder"
      ref="newOrderDialogComponent"
    ></NewOrderDialog>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOrdersCreateIncomingOrder,
  warehouseApiRoutesOrdersGetIncomingOrders,
  type IncomingOrderCreateOrUpdateSchema,
  type IncomingOrderSchema,
} from '@/client'
import NewOrderDialog from '@/components/order/NewOrderDialog.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search } = useQueryProducts()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const orders = ref<IncomingOrderSchema[]>([])
const loading = ref(false)
const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesOrdersGetIncomingOrders({
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
    name: 'created',
    field: 'created',
    label: 'Datum vytvoření',
    format: (val: string) =>
      `${new Date(val).toLocaleDateString()} - ${new Date(val).toLocaleTimeString()}`,
    align: 'left',
  },
  {
    name: 'externalCode',
    field: 'external_code',
    label: 'Externí kód',
    align: 'left',
  },
  {
    name: 'itemsCount',
    field: (order: IncomingOrderSchema) => order.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'supplier',
    field: (order: IncomingOrderSchema) => order.supplier.name,
    label: 'Dodavatel',
    align: 'left',
  },
]

const { onResponse } = useApi()
const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof NewOrderDialog>>()
const createOrder = async (params: IncomingOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesOrdersCreateIncomingOrder({ body: params })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    router.push({ name: 'incomingOrderDetail', params: { code: data.data.code } })
  }
}
</script>

<style lang="scss" scoped></style>
