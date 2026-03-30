<template>
  <q-table
    :rows="units"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    v-model:pagination="pagination"
    @request="onPaginationChange"
    no-data-label="Žádné jednotky nenalezeny"
    :rows-per-page-options="[10, 30, 50, 100]"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat jednotku"
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

    <template #body-cell-amount_of_base_uom="props">
      <q-td>
        {{ props.row.amount_of_base_uom ?? '-' }}
      </q-td>
    </template>

    <template #body-cell-base_uom="props">
      <q-td>
        {{ props.row.base_uom ?? '-' }}
      </q-td>
    </template>
  </q-table>

  <UnitOfMeasureUpsertDialog
    v-model:show="showCreateDialog"
    v-model="unitForm"
    title="Vytvořit jednotku"
    submit-label="vytvořit"
    :loading="creating"
    @submit="createUnit"
  />

  <UnitOfMeasureUpsertDialog
    v-model:show="showEditDialog"
    v-model="unitForm"
    title="Upravit jednotku"
    submit-label="uložit"
    :loading="saving"
    @submit="updateUnit"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingCreateUnit,
  warehouseApiRoutesPackagingGetUnits,
  warehouseApiRoutesPackagingUpdateUnit,
  type UnitOfMeasureCreateOrUpdateSchema,
  type UnitOfMeasureSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryUnits } from '@/composables/query/use-units-query'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import UnitOfMeasureUpsertDialog from './UnitOfMeasureUpsertDialog.vue'

const { page, pageSize, search } = useQueryUnits()
const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const units = ref<UnitOfMeasureSchema[]>([])
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingUnit = ref<UnitOfMeasureSchema | null>(null)

const createDefaultForm = (): UnitOfMeasureCreateOrUpdateSchema => ({
  name: '',
  amount_of_base_uom: null,
  base_uom: null,
})

const unitForm = ref<UnitOfMeasureCreateOrUpdateSchema>(createDefaultForm())

const fetchUnits = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesPackagingGetUnits({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      units.value = res.data.data
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
  setTimeout(() => fetchUnits(), 2)
}

const { currentRoute } = useRouter()
watch(currentRoute, () => {
  if (!shouldNotFetch()) {
    fetchUnits()
  }
})

watch(search, fetchUnits)

onMounted(fetchUnits)

const openCreateForm = () => {
  editingUnit.value = null
  unitForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (unit: UnitOfMeasureSchema) => {
  editingUnit.value = unit
  unitForm.value = {
    name: unit.name,
    amount_of_base_uom: unit.amount_of_base_uom ?? null,
    base_uom: unit.base_uom ?? null,
  }
  showEditDialog.value = true
}

const createUnit = async (body: UnitOfMeasureCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesPackagingCreateUnit({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchUnits()
    }
  } finally {
    creating.value = false
  }
}

const updateUnit = async (body: UnitOfMeasureCreateOrUpdateSchema) => {
  if (!editingUnit.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesPackagingUpdateUnit({
      path: { unit_name: editingUnit.value.name },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchUnits()
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
  {
    name: 'amount_of_base_uom',
    field: 'amount_of_base_uom',
    label: 'Množství ZJ',
    align: 'left',
  },
  {
    name: 'base_uom',
    field: 'base_uom',
    label: 'Základní jednotka',
    align: 'left',
  },
]
</script>

<style scoped></style>
