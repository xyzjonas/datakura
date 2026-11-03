<template>
  <q-table
    :rows="types"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné typy dopravy nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat typ dopravy"
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
            @click="removeType(props.row)"
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

  <ShippingTypeUpsertDialog
    v-model:show="showCreateDialog"
    v-model="typeForm"
    title="Vytvořit typ dopravy"
    submit-label="vytvořit"
    :loading="creating"
    @submit="createType"
  />

  <ShippingTypeUpsertDialog
    v-model:show="showEditDialog"
    v-model="typeForm"
    title="Upravit typ dopravy"
    submit-label="uložit"
    :loading="saving"
    @submit="updateType"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesShippingTypesCreateShippingType,
  warehouseApiRoutesShippingTypesDeleteShippingType,
  warehouseApiRoutesShippingTypesGetShippingTypes,
  warehouseApiRoutesShippingTypesUpdateShippingType,
  type ShippingTypeCreateOrUpdateSchema,
  type ShippingTypeSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import ShippingTypeUpsertDialog from './ShippingTypeUpsertDialog.vue'

const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: 20,
  page: 1,
  rowsNumber: 0,
})

const types = ref<ShippingTypeSchema[]>([])
const search = ref('')
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingType = ref<ShippingTypeSchema | null>(null)

const createDefaultForm = (): ShippingTypeCreateOrUpdateSchema => ({
  name: '',
})

const typeForm = ref<ShippingTypeCreateOrUpdateSchema>(createDefaultForm())

const fetchTypes = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesShippingTypesGetShippingTypes({
      query: {
        page: Number(pagination.value.page),
        page_size: Number(pagination.value.rowsPerPage),
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

const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
  if (!requestProp.pagination) {
    return
  }
  pagination.value = requestProp.pagination
  await fetchTypes()
}

watch(search, fetchTypes)

onMounted(fetchTypes)

const openCreateForm = () => {
  editingType.value = null
  typeForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (type: ShippingTypeSchema) => {
  editingType.value = type
  typeForm.value = {
    name: type.name,
  }
  showEditDialog.value = true
}

const createType = async (body: ShippingTypeCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesShippingTypesCreateShippingType({
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchTypes()
    }
  } finally {
    creating.value = false
  }
}

const updateType = async (body: ShippingTypeCreateOrUpdateSchema) => {
  if (!editingType.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesShippingTypesUpdateShippingType({
      path: { type_id: editingType.value.id },
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

const removeType = async (type: ShippingTypeSchema) => {
  const result = await warehouseApiRoutesShippingTypesDeleteShippingType({
    path: { type_id: type.id },
  })
  const response = onResponse(result)
  if (response?.success) {
    await fetchTypes()
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
