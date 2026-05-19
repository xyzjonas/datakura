<template>
  <q-table
    :rows="items"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    no-data-label="Žádné šarže nenalezeny"
    class="bg-transparent"
    v-model:pagination="pagination"
  >
    <template #top-left>
      <SearchInput v-model="search" placeholder="Vyhledat šarži" clearable :debounce="300" />
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
            @click="removeBatch(props.row)"
          >
            <q-tooltip>Smazat</q-tooltip>
          </q-btn>
        </div>
      </q-td>
    </template>

    <template #body-cell-barcode="props">
      <q-td>
        <span class="font-bold light:text-primary dark:text-light font-mono">{{
          props.row.primary_barcode?.code || '-'
        }}</span>
      </q-td>
    </template>

    <template #body-cell-description="props">
      <q-td>
        {{ props.row.description || '-' }}
      </q-td>
    </template>

    <template #body-cell-id="props">
      <q-td>
        <span class="text-gray-5">#{{ props.row.id }}</span>
      </q-td>
    </template>
  </q-table>

  <BatchUpsertDialog
    v-model:show="showCreateDialog"
    v-model="batchForm"
    title="Vytvořit šarži"
    submit-label="vytvořit"
    :loading="saving"
    @submit="createBatch"
  />

  <BatchUpsertDialog
    v-model:show="showEditDialog"
    v-model="batchForm"
    title="Upravit šarži"
    submit-label="uložit"
    :loading="saving"
    @submit="updateBatch"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingCreateBatch,
  warehouseApiRoutesPackagingDeleteBatch,
  warehouseApiRoutesPackagingGetBatches,
  warehouseApiRoutesPackagingUpdateBatch,
  type BatchCreateOrUpdateSchema,
  type BatchSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import type { QTableColumn } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import BatchUpsertDialog from './BatchUpsertDialog.vue'

const { onResponse } = useApi()

const search = ref('')
const loading = ref(false)
const saving = ref(false)
const items = ref<BatchSchema[]>([])
const pagination = ref({
  rowsPerPage: 25,
  page: 1,
})

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingBatch = ref<BatchSchema | null>(null)

const createDefaultForm = (): BatchCreateOrUpdateSchema => ({
  barcode: null,
  description: null,
  auto_generate_barcode: false,
})

const batchForm = ref<BatchCreateOrUpdateSchema>(createDefaultForm())

const fetchBatches = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesPackagingGetBatches({
      query: { search_term: search.value || undefined },
    })
    const data = onResponse(response)
    if (data) {
      items.value = data.data || []
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchBatches)
watch(search, fetchBatches)

const openCreateForm = () => {
  editingBatch.value = null
  batchForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (batch: BatchSchema) => {
  editingBatch.value = batch
  batchForm.value = {
    barcode: batch.primary_barcode?.code ?? null,
    description: batch.description ?? null,
    auto_generate_barcode: false,
  }
  showEditDialog.value = true
}

const createBatch = async (body: BatchCreateOrUpdateSchema) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesPackagingCreateBatch({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchBatches()
    }
  } finally {
    saving.value = false
  }
}

const updateBatch = async (body: BatchCreateOrUpdateSchema) => {
  if (!editingBatch.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesPackagingUpdateBatch({
      path: { batch_id: editingBatch.value.id },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchBatches()
    }
  } finally {
    saving.value = false
  }
}

const removeBatch = async (batch: BatchSchema) => {
  const result = await warehouseApiRoutesPackagingDeleteBatch({
    path: { batch_id: batch.id },
  })
  const response = onResponse(result)
  if (response?.success) {
    items.value = items.value.filter((item) => item.id !== batch.id)
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
    name: 'barcode',
    field: 'primary_barcode',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'description',
    field: 'description',
    label: 'Popis',
    align: 'left',
  },
  {
    name: 'id',
    field: 'id',
    label: 'ID',
    align: 'right',
  },
]
</script>

<style lang="scss" scoped></style>
