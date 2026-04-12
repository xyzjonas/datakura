<template>
  <q-table
    :rows="filteredGroups"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    row-key="code"
    no-data-label="Žádné slevové skupiny nenalezeny"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput
        v-model="search"
        placeholder="Vyhledat slevovou skupinu"
        clearable
        :debounce="300"
      />
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
            @click="removeGroup(props.row.code)"
          >
            <q-tooltip>Smazat</q-tooltip>
          </q-btn>
        </div>
      </q-td>
    </template>

    <template #body-cell-code="props">
      <q-td>
        <span class="font-bold">{{ props.row.code }}</span>
      </q-td>
    </template>

    <template #body-cell-discount_percent="props">
      <q-td>{{ props.row.discount_percent }} %</q-td>
    </template>

    <template #body-cell-is_active="props">
      <q-td>
        <q-badge :color="props.row.is_active ? 'positive' : 'grey-6'">
          {{ props.row.is_active ? 'aktivní' : 'neaktivní' }}
        </q-badge>
      </q-td>
    </template>
  </q-table>

  <DiscountGroupUpsertDialog
    v-model:show="showCreateDialog"
    v-model="discountGroupForm"
    title="Vytvořit slevovou skupinu"
    submit-label="vytvořit"
    :loading="saving"
    @submit="createGroup"
  />

  <DiscountGroupUpsertDialog
    v-model:show="showEditDialog"
    v-model="discountGroupForm"
    title="Upravit slevovou skupinu"
    submit-label="uložit"
    :loading="saving"
    @submit="updateGroup"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductCreateDiscountGroup,
  warehouseApiRoutesProductDeleteDiscountGroup,
  warehouseApiRoutesProductGetDiscountGroups,
  warehouseApiRoutesProductUpdateDiscountGroup,
  type DiscountGroupCreateOrUpdateSchema,
  type DiscountGroupSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { type QTableColumn } from 'quasar'
import { computed, onMounted, ref } from 'vue'
import DiscountGroupUpsertDialog from './DiscountGroupUpsertDialog.vue'

const { onResponse } = useApi()

const search = ref('')
const loading = ref(false)
const saving = ref(false)

const groups = ref<DiscountGroupSchema[]>([])
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingGroupCode = ref<string | null>(null)

const discountGroupForm = ref<DiscountGroupCreateOrUpdateSchema>({
  name: '',
  discount_percent: 0,
  is_active: true,
})

const fetchGroups = async () => {
  loading.value = true
  try {
    const result = await warehouseApiRoutesProductGetDiscountGroups()
    if (result.data?.data) {
      groups.value = result.data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchGroups)

const filteredGroups = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) {
    return groups.value
  }

  return groups.value.filter(
    (group) =>
      group.code.toLowerCase().includes(term) ||
      group.name.toLowerCase().includes(term) ||
      String(group.discount_percent).includes(term),
  )
})

const openCreateForm = () => {
  editingGroupCode.value = null
  discountGroupForm.value = {
    name: '',
    discount_percent: 0,
    is_active: true,
  }
  showCreateDialog.value = true
}

const openEditForm = (group: DiscountGroupSchema) => {
  editingGroupCode.value = group.code
  discountGroupForm.value = {
    name: group.name,
    discount_percent: group.discount_percent,
    is_active: group.is_active,
  }
  showEditDialog.value = true
}

const createGroup = async (body: DiscountGroupCreateOrUpdateSchema) => {
  const code = body.name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toUpperCase()

  if (!code) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesProductCreateDiscountGroup({
      path: { group_code: code },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchGroups()
    }
  } finally {
    saving.value = false
  }
}

const updateGroup = async (body: DiscountGroupCreateOrUpdateSchema) => {
  if (!editingGroupCode.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesProductUpdateDiscountGroup({
      path: { group_code: editingGroupCode.value },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      await fetchGroups()
    }
  } finally {
    saving.value = false
  }
}

const removeGroup = async (groupCode: string) => {
  const result = await warehouseApiRoutesProductDeleteDiscountGroup({
    path: { group_code: groupCode },
  })
  const response = onResponse(result)
  if (response?.data) {
    groups.value = response.data
  }
}

const columns: QTableColumn[] = [
  {
    name: 'actions',
    field: 'code',
    label: 'Akce',
    align: 'left',
  },
  {
    name: 'code',
    field: 'code',
    label: 'Kód',
    align: 'left',
  },
  {
    name: 'name',
    field: 'name',
    label: 'Název',
    align: 'left',
  },
  {
    name: 'discount_percent',
    field: 'discount_percent',
    label: 'Sleva',
    align: 'left',
  },
  {
    name: 'is_active',
    field: 'is_active',
    label: 'Stav',
    align: 'left',
  },
]
</script>
