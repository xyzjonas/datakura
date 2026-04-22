<template>
  <q-table
    :rows="items"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    no-data-label="Žádné typy balení nenalezeny"
    class="bg-transparent"
    hide-pagination
    :pagination="{ rowsPerPage: -1 }"
  >
    <template #top-left>
      <SearchInput v-model="search" placeholder="Vyhledat typ balení" clearable :debounce="300" />
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
            @click="removePackageType(props.row)"
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

    <template #body-cell-description="props">
      <q-td>
        {{ props.row.description || '-' }}
      </q-td>
    </template>

    <template #body-cell-unit="props">
      <q-td>
        {{ props.row.unit || '-' }}
      </q-td>
    </template>
  </q-table>

  <PackageTypeUpsertDialog
    v-model:show="showCreateDialog"
    v-model="packageTypeForm"
    title="Vytvořit typ balení"
    submit-label="vytvořit"
    :loading="saving"
    @submit="createPackageType"
  />

  <PackageTypeUpsertDialog
    v-model:show="showEditDialog"
    v-model="packageTypeForm"
    title="Upravit typ balení"
    submit-label="uložit"
    :loading="saving"
    @submit="updatePackageType"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingCreatePackageType,
  warehouseApiRoutesPackagingDeletePackageType,
  warehouseApiRoutesPackagingGetPackageTypes,
  warehouseApiRoutesPackagingUpdatePackageType,
  type PackageTypeCreateOrUpdateSchema,
  type PackageTypeSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import type { QTableColumn } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import PackageTypeUpsertDialog from './PackageTypeUpsertDialog.vue'

const { onResponse } = useApi()

const search = ref('')
const loading = ref(false)
const saving = ref(false)
const items = ref<PackageTypeSchema[]>([])

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingPackageType = ref<PackageTypeSchema | null>(null)

const createDefaultForm = (): PackageTypeCreateOrUpdateSchema => ({
  name: '',
  description: null,
  amount: 1,
  unit: null,
})

const packageTypeForm = ref<PackageTypeCreateOrUpdateSchema>(createDefaultForm())

const fetchPackageTypes = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesPackagingGetPackageTypes({
      query: { search_term: search.value || undefined },
    })
    const data = onResponse(response)
    if (data) {
      items.value = data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchPackageTypes)
watch(search, fetchPackageTypes)

const openCreateForm = () => {
  editingPackageType.value = null
  packageTypeForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (packageType: PackageTypeSchema) => {
  editingPackageType.value = packageType
  packageTypeForm.value = {
    name: packageType.name,
    description: packageType.description ?? null,
    amount: packageType.amount,
    unit: packageType.unit ?? null,
  }
  showEditDialog.value = true
}

const createPackageType = async (body: PackageTypeCreateOrUpdateSchema) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesPackagingCreatePackageType({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchPackageTypes()
    }
  } finally {
    saving.value = false
  }
}

const updatePackageType = async (body: PackageTypeCreateOrUpdateSchema) => {
  if (!editingPackageType.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesPackagingUpdatePackageType({
      path: { package_type_name: editingPackageType.value.name },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchPackageTypes()
    }
  } finally {
    saving.value = false
  }
}

const removePackageType = async (packageType: PackageTypeSchema) => {
  const result = await warehouseApiRoutesPackagingDeletePackageType({
    path: { package_type_name: packageType.name },
  })
  const response = onResponse(result)
  if (response?.success) {
    items.value = items.value.filter((item) => item.name !== packageType.name)
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
    name: 'description',
    field: 'description',
    label: 'Popis',
    align: 'left',
  },
  {
    name: 'amount',
    field: 'amount',
    label: 'Množství',
    align: 'left',
  },
  {
    name: 'unit',
    field: 'unit',
    label: 'MJ',
    align: 'left',
  },
]
</script>

<style lang="scss" scoped></style>
