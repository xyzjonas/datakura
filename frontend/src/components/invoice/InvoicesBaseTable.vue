<template>
  <q-table
    :rows="invoices"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    row-key="code"
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné faktury nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
    :grid="$q.screen.lt.sm"
  >
    <template #item="props">
      <div class="q-pa-xs col-12">
        <InvoiceGridCard :invoice="props.row" :direction="direction" />
      </div>
    </template>

    <template #body-cell-code="props">
      <q-td>
        <a class="link" @click="goToInvoice(props.row.code)">{{ props.row.code }}</a>
      </q-td>
    </template>

    <template #body-cell-partner="props">
      <q-td>
        <CustomerLink :customer="props.row[direction === 'outbound' ? 'customer' : 'supplier']" />
      </q-td>
    </template>

    <template #body-cell-dueDate="props">
      <q-td>
        <span v-if="new Date(props.row.due_date) < new Date()" class="text-negative">
          {{ props.row.due_date }} (po termínu)
        </span>
        <span v-else>
          {{ props.row.due_date }}
        </span>
      </q-td>
    </template>

    <template #body-cell-paid="props">
      <q-td>
        <q-badge v-if="props.row.paid_date" color="positive" label="Uhrazeno" />
        <q-badge v-else color="negative" label="Neuhrazeno" />
      </q-td>
    </template>
  </q-table>
</template>

<script setup lang="ts">
import type { InvoiceSchema } from '@/client'
import { useInvoicesQuery } from '@/composables/query/use-invoices-query'
import { useAppRouter } from '@/composables/use-app-router'
import { type QTableColumn, type QTableProps, useQuasar } from 'quasar'
import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import InvoiceGridCard from './InvoiceGridCard.vue'
import CustomerLink from '../links/CustomerLink.vue'

export type Pagination = NonNullable<QTableProps['pagination']>

const props = defineProps<{
  fetchInvoices: (pagination: Ref<Pagination>, loading: Ref<boolean>) => Promise<InvoiceSchema[]>
  direction: 'inbound' | 'outbound'
}>()

const { page, pageSize } = useInvoicesQuery()
const { goToInvoice } = useAppRouter()
const { currentRoute } = useRouter()
const $q = useQuasar()

const pagination = ref<Pagination>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const invoices = ref<InvoiceSchema[]>([])
const loading = ref(false)

const fetch = async () => {
  invoices.value = await props.fetchInvoices(pagination, loading)
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

watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetch()
  }
})

const resolvePartnerName = (invoice: InvoiceSchema) =>
  props.direction === 'outbound' ? (invoice.customer?.name ?? '-') : (invoice.supplier?.name ?? '-')

const columns = computed<QTableColumn[]>(() => [
  {
    name: 'code',
    field: 'code',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'paid',
    field: (row: InvoiceSchema) => !!row.paid_date,
    label: 'Zaplaceno',
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
    name: 'issuedDate',
    field: 'issued_date',
    label: 'Vystaveno',
    align: 'left',
  },
  {
    name: 'dueDate',
    field: 'due_date',
    label: 'Splatnost',
    align: 'left',
  },
  {
    name: 'externalCode',
    field: 'external_code',
    label: 'Externí kód',
    align: 'left',
  },
  {
    name: 'partner',
    field: resolvePartnerName,
    label: props.direction === 'outbound' ? 'Odběratel' : 'Dodavatel',
    align: 'left',
  },
  {
    name: 'paymentMethod',
    field: (invoice: InvoiceSchema) => invoice.payment_method.name,
    label: 'Platební metoda',
    align: 'left',
  },
  {
    name: 'currency',
    field: 'currency',
    label: 'Měna',
    align: 'left',
  },
])
</script>
