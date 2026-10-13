<template>
  <q-table
    :rows="users"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    no-data-label="Žádní uživatelé nenalezeni"
    class="bg-transparent"
    hide-pagination
    :pagination="{ rowsPerPage: -1 }"
  >
    <template #top-left>
      <SearchInput v-model="search" placeholder="Vyhledat uživatele" clearable :debounce="300" />
    </template>

    <template #top-right>
      <q-btn color="primary" unelevated label="přidat" icon="add" @click="openCreateForm" />
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
            :disable="props.row.id === user.user_id"
            @click="openDeleteDialog(props.row)"
          >
            <q-tooltip>Smazat</q-tooltip>
          </q-btn>
        </div>
      </q-td>
    </template>

    <template #body-cell-username="props">
      <q-td>
        <span class="font-bold light:text-primary dark:text-light">{{ props.row.username }}</span>
        <span v-if="props.row.id === user.user_id" class="ml-2 text-xs text-muted">(vy)</span>
      </q-td>
    </template>

    <template #body-cell-is_superuser="props">
      <q-td>
        <q-badge :color="props.row.is_superuser ? 'primary' : 'grey-7'">
          {{ props.row.is_superuser ? 'administrátor' : 'uživatel' }}
        </q-badge>
      </q-td>
    </template>

    <template #body-cell-is_active="props">
      <q-td>
        <q-badge :color="props.row.is_active ? 'positive' : 'negative'">
          {{ props.row.is_active ? 'aktivní' : 'zablokován' }}
        </q-badge>
      </q-td>
    </template>
  </q-table>

  <UserUpsertDialog
    v-model:show="showCreateDialog"
    v-model="userForm"
    title="Přidat uživatele"
    submit-label="přidat"
    :loading="saving"
    @submit="createUser"
  />

  <UserUpsertDialog
    v-model:show="showEditDialog"
    v-model="userForm"
    title="Upravit uživatele"
    submit-label="uložit"
    editing
    :is-self="editingUser?.id === user.user_id"
    :loading="saving"
    @submit="updateUser"
  />

  <ConfirmDialog v-model:show="showDeleteDialog" title="Smazat uživatele?" @confirm="removeUser">
    <p>
      Opravdu smazat uživatele
      <strong>{{ userToDelete?.username }}</strong>
      ?
    </p>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesUsersCreateUser,
  warehouseApiRoutesUsersDeleteUser,
  warehouseApiRoutesUsersGetUsers,
  warehouseApiRoutesUsersUpdateUser,
  type UserSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { useAuth } from '@/composables/use-auth'
import { formatDateTimeLong } from '@/utils/date'
import type { QTableColumn } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import UserUpsertDialog from './UserUpsertDialog.vue'
import { createDefaultUserForm, type UserFormData } from './user-form'

const { onResponse } = useApi()
const { user, whoami } = useAuth()

const search = ref('')
const loading = ref(false)
const saving = ref(false)
const users = ref<UserSchema[]>([])

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const editingUser = ref<UserSchema | null>(null)
const userToDelete = ref<UserSchema | null>(null)

const userForm = ref<UserFormData>(createDefaultUserForm())

const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesUsersGetUsers({
      query: { search_term: search.value || undefined },
    })
    const data = onResponse(response)
    if (data) {
      users.value = data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchUsers)
watch(search, fetchUsers)

const openCreateForm = () => {
  editingUser.value = null
  userForm.value = createDefaultUserForm()
  showCreateDialog.value = true
}

const openEditForm = (row: UserSchema) => {
  editingUser.value = row
  userForm.value = {
    username: row.username,
    password: '',
    email: row.email,
    first_name: row.first_name,
    last_name: row.last_name,
    is_active: row.is_active,
    is_superuser: row.is_superuser,
  }
  showEditDialog.value = true
}

const openDeleteDialog = (row: UserSchema) => {
  userToDelete.value = row
  showDeleteDialog.value = true
}

const createUser = async (body: UserFormData) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesUsersCreateUser({ body })
    if (onResponse(result)?.data) {
      showCreateDialog.value = false
      await fetchUsers()
    }
  } finally {
    saving.value = false
  }
}

const updateUser = async (form: UserFormData) => {
  if (!editingUser.value) {
    return
  }

  saving.value = true
  try {
    const editedId = editingUser.value.id
    const result = await warehouseApiRoutesUsersUpdateUser({
      path: { user_id: editedId },
      body: { ...form, password: form.password || null },
    })
    if (onResponse(result)?.data) {
      showEditDialog.value = false
      if (editedId === user.value.user_id) {
        await whoami()
      }
      await fetchUsers()
    }
  } finally {
    saving.value = false
  }
}

const removeUser = async () => {
  if (!userToDelete.value) {
    return
  }

  const result = await warehouseApiRoutesUsersDeleteUser({
    path: { user_id: userToDelete.value.id },
  })
  if (onResponse(result)?.data) {
    userToDelete.value = null
    await fetchUsers()
  }
}

const columns: QTableColumn<UserSchema>[] = [
  { name: 'actions', field: 'id', label: 'Akce', align: 'left' },
  { name: 'username', field: 'username', label: 'Uživatel', align: 'left' },
  {
    name: 'name',
    field: (row) => `${row.first_name} ${row.last_name}`.trim() || '-',
    label: 'Jméno',
    align: 'left',
  },
  { name: 'email', field: (row) => row.email || '-', label: 'E-mail', align: 'left' },
  { name: 'is_superuser', field: 'is_superuser', label: 'Role', align: 'left' },
  { name: 'is_active', field: 'is_active', label: 'Stav', align: 'left' },
  {
    name: 'last_login',
    field: (row) => (row.last_login ? formatDateTimeLong(new Date(row.last_login)) : '-'),
    label: 'Poslední přihlášení',
    align: 'left',
  },
]
</script>
