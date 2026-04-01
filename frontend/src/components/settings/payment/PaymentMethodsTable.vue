<template>
  <q-table
    :rows="methods"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné platební metody nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat platební metodu"
        clearable
        :debounce="300"
      ></SearchInput>
    </template>

    <template #top-right>
      <q-btn color="primary" unelevated label="vytvořit" icon="add" @click="openCreateForm" />
    </template>

    <template #body-cell-actions="props">
      <q-td auto-width>
        <div class="flex items-center gap-3 flex-nowrap">
          <q-btn flat dense round icon="edit" size="sm" @click="openEditForm(props.row)">
            <q-tooltip>Upravit</q-tooltip>
          </q-btn>
          <q-btn
            flat
            dense
            round
            icon="delete"
            size="sm"
            color="negative"
            @click="removeMethod(props.row)"
          >
            <q-tooltip>Smazat</q-tooltip>
          </q-btn>
        </div>
      </q-td>
    </template>

    <template #body-cell-name="props">
      <q-td>
        <span class="font-bold light:text-primary dark:text-light">{{ props.row.name }}</span>
      </q-td>
    </template>
  </q-table>

  <PaymentMethodUpsertDialog
    v-model:show="showCreateDialog"
    v-model="methodForm"
    title="Vytvořit platební metodu"
    submit-label="vytvořit"
    :loading="creating"
    @submit="createMethod"
  />

  <PaymentMethodUpsertDialog
    v-model:show="showEditDialog"
    v-model="methodForm"
    title="Upravit platební metodu"
    submit-label="uložit"
    :loading="saving"
    @submit="updateMethod"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInvoicePaymentMethodsCreateInvoicePaymentMethod,
  warehouseApiRoutesInvoicePaymentMethodsDeleteInvoicePaymentMethod,
  warehouseApiRoutesInvoicePaymentMethodsGetInvoicePaymentMethods,
  warehouseApiRoutesInvoicePaymentMethodsUpdateInvoicePaymentMethod,
  type InvoicePaymentMethodCreateOrUpdateSchema,
  type InvoicePaymentMethodSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import PaymentMethodUpsertDialog from './PaymentMethodUpsertDialog.vue'

const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: 20,
  page: 1,
  rowsNumber: 0,
})

const methods = ref<InvoicePaymentMethodSchema[]>([])
const search = ref('')
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingMethod = ref<InvoicePaymentMethodSchema | null>(null)

const createDefaultForm = (): InvoicePaymentMethodCreateOrUpdateSchema => ({
  name: '',
})

const methodForm = ref<InvoicePaymentMethodCreateOrUpdateSchema>(createDefaultForm())

const fetchMethods = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesInvoicePaymentMethodsGetInvoicePaymentMethods({
      query: {
        page: Number(pagination.value.page),
        page_size: Number(pagination.value.rowsPerPage),
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      methods.value = res.data.data
      pagination.value.rowsNumber = res.data.count
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
  if (!requestProp.pagination) {
    return
  }
  pagination.value = requestProp.pagination
  await fetchMethods()
}

watch(search, fetchMethods)

onMounted(fetchMethods)

const openCreateForm = () => {
  editingMethod.value = null
  methodForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (method: InvoicePaymentMethodSchema) => {
  editingMethod.value = method
  methodForm.value = {
    name: method.name,
  }
  showEditDialog.value = true
}

const createMethod = async (body: InvoicePaymentMethodCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesInvoicePaymentMethodsCreateInvoicePaymentMethod({
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchMethods()
    }
  } finally {
    creating.value = false
  }
}

const updateMethod = async (body: InvoicePaymentMethodCreateOrUpdateSchema) => {
  if (!editingMethod.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesInvoicePaymentMethodsUpdateInvoicePaymentMethod({
      path: { method_id: editingMethod.value.id },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchMethods()
    }
  } finally {
    saving.value = false
  }
}

const removeMethod = async (method: InvoicePaymentMethodSchema) => {
  const result = await warehouseApiRoutesInvoicePaymentMethodsDeleteInvoicePaymentMethod({
    path: { method_id: method.id },
  })
  const response = onResponse(result)
  if (response?.success) {
    await fetchMethods()
  }
}

const columns: QTableColumn[] = [
  {
    name: 'actions',
    field: 'id',
    label: 'Akce',
    align: 'left',
  },
  {
    name: 'name',
    field: 'name',
    label: 'Název',
    align: 'left',
  },
]
</script>
