<template>
  <div class="flex-1">
    <q-table
      :rows="customers"
      :columns="columns"
      :loading="loading"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádní zákazníci nenalezeni"
      loading-label="Načítám"
      :rows-per-page-options="[10, 20, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat zákazníka"
          clearable
          :debounce="300"
        ></SearchInput>
      </template>
      <template #body-cell-name="props">
        <q-td class="flex items-center gap-2">
          <CustomerTypeIcon
            :type="props.row.customer_type"
            class="text-lg light:text-primary dark:text-light"
          />
          <a
            @click="
              $router.push({
                name: 'customerDetail',
                params: { customerCode: props.row.code },
              })
            "
            class="link"
          >
            {{ props.row.name }}</a
          >
        </q-td>
      </template>
      <template #body-cell-type="props">
        <q-td auto-width>
          <CustomerTypeIcon :type="props.row.customer_type" class="text-lg" />
          <span class="lowercase ml-2">{{ props.row.customer_type }}</span>
        </q-td>
      </template>
    </q-table>
  </div>
</template>

<script setup lang="ts">
import { warehouseApiRoutesCustomerGetCustomers, type CustomerSchema } from '@/client'
import CustomerTypeIcon from '@/components/customer/CustomerTypeIcon.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryCustomers } from '@/composables/query/use-customers-query'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search } = useQueryCustomers()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const customers = ref<CustomerSchema[]>([])
const loading = ref(false)
const fetchCustomers = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesCustomerGetCustomers({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.error) {
      return
    }
    pagination.value.rowsNumber = res.data?.count
    customers.value = res.data?.data ?? []
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchCustomers)

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
  setTimeout(() => fetchCustomers(), 2)
}

const { currentRoute } = useRouter()
watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetchCustomers()
  }
})

watch(search, () => {
  fetchCustomers()
})

const columns: QTableColumn[] = [
  {
    name: 'name',
    field: 'name',
    label: 'Název',
    align: 'left',
  },
  {
    name: 'code',
    field: 'code',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'id',
    field: 'identification',
    label: 'IČO',
    align: 'left',
  },
  {
    name: 'taxId',
    field: (cust: CustomerSchema) => (cust.tax_identification ? cust.tax_identification : '-'),
    label: 'DIČ',
    align: 'right',
  },
  // {
  //   name: 'type',
  //   field: (cust: CustomerSchema) => cust.customer_type.toLowerCase(),
  //   label: 'Typ',
  //   align: 'left',
  // },
]
</script>

<style lang="scss" scoped></style>
