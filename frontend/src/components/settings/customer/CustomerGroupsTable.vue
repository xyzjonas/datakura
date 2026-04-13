<template>
  <q-table
    :rows="filteredGroups"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    row-key="code"
    no-data-label="Žádné zákaznické skupiny nenalezeny"
    class="bg-transparent"
  >
    <template #top-left>
      <SearchInput v-model="search" placeholder="Vyhledat skupinu" clearable :debounce="300" />
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
  </q-table>

  <CustomerGroupUpsertDialog
    v-model:show="showCreateDialog"
    v-model="groupForm"
    title="Vytvořit zákaznickou skupinu"
    submit-label="vytvořit"
    :loading="saving"
    @submit="createGroup"
  />

  <CustomerGroupUpsertDialog
    v-model:show="showEditDialog"
    v-model="groupForm"
    title="Upravit zákaznickou skupinu"
    submit-label="uložit"
    :loading="saving"
    @submit="updateGroup"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCustomerGroupsCreateCustomerGroup,
  warehouseApiRoutesCustomerGroupsDeleteCustomerGroup,
  warehouseApiRoutesCustomerGroupsGetCustomerGroups,
  warehouseApiRoutesCustomerGroupsUpdateCustomerGroup,
  type CustomerGroupCreateOrUpdateSchema,
  type CustomerGroupSchema,
} from '@/client'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { type QTableColumn } from 'quasar'
import { computed, onMounted, ref } from 'vue'
import CustomerGroupUpsertDialog from './CustomerGroupUpsertDialog.vue'

const { onResponse } = useApi()

const search = ref('')
const loading = ref(false)
const saving = ref(false)

const groups = ref<CustomerGroupSchema[]>([])
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingGroupCode = ref<string | null>(null)

const groupForm = ref<CustomerGroupCreateOrUpdateSchema>({
  code: '',
  name: '',
})

const fetchGroups = async () => {
  loading.value = true
  try {
    const result = await warehouseApiRoutesCustomerGroupsGetCustomerGroups({
      query: { page: 1, page_size: 500 },
    })
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
    (group) => group.code.toLowerCase().includes(term) || group.name.toLowerCase().includes(term),
  )
})

const openCreateForm = () => {
  editingGroupCode.value = null
  groupForm.value = {
    code: '',
    name: '',
  }
  showCreateDialog.value = true
}

const openEditForm = (group: CustomerGroupSchema) => {
  editingGroupCode.value = group.code
  groupForm.value = {
    code: group.code,
    name: group.name,
  }
  showEditDialog.value = true
}

const createGroup = async (body: CustomerGroupCreateOrUpdateSchema) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesCustomerGroupsCreateCustomerGroup({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchGroups()
    }
  } finally {
    saving.value = false
  }
}

const updateGroup = async (body: CustomerGroupCreateOrUpdateSchema) => {
  if (!editingGroupCode.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesCustomerGroupsUpdateCustomerGroup({
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
  const result = await warehouseApiRoutesCustomerGroupsDeleteCustomerGroup({
    path: { group_code: groupCode },
  })
  const response = onResponse(result)
  if (response?.data) {
    groups.value = groups.value.filter((group) => group.code !== groupCode)
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
]
</script>
