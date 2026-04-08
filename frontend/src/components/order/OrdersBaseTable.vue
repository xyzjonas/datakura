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
                name: detailRouteName,
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
          <component :is="orderStateBadgeComponent" :state="props.row.state" />
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
                name: warehouseDetailRouteName,
                params: {
                  code: props.row.warehouse_orders.filter(
                    (order: { state: string; code: string }) => order.state !== 'completed',
                  )[0].code,
                },
              })
            "
            >{{
              props.row.warehouse_orders.filter(
                (order: { state: string; code: string }) => order.state !== 'completed',
              )[0].code
            }}
            <component
              :is="warehouseOrderStateBadgeComponent"
              :state="
                props.row.warehouse_orders.filter(
                  (order: { state: string; code: string }) => order.state !== 'completed',
                )[0].state
              "
              class="ml-1"
          /></a>
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup lang="ts">
import { type InboundOrderSchema, type OutboundOrderSchema } from '@/client'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import OutboundWarehouseOrderStateBadge from '@/components/putaway/OutboundWarehouseOrderStateBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import StockProductSearchSelect from '@/components/selects/StockProductSearchSelect.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { calculateTotalPrice } from '@/utils/total-price'
import { type QTableColumn, type QTableProps } from 'quasar'
import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search, stockProductCode } = useQueryProducts()

export type Pagination = NonNullable<QTableProps['pagination']>

const pagination = ref<Pagination>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

type Order = InboundOrderSchema | OutboundOrderSchema

const props = defineProps<{
  fetchOrders: (pagination: Ref<Pagination>, loading: Ref<boolean>) => Promise<Order[]>
  orderType?: 'inbound' | 'outbound'
  detailRouteName?: string
  warehouseDetailRouteName?: string
  warehouseLabel?: string
  partnerLabel?: string
  partnerField?: 'supplier' | 'customer'
}>()

const orderType = props.orderType ?? 'inbound'
const detailRouteName = props.detailRouteName ?? 'incomingOrderDetail'
const warehouseDetailRouteName = props.warehouseDetailRouteName ?? 'warehouseInboundOrderDetail'
const warehouseLabel = props.warehouseLabel ?? 'Příjemka'
const partnerLabel = props.partnerLabel ?? 'Dodavatel'
const partnerField = props.partnerField ?? 'supplier'
const orderStateBadgeComponent = computed(() =>
  orderType === 'outbound' ? OutboundOrderStateBadge : InboundOrderStateBadge,
)
const warehouseOrderStateBadgeComponent = computed(() =>
  orderType === 'outbound' ? OutboundWarehouseOrderStateBadge : InboundWarehouseOrderStateBadge,
)

const orders = ref<Order[]>([])
const loading = ref(false)

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
    label: warehouseLabel,
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
    name: 'partner',
    field: (order: Order) =>
      partnerField === 'supplier'
        ? ((order as InboundOrderSchema).supplier?.name ?? '')
        : ((order as OutboundOrderSchema).customer?.name ?? ''),
    label: partnerLabel,
    align: 'left',
  },
  {
    name: 'price',
    field: (order: InboundOrderSchema) => `${calculateTotalPrice(order.items)} ${order.currency}`,
    label: 'Celková částka',
    align: 'left',
  },
]
</script>

<style lang="scss" scoped></style>
