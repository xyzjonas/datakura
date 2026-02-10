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
      no-data-label="Žádné dobropisy nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat dobropis"
          clearable
          :debounce="300"
        ></SearchInput>
      </template>
      <template #body-cell-code="props">
        <q-td>
          <a
            @click="
              $router.push({
                name: entityRouteName,
                params: { code: props.row.code },
              })
            "
            class="link mr-2"
            >{{ props.row.code }}
          </a>
        </q-td>
      </template>
      <template #body-cell-order="props">
        <q-td>
          <a @click="goToOrderIn(props.row.order.code)" class="link mr-2"
            >{{ props.row.order.code }}
          </a>
          <InboundOrderStateBadge :state="props.row.order.state" />
        </q-td>
      </template>
      <template #body-cell-state="props">
        <q-td>
          <GenericStateBadge :state="props.row.state" />
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup lang="ts">
import { type CreditNoteSupplierSchema } from '@/client'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryProducts } from '@/composables/query/use-products-query'
import { useAppRouter } from '@/composables/use-app-router'
import { calculateTotalPrice } from '@/utils/total-price'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import GenericStateBadge from '../GenericStateBadge.vue'

const { page, pageSize, search } = useQueryProducts()

const { goToOrderIn } = useAppRouter()

export type Pagination = NonNullable<QTableProps['pagination']>

const pagination = ref<Pagination>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

// todo: 'or' + Outbound
type CreditNote = CreditNoteSupplierSchema

const props = defineProps<{
  fetchCreditNotes: (pagination: Ref<Pagination>, loading: Ref<boolean>) => Promise<CreditNote[]>
  entityRouteName: string
}>()

const orders = ref<CreditNote[]>([])
const loading = ref(false)

const fetch = async () => {
  orders.value = await props.fetchCreditNotes(pagination, loading)
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
    field: (note: CreditNote) => note.order.code,
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
    field: (note: CreditNote) => note.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'reason',
    field: 'reason',
    label: 'Důvod',
    align: 'left',
  },
  {
    name: 'supplier',
    field: (note: CreditNote) => note.order.supplier.name,
    label: 'Dodavatel',
    align: 'left',
  },
  {
    name: 'price',
    field: (note: CreditNote) => `${calculateTotalPrice(note.items)} ${note.order.currency}`,
    label: 'Celková částka',
    align: 'left',
  },
]
</script>

<style lang="scss" scoped></style>
