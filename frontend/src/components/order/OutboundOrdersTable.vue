<template>
  <q-table
    :rows="orders"
    :columns="columns"
    :loading="loading"
    loading-label="Nacitam"
    flat
    row-key="code"
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Zadne objednavky nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
    :grid="$q.screen.lt.sm"
  >
    <template #top-left>
      <div class="flex gap-2 items-start flex-wrap">
        <SearchInput
          v-model="search"
          placeholder="Vyhledat objednavku"
          clearable
          :debounce="300"
          class="min-w-[260px] flex-1"
        />
        <StockProductSearchSelect
          v-model="stockProductCode"
          label="Produkt v objednavce"
          hint=""
          class="min-w-[300px] flex-1"
        />
      </div>
    </template>

    <template #item="props">
      <div class="q-pa-xs col-12">
        <div class="flex items-start gap-3">
          <div
            v-if="invoiceMode"
            class="mt-4 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#d8e2ec] bg-white"
          >
            <q-checkbox
              :model-value="isSelected(props.row.code)"
              :disable="!canSelect(props.row)"
              @update:model-value="(checked) => toggleOrderSelection(props.row, checked)"
            />
            <q-tooltip v-if="getSelectionReason(props.row)">
              {{ getSelectionReasonLabel(props.row) }}
            </q-tooltip>
          </div>
          <component
            :is="OutboundOrderGridCard"
            :order="props.row"
            detail-route-name="outboundOrderDetail"
            class="flex-1"
          />
        </div>
      </div>
    </template>

    <template #header-cell-select>
      <q-th auto-width>
        <q-checkbox
          v-if="invoiceMode"
          :model-value="allVisibleSelected"
          :indeterminate="someVisibleSelected && !allVisibleSelected"
          :disable="visibleSelectableOrders.length === 0"
          @update:model-value="toggleVisibleSelection"
        />
      </q-th>
    </template>

    <template #body-cell-select="props">
      <q-td auto-width>
        <div class="flex justify-center">
          <q-checkbox
            v-if="invoiceMode"
            :model-value="isSelected(props.row.code)"
            :disable="!canSelect(props.row)"
            @update:model-value="(checked) => toggleOrderSelection(props.row, checked)"
          />
          <q-tooltip v-if="getSelectionReason(props.row)">
            {{ getSelectionReasonLabel(props.row) }}
          </q-tooltip>
        </div>
      </q-td>
    </template>

    <template #body-cell-code="props">
      <q-td>
        <a
          class="link"
          @click="router.push({ name: 'outboundOrderDetail', params: { code: props.row.code } })"
        >
          {{ props.row.code }}
        </a>
      </q-td>
    </template>

    <template #body-cell-state="props">
      <q-td>
        <OutboundOrderStateBadge :state="props.row.state" />
      </q-td>
    </template>

    <template #body-cell-customer="props">
      <q-td>
        <CustomerLink :customer="props.row.customer" />
      </q-td>
    </template>

    <template #body-cell-warehouseOrder="props">
      <q-td>
        <a
          v-if="primaryWarehouseOrder(props.row)"
          class="link"
          @click="
            router.push({
              name: 'warehouseOutboundOrderDetail',
              params: { code: primaryWarehouseOrder(props.row)?.code },
            })
          "
        >
          {{ primaryWarehouseOrder(props.row)?.code }}
          <OutboundWarehouseOrderStateBadge
            :state="primaryWarehouseOrder(props.row)?.state ?? 'pending'"
            class="ml-1"
          />
        </a>
      </q-td>
    </template>
  </q-table>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesOutboundOrdersGetOutboundOrders,
  type OutboundOrderSchema,
} from '@/client'
import OutboundOrderGridCard from '@/components/order/OutboundOrderGridCard.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import OutboundWarehouseOrderStateBadge from '@/components/putaway/OutboundWarehouseOrderStateBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import StockProductSearchSelect from '@/components/selects/StockProductSearchSelect.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useApi } from '@/composables/use-api'
import { calculateTotalPrice } from '@/utils/total-price'
import { useQuasar, type QTableColumn, type QTableProps } from 'quasar'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import CustomerLink from '../links/CustomerLink.vue'
import {
  canGroupOutboundOrderForInvoice,
  getOutboundInvoiceSelectionBlockReason,
  outboundInvoiceSelectionReasonLabel,
} from './outbound-invoice'

export type Pagination = NonNullable<QTableProps['pagination']>

const props = withDefaults(
  defineProps<{
    invoiceMode?: boolean
  }>(),
  {
    invoiceMode: false,
  },
)

const selectedOrders = defineModel<OutboundOrderSchema[]>('selectedOrders', { default: [] })

const { page, pageSize, search, stockProductCode } = useQueryProducts()
const { onResponse } = useApi()
const router = useRouter()
const $q = useQuasar()

const pagination = ref<Pagination>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const orders = ref<OutboundOrderSchema[]>([])
const loading = ref(false)

