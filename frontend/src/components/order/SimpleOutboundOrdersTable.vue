<template>
  <q-table
    :rows="orders"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné objednávky nenalezeny"
    :rows-per-page-options="[5]"
    class="bg-transparent"
    :grid="forceGrid || $q.screen.lt.md"
  >
    <template #item="props">
      <div class="q-pa-xs col-12">
        <OutboundOrderGridCard :order="props.row" detail-route-name="outboundOrderDetail" />
      </div>
    </template>

    <template v-if="!hideSearch" #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat objednávku"
        clearable
        :debounce="300"
        class="min-w-[260px]"
      />
    </template>

    <template #body-cell-code="props">
      <q-td>
        <a
          @click="
            $router.push({
              name: 'outboundOrderDetail',
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
        <OutboundOrderStateBadge :state="props.row.state" />
      </q-td>
    </template>
  </q-table>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersGetOutboundOrders,
  type OutboundOrderSchema,
  type PagedOutboundOrderSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import OutboundOrderGridCard from '@/components/order/OutboundOrderGridCard.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import { useApi } from '@/composables/use-api'
import { calculateTotalPrice } from '@/utils/total-price'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  stockProductCode: string
  hideSearch?: boolean
  forceGrid?: boolean
}>()

type Pagination = NonNullable<QTableProps['pagination']>

const pagination = ref<Pagination>({
  rowsPerPage: 5,
  page: 1,
  rowsNumber: 0,
})

const search = ref('')
const loading = ref(false)
const orders = ref<OutboundOrderSchema[]>([])

const { onResponse } = useApi()

const fetchOrders = async () => {
  loading.value = true
  try {
    const result = await warehouseApiRoutesOutboundOrdersGetOutboundOrders({
      query: {
        page: Number(pagination.value.page),
        page_size: Number(pagination.value.rowsPerPage),
        search_term: search.value || undefined,
        stock_product_code: props.stockProductCode,
      },
    })

    const data = onResponse(result) as PagedOutboundOrderSchema | undefined
    if (!data) {
      orders.value = []
      pagination.value.rowsNumber = 0
      return
    }

    orders.value = data.data
    pagination.value.rowsNumber = data.count
  } finally {
    setTimeout(() => (loading.value = false), 250)
  }
}

const onPaginationChange = (request: { pagination: QTableProps['pagination'] }) => {
  if (!request.pagination) {
    return
  }
  pagination.value = request.pagination
  fetchOrders()
}

watch(search, () => {
  pagination.value.page = 1
  fetchOrders()
})

watch(
  () => props.stockProductCode,
  () => {
    pagination.value.page = 1
    fetchOrders()
  },
)

onMounted(fetchOrders)

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
    name: 'created',
    field: 'created',
    label: 'Datum vytvoření',
    format: (value: string) =>
      `${new Date(value).toLocaleDateString()} - ${new Date(value).toLocaleTimeString()}`,
    align: 'left',
  },
  {
    name: 'customer',
    field: (order: OutboundOrderSchema) => order.customer.name,
    label: 'Odběratel',
    align: 'left',
  },
  {
    name: 'itemsCount',
    field: (order: OutboundOrderSchema) => order.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'price',
    field: (order: OutboundOrderSchema) => `${calculateTotalPrice(order.items)} ${order.currency}`,
    label: 'Celková částka',
    align: 'left',
  },
]
</script>
