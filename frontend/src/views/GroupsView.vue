<template>
  <div class="flex-1">
    <div class="mb-2 flex justify-between items-center">
      <div>
        <h1>Přehled Skupin</h1>
        <h5 class="text-gray-5 mt-2">Správa skupin produktů</h5>
      </div>
      <q-btn
        color="primary"
        unelevated
        label="vytvořit"
        icon="sym_o_add"
        @click="openCreateForm"
        class="mt-5 mx-4 xs:mx-0 xs:mt-0"
      />
    </div>
    <q-table
      :rows="groups"
      :columns="columns"
      :loading="loading"
      loading-label="Načítám"
      flat
      v-model:pagination="pagination"
      @request="onPaginationChange"
      no-data-label="Žádné skupiny nenalezeny"
      :rows-per-page-options="[10, 30, 50, 100]"
      class="bg-transparent"
    >
      <template #top-left>
        <SearchInput
          v-model="search"
          placeholder="Vyhledat skupinu"
          clearable
          :debounce="300"
        ></SearchInput>
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

    <GroupUpsertDialog
      v-model:show="showCreateDialog"
      v-model="groupForm"
      title="Vytvořit skupinu"
      submit-label="vytvořit"
      :loading="creating"
      @submit="createGroup"
    />

    <GroupUpsertDialog
      v-model:show="showEditDialog"
      v-model="groupForm"
      title="Upravit skupinu"
      submit-label="uložit"
      :loading="saving"
      @submit="updateGroup"
    />
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesGroupGetGroups,
  warehouseApiRoutesGroupCreateGroup,
  warehouseApiRoutesGroupUpdateGroup,
  type ProductGroupCreateOrUpdateSchema,
  type ProductGroupSchema,
} from '@/client'
import GroupUpsertDialog from '@/components/product/GroupUpsertDialog.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useQueryGroups } from '@/composables/query/use-groups-query'
import { useApi } from '@/composables/use-api'
import { type QTableColumn, type QTableProps } from 'quasar'
import { onMounted, ref, watch } from 'vue'

const { page, pageSize, search } = useQueryGroups()
const { onResponse } = useApi()

const pagination = ref<NonNullable<QTableProps['pagination']>>({
  rowsPerPage: pageSize.value,
  page: page.value,
  rowsNumber: pageSize.value,
})

const groups = ref<ProductGroupSchema[]>([])
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingGroup = ref<ProductGroupSchema | null>(null)

const createDefaultForm = (): ProductGroupCreateOrUpdateSchema => ({
  name: '',
})

const groupForm = ref<ProductGroupCreateOrUpdateSchema>(createDefaultForm())

const fetchGroups = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesGroupGetGroups({
      query: {
        page: page.value,
        page_size: pageSize.value,
        search_term: search.value,
      },
    })
    if (res.data?.data) {
      groups.value = res.data.data
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
  setTimeout(() => fetchGroups(), 2)
}

watch([page, pageSize, search], () => {
  fetchGroups()
})

onMounted(fetchGroups)

const openCreateForm = () => {
  editingGroup.value = null
  groupForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (group: ProductGroupSchema) => {
  editingGroup.value = group
  groupForm.value = { name: group.name }
  showEditDialog.value = true
}

const createGroup = async (body: ProductGroupCreateOrUpdateSchema) => {
  creating.value = true
  try {
    const result = await warehouseApiRoutesGroupCreateGroup({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchGroups()
    }
  } finally {
    creating.value = false
  }
}

const updateGroup = async (body: ProductGroupCreateOrUpdateSchema) => {
  if (!editingGroup.value) {
    return
  }

  saving.value = true
  try {
    const result = await warehouseApiRoutesGroupUpdateGroup({
      path: { group_name: editingGroup.value.name },
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
