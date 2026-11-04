<template>
  <q-table
    :rows="schedules"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    no-data-label="Žádné plány nenalezeny"
    class="bg-transparent"
    hide-pagination
    :pagination="{ rowsPerPage: -1 }"
  >
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
            @click="openDeleteDialog(props.row)"
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

    <template #body-cell-schedule="props">
      <q-td>{{ describeSchedule(props.row) }}</q-td>
    </template>

    <template #body-cell-enabled="props">
      <q-td auto-width>
        <q-toggle
          :model-value="props.row.enabled"
          dense
          @update:model-value="toggleEnabled(props.row, $event)"
        />
      </q-td>
    </template>

    <template #body-cell-last_run_at="props">
      <q-td>{{ props.row.last_run_at ? formatDateTimeLong(props.row.last_run_at) : '-' }}</q-td>
    </template>
  </q-table>

  <SnapshotScheduleUpsertDialog
    v-model:show="showCreateDialog"
    v-model="scheduleForm"
    title="Přidat plán"
    submit-label="přidat"
    :loading="saving"
    @submit="createSchedule"
  />

  <SnapshotScheduleUpsertDialog
    v-model:show="showEditDialog"
    v-model="scheduleForm"
    title="Upravit plán"
    submit-label="uložit"
    :loading="saving"
    @submit="updateSchedule"
  />

  <ConfirmDialog v-model:show="showDeleteDialog" title="Smazat plán?" @confirm="removeSchedule">
    <p>
      Opravdu smazat plán
      <strong>{{ scheduleToDelete?.name }}</strong>
      ?
    </p>
    <p v-if="scheduleToDelete" class="mt-2 text-muted">{{ describeSchedule(scheduleToDelete) }}</p>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesSnapshotSchedulesCreateSnapshotSchedule,
  warehouseApiRoutesSnapshotSchedulesDeleteSnapshotSchedule,
  warehouseApiRoutesSnapshotSchedulesGetSnapshotSchedules,
  warehouseApiRoutesSnapshotSchedulesUpdateSnapshotSchedule,
  type SnapshotScheduleCreateOrUpdateSchema,
  type SnapshotScheduleSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useApi } from '@/composables/use-api'
import { formatDateTimeLong } from '@/utils/date'
import type { QTableColumn } from 'quasar'
import { onMounted, ref } from 'vue'
import SnapshotScheduleUpsertDialog from './SnapshotScheduleUpsertDialog.vue'
import { createDefaultScheduleForm, describeSchedule, scheduleToForm } from './snapshot-schedule'

const { onResponse } = useApi()

const loading = ref(false)
const saving = ref(false)
const schedules = ref<SnapshotScheduleSchema[]>([])

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const editingSchedule = ref<SnapshotScheduleSchema | null>(null)
const scheduleToDelete = ref<SnapshotScheduleSchema | null>(null)
const scheduleForm = ref<SnapshotScheduleCreateOrUpdateSchema>(createDefaultScheduleForm())

const fetchSchedules = async () => {
  loading.value = true
  try {
    const data = onResponse(await warehouseApiRoutesSnapshotSchedulesGetSnapshotSchedules())
    if (data) {
      schedules.value = data.data
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchSchedules)

const openCreateForm = () => {
  editingSchedule.value = null
  scheduleForm.value = createDefaultScheduleForm()
  showCreateDialog.value = true
}

const openEditForm = (schedule: SnapshotScheduleSchema) => {
  editingSchedule.value = schedule
  scheduleForm.value = scheduleToForm(schedule)
  showEditDialog.value = true
}

const openDeleteDialog = (schedule: SnapshotScheduleSchema) => {
  scheduleToDelete.value = schedule
  showDeleteDialog.value = true
}

const createSchedule = async (body: SnapshotScheduleCreateOrUpdateSchema) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesSnapshotSchedulesCreateSnapshotSchedule({ body })
    if (onResponse(result)?.data) {
      showCreateDialog.value = false
      await fetchSchedules()
    }
  } finally {
    saving.value = false
  }
}

const updateSchedule = async (body: SnapshotScheduleCreateOrUpdateSchema) => {
  if (!editingSchedule.value) {
    return
  }
  saving.value = true
  try {
    const result = await warehouseApiRoutesSnapshotSchedulesUpdateSnapshotSchedule({
      path: { schedule_id: editingSchedule.value.id },
      body,
    })
    if (onResponse(result)?.data) {
      showEditDialog.value = false
      await fetchSchedules()
    }
  } finally {
    saving.value = false
  }
}

const toggleEnabled = async (schedule: SnapshotScheduleSchema, enabled: boolean) => {
  const result = await warehouseApiRoutesSnapshotSchedulesUpdateSnapshotSchedule({
    path: { schedule_id: schedule.id },
    body: { ...scheduleToForm(schedule), enabled },
  })
  onResponse(result)
  await fetchSchedules()
}

const removeSchedule = async () => {
  if (!scheduleToDelete.value) {
    return
  }
  const result = await warehouseApiRoutesSnapshotSchedulesDeleteSnapshotSchedule({
    path: { schedule_id: scheduleToDelete.value.id },
  })
  if (onResponse(result)?.data) {
    scheduleToDelete.value = null
    await fetchSchedules()
  }
}

const columns: QTableColumn[] = [
  { name: 'actions', field: 'id', label: 'Akce', align: 'left' },
  { name: 'name', field: 'name', label: 'Název', align: 'left' },
  { name: 'schedule', field: 'mode', label: 'Plán', align: 'left' },
  { name: 'enabled', field: 'enabled', label: 'Aktivní', align: 'left' },
  { name: 'last_run_at', field: 'last_run_at', label: 'Naposledy spuštěno', align: 'left' },
  { name: 'total_run_count', field: 'total_run_count', label: 'Počet spuštění', align: 'left' },
]
</script>
