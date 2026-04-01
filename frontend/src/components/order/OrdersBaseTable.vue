<template>
  <div>
    <q-table
      :rows="orders"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné objednávky nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <div class="flex gap-2 items-start flex-wrap">
          <SearchInput
            v-model="search"
            placeholder="Vyhledat objednávku"
            clearable
            :debounce="300"
            class="min-w-[260px]"
          ></SearchInput>
          <StockProductSearchSelect
            v-model="stockProductCode"
            label="Produkt v objednávce"
            hint=""
            class="min-w-[300px]"
          />
        </div>
      </template>
      <!-- <template #top-right>
        <q-btn color="gray" unelevated label="vytvořit" disable @click="newOrderDialog = true" />
      </template> -->
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
            v-if="
              props.row.warehouse_orders.filter(
                (order: InboundOrderSchema) => order.state !== 'completed',
              ).length > 0
            "
            class="link"
            @click="
              $router.push({
                name: 'warehouseInboundOrderDetail',
                params: {
                  code: props.row.warehouse_orders.filter(
                    (order: InboundOrderSchema) => order.state !== 'completed',
                  )[0].code,
                },
              })
            "
            >{{
              props.row.warehouse_orders.filter(
                (order: InboundOrderSchema) => order.state !== 'completed',
              )[0].code
            }}
            <InboundWarehouseOrderStateBadge
              :state="
                props.row.warehouse_orders.filter(
                  (order: InboundOrderSchema) => order.state !== 'completed',
                )[0].state
              "
              class="ml-1"
          /></a>
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
  warehouseApiRoutesInboundOrdersCreateInboundOrder,
  type InboundOrderCreateOrUpdateSchema,
  type InboundOrderSchema,
} from '@/client'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import NewOrderDialog from '@/components/order/InboundOrderUpdateOrCreateDialog.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import StockProductSearchSelect from '@/components/selects/StockProductSearchSelect.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import { calculateTotalPrice } from '@/utils/total-price'
import { useQuasar, type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'

const { onResponse } = useApi()
const { page, pageSize, search, stockProductCode } = useQueryProducts()

export type Pagination = NonNullable<QTableProps['pagination']>

const pagination = ref<Pagination>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

// todo: 'or' Outbound
type Order = InboundOrderSchema

const props = defineProps<{
  fetchOrders: (pagination: Ref<Pagination>, loading: Ref<boolean>) => Promise<Order[]>
}>()

const orders = ref<Order[]>([])
const loading = ref(false)
// const fetchOrders = async () => {
//   loading.value = true
//   try {
//     const res = await warehouseApiRoutesInboundOrdersGetInboundOrders({
//       query: {
//         page: page.value,
//         page_size: pageSize.value,
//         search_term: search.value,
//       },
//     })
//     const data = onResponse(res)
//     if (data) {
//       orders.value = data.data
//       pagination.value.rowsNumber = data.count
//     }
//   } finally {
//     setTimeout(() => (loading.value = false), 300)
//   }
// }

const fetch = async () => {
  orders.value = await props.fetchOrders(pagination, loading)
}

onMounted(fetch)

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
  setTimeout(() => fetch(), 2)
}

const { currentRoute } = useRouter()
watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetch()
  }
})

watch(search, fetch)
watch(stockProductCode, fetch)

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
    name: 'warehouseOrder',
    field: (order: InboundOrderSchema) => order.warehouse_order_codes?.join(', '),
    label: 'Příjemka',
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
    field: (order: InboundOrderSchema) => order.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'supplier',
    field: (order: InboundOrderSchema) => order.supplier.name,
    label: 'Dodavatel',
    align: 'left',
  },
  {
    name: 'price',
    field: (order: InboundOrderSchema) => `${calculateTotalPrice(order.items)} ${order.currency}`,
    label: 'Celková částka',
    align: 'left',
  },
]

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
