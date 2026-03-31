<template>
  <q-table
    :rows="types"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné typy zboží nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat typ zboží"
        clearable
        :debounce="300"
      ></SearchInput>
    </template>

    <template #top-right>
      <q-btn color="primary" unelevated label="vytvořit" icon="add" @click="openCreateForm" />
    </template>

    <template #body-cell-actions="props">
      <q-td auto-width>
        <q-btn flat dense round icon="edit" size="sm" @click="openEditForm(props.row)">
          <q-tooltip>Upravit</q-tooltip>
        </q-btn>
      </q-td>
    </template>

    <template #body-cell-name="props">
      <q-td>
        <span class="font-bold light:text-primary dark:text-light">{{ props.row.name }}</span>
      </q-td>
    </template>
  </q-table>

  <ProductTypeUpsertDialog
    v-model:show="showCreateDialog"
    v-model="typeForm"
    title="Vytvořit typ zboží"
    submit-label="vytvořit"
    :loading="creating"
    @submit="createType"
  />

  <ProductTypeUpsertDialog
    v-model:show="showEditDialog"
    v-model="typeForm"
    title="Upravit typ zboží"
    submit-label="uložit"
    :loading="saving"
    @submit="updateType"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductCreateType,
  warehouseApiRoutesProductGetTypes,
  warehouseApiRoutesProductUpdateType,
  type ProductTypeCreateOrUpdateSchema,
  type ProductTypeSchema,
} from '@/client'
import ProductTypeUpsertDialog from '@/components/product/ProductTypeUpsertDialog.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryTypes } from '@/composables/query/use-types-query'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'

const { page, pageSize, search } = useQueryTypes()
const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const types = ref<ProductTypeSchema[]>([])
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingType = ref<ProductTypeSchema | null>(null)

const createDefaultForm = (): ProductTypeCreateOrUpdateSchema => ({
  name: '',
})

const typeForm = ref<ProductTypeCreateOrUpdateSchema>(createDefaultForm())

const fetchTypes = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesProductGetTypes({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      types.value = res.data.data
      pagination.value.rowsNumber = res.data.count
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

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
  setTimeout(() => fetchTypes(), 2)
}

watch([page, pageSize, search], () => {
  fetchTypes()
})

onMounted(fetchTypes)

const openCreateForm = () => {
  editingType.value = null
  typeForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (type: ProductTypeSchema) => {
  editingType.value = type
  typeForm.value = {
    name: type.name,
  }
  showEditDialog.value = true
}

const createType = async (body: ProductTypeCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesProductCreateType({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchTypes()
    }
  } finally {
    creating.value = false
  }
}

const updateType = async (body: ProductTypeCreateOrUpdateSchema) => {
  if (!editingType.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesProductUpdateType({
      path: { type_name: editingType.value.name },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchTypes()
    }
  } finally {
    saving.value = false
  }
}

const columns: QTableColumn[] = [
  {
    name: 'actions',
    field: 'name',
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

<style scoped></style>
