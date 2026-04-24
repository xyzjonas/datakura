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
      <template #top-right>
        <q-btn color="primary" unelevated icon="add" label="vytvořit" @click="onCreateCustomer" />
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

      <template #body-cell-discountGroup="props">
        <q-td>
          <span v-if="props.row.discount_group">
            {{ props.row.discount_group.name }} ({{ props.row.discount_group.discount_percent }} %)
          </span>
          <span v-else>—</span>
        </q-td>
      </template>
    </q-table>
  </div>

  <CustomerUpsertDialog
    v-model:show="showCreateDialog"
    v-model="newCustomer"
    :customer-groups="customerGroups"
    title="Nový zákazník"
    submit-label="vytvořit"
    :loading="savingCustomer"
    @submit="onSaveCustomer"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCustomerCreateCustomer,
  warehouseApiRoutesCustomerGroupsGetCustomerGroups,
  warehouseApiRoutesCustomerGetCustomers,
  type CustomerCreateOrUpdateSchema,
  type CustomerGroupSchema,
  type CustomerSchema,
} from '@/client'
import CustomerUpsertDialog from '@/components/customer/CustomerUpsertDialog.vue'
import CustomerTypeIcon from '@/components/customer/CustomerTypeIcon.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { useQueryCustomers } from '@/composables/query/use-customers-query'
import { type QTableColumn, type QTableProps, useQuasar } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { page, pageSize, search } = useQueryCustomers()
const { onResponse } = useApi()
const $q = useQuasar()
const router = useRouter()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const customers = ref<CustomerSchema[]>([])
const customerGroups = ref<CustomerGroupSchema[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const savingCustomer = ref(false)
const newCustomer = ref<CustomerCreateOrUpdateSchema>({
  code: '',
  name: '',
  customer_type: 'FIRMA',
  price_type: 'FIRMY',
  customer_group_code: '',
  invoice_due_days: 30,
  block_after_due_days: 30,
  is_self: false,
  default_payment_method_name: undefined,
  state: 'CZ',
  data_collection_agreement: false,
  marketing_data_use_agreement: false,
  is_valid: true,
  is_deleted: false,
})

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

const fetchCustomerGroups = async () => {
  const result = await warehouseApiRoutesCustomerGroupsGetCustomerGroups({
    query: { page: 1, page_size: 200 },
  })
  if (result.data?.data) {
    customerGroups.value = result.data.data
  }
}

const resetNewCustomer = () => {
  newCustomer.value = {
    code: '',
    name: '',
    customer_type: 'FIRMA',
    price_type: 'FIRMY',
    customer_group_code: '',
    invoice_due_days: 30,
    block_after_due_days: 30,
    is_self: false,
    default_payment_method_name: undefined,
    state: 'CZ',
    data_collection_agreement: false,
    marketing_data_use_agreement: false,
    is_valid: true,
    is_deleted: false,
  }
}

const onCreateCustomer = () => {
  resetNewCustomer()
  showCreateDialog.value = true
}

const onSaveCustomer = async (body: CustomerCreateOrUpdateSchema) => {
  savingCustomer.value = true
  try {
    const result = await warehouseApiRoutesCustomerCreateCustomer({ body })
    const response = onResponse(result)
    if (!response?.data) {
      return
    }

    showCreateDialog.value = false
    await fetchCustomers()
    $q.notify({ type: 'positive', message: 'Zákazník byl vytvořen.' })
    await router.push({
      name: 'customerDetail',
      params: { customerCode: response.data.code },
    })
  } finally {
    savingCustomer.value = false
  }
}

onMounted(fetchCustomers)
onMounted(fetchCustomerGroups)

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

const { currentRoute } = router
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
  {
    name: 'discountGroup',
    field: (cust: CustomerSchema) => cust.discount_group?.name ?? '-',
    label: 'Slevová skupina',
    align: 'left',
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