const fetchOrders = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesOutboundOrdersGetOutboundOrders({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
        stock_product_code: stockProductCode.value ?? undefined,
      },
    })
    const data = onResponse(response)
    if (data) {
      pagination.value.rowsNumber = data.count
      orders.value = data.data
      syncSelection()
      return
    }

    orders.value = []
    syncSelection()
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

watch(search, fetchOrders)
watch(stockProductCode, fetchOrders)

watch(
  () => props.invoiceMode,
  (isEnabled) => {
    if (!isEnabled) {
      selectedOrders.value = []
    }
  },
)

const selectionAnchor = computed(() => selectedOrders.value[0])

const syncSelection = () => {
  const rowsByCode = new Map(orders.value.map((order) => [order.code, order]))
  selectedOrders.value = selectedOrders.value
    .map((order) => rowsByCode.get(order.code))
    .filter((order): order is OutboundOrderSchema => !!order)

  if (!selectedOrders.value.length) {
    return
  }

  const anchor = selectedOrders.value[0]
  selectedOrders.value = selectedOrders.value.filter((order) =>
    canGroupOutboundOrderForInvoice(order, anchor),
  )
}

const getSelectionReason = (order: OutboundOrderSchema) =>
  getOutboundInvoiceSelectionBlockReason(order, selectionAnchor.value)

const getSelectionReasonLabel = (order: OutboundOrderSchema) => {
  const reason = getSelectionReason(order)
  return reason ? outboundInvoiceSelectionReasonLabel[reason] : ''
}

const canSelect = (order: OutboundOrderSchema) => !getSelectionReason(order)

const isSelected = (code: string) => selectedOrders.value.some((order) => order.code === code)

const toggleOrderSelection = (order: OutboundOrderSchema, checked: boolean) => {
  if (!canSelect(order) && checked) {
    return
  }

  if (checked) {
    if (!isSelected(order.code)) {
      selectedOrders.value = [...selectedOrders.value, order]
    }
    return
  }

  selectedOrders.value = selectedOrders.value.filter(
    (selectedOrder) => selectedOrder.code !== order.code,
  )
}

const visibleSelectionAnchor = computed(() => {
  if (selectionAnchor.value) {
    return selectionAnchor.value
  }

  return orders.value.find((order) => canGroupOutboundOrderForInvoice(order))
})

const visibleSelectableOrders = computed(() => {
  if (!visibleSelectionAnchor.value) {
    return []
  }

  return orders.value.filter((order) =>
    canGroupOutboundOrderForInvoice(order, visibleSelectionAnchor.value),
  )
})

const allVisibleSelected = computed(
  () =>
    visibleSelectableOrders.value.length > 0 &&
    visibleSelectableOrders.value.every((order) => isSelected(order.code)),
)

const someVisibleSelected = computed(() =>
  visibleSelectableOrders.value.some((order) => isSelected(order.code)),
)

const toggleVisibleSelection = (checked: boolean) => {
  if (!visibleSelectionAnchor.value) {
    return
  }

  if (!checked) {
    const visibleCodes = new Set(visibleSelectableOrders.value.map((order) => order.code))
    selectedOrders.value = selectedOrders.value.filter((order) => !visibleCodes.has(order.code))
    return
  }

  const selectedCodes = new Set(selectedOrders.value.map((order) => order.code))
  selectedOrders.value = [
    ...selectedOrders.value,
    ...visibleSelectableOrders.value.filter((order) => !selectedCodes.has(order.code)),
  ]
}

const primaryWarehouseOrder = (order: OutboundOrderSchema) => {
  const warehouseOrders = order.warehouse_orders ?? []
  return (
    warehouseOrders.find((warehouseOrder) => warehouseOrder.state !== 'completed') ??
    warehouseOrders[0]
  )
}

const columns = computed<QTableColumn[]>(() => {
  const baseColumns: QTableColumn[] = [
    {
      name: 'code',
      field: 'code',
      label: 'Kod',
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
      field: (order: OutboundOrderSchema) => order.warehouse_order_codes?.join(', '),
      label: 'Vydejka',
      align: 'left',
    },
    {
      name: 'created',
      field: 'created',
      label: 'Datum vytvoreni',
      format: (val: string) =>
        `${new Date(val).toLocaleDateString()} - ${new Date(val).toLocaleTimeString()}`,
      align: 'left',
    },
    {
      name: 'externalCode',
      field: 'external_code',
      label: 'Externi kod',
      align: 'left',
    },
    {
      name: 'itemsCount',
      field: (order: OutboundOrderSchema) => order.items?.length ?? 0,
      label: 'Pocet polozek',
      align: 'left',
    },
    {
      name: 'customer',
      field: (order: OutboundOrderSchema) => order.customer.name,
      label: 'Odberatel',
      align: 'left',
    },
    {
      name: 'price',
      field: (order: OutboundOrderSchema) =>
        `${calculateTotalPrice(order.items)} ${order.currency}`,
      label: 'Celkova castka',
      align: 'left',
    },
  ]

  if (!props.invoiceMode) {
    return baseColumns
  }

  return [
    {
      name: 'select',
      field: 'select',
      label: '',
      align: 'left',
    },
    ...baseColumns,
  ]
})

defineExpose({
  refresh: fetchOrders,
})
</script>
