<template>
  <q-table
    :rows="printers"
    :columns="columns"
    :loading="loading"
    loading-label="Načítám"
    flat
    no-data-label="Žádné tiskárny nenalezeny"
    class="bg-transparent"
    hide-pagination
    :pagination="{ rowsPerPage: -1 }"
  >
    <template #top-left>
      <SearchInput v-model="search" placeholder="Vyhledat tiskárnu" clearable :debounce="300" />
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
            @click="openDeleteDialog(props.row)"
          >
            <q-tooltip>Smazat</q-tooltip>
          </q-btn>
        </div>
      </q-td>
    </template>

    <template #body-cell-code="props">
      <q-td>
        <span class="font-bold light:text-primary dark:text-light">{{ props.row.code }}</span>
      </q-td>
    </template>

    <template #body-cell-description="props">
      <q-td>
        {{ props.row.description || '-' }}
      </q-td>
    </template>
  </q-table>

  <PrinterUpsertDialog
    v-model:show="showCreateDialog"
    v-model="printerForm"
    title="Přidat tiskárnu"
    submit-label="přidat"
    :loading="saving"
    @submit="createPrinter"
  />

  <PrinterUpsertDialog
    v-model:show="showEditDialog"
    v-model="printerForm"
    title="Upravit tiskárnu"
    submit-label="uložit"
    :loading="saving"
    @submit="updatePrinter"
  />

  <ConfirmDialog v-model:show="showDeleteDialog" title="Smazat tiskárnu?" @confirm="removePrinter">
    <p>
      Opravdu smazat tiskárnu
      <strong>{{ printerToDelete?.code }}</strong>
      ?
    </p>
    <p v-if="printerToDelete?.description" class="mt-2 text-muted">
      {{ printerToDelete.description }}
    </p>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPrintersCreatePrinter,
  warehouseApiRoutesPrintersDeletePrinter,
  warehouseApiRoutesPrintersGetPrinters,
  warehouseApiRoutesPrintersUpdatePrinter,
  type PrinterCreateOrUpdateSchema,
  type PrinterSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import SearchInput from '@/components/SearchInput.vue'
import { useApi } from '@/composables/use-api'
import { useAuth } from '@/composables/use-auth'
import type { QTableColumn } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import PrinterUpsertDialog from './PrinterUpsertDialog.vue'

const { onResponse } = useApi()
const { user, whoami } = useAuth()

const search = ref('')
const loading = ref(false)
const saving = ref(false)
const printers = ref<PrinterSchema[]>([])

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const editingPrinter = ref<PrinterSchema | null>(null)
const printerToDelete = ref<PrinterSchema | null>(null)

const createDefaultForm = (): PrinterCreateOrUpdateSchema => ({
  code: '',
  description: null,
})

const printerForm = ref<PrinterCreateOrUpdateSchema>(createDefaultForm())

const fetchPrinters = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesPrintersGetPrinters({
      query: { search_term: search.value || undefined },
    })
    const data = onResponse(response)
    if (data) {
      printers.value = data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

onMounted(fetchPrinters)
watch(search, fetchPrinters)

const openCreateForm = () => {
  editingPrinter.value = null
  printerForm.value = createDefaultForm()
  showCreateDialog.value = true
}

const openEditForm = (printer: PrinterSchema) => {
  editingPrinter.value = printer
  printerForm.value = {
    code: printer.code,
    description: printer.description ?? null,
  }
  showEditDialog.value = true
}

const openDeleteDialog = (printer: PrinterSchema) => {
  printerToDelete.value = printer
  showDeleteDialog.value = true
}

const createPrinter = async (body: PrinterCreateOrUpdateSchema) => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesPrintersCreatePrinter({ body })
    const response = onResponse(result)
    if (response?.data) {
      showCreateDialog.value = false
      await fetchPrinters()
    }
  } finally {
    saving.value = false
  }
}

const updatePrinter = async (body: PrinterCreateOrUpdateSchema) => {
  if (!editingPrinter.value) {
    return
  }

  saving.value = true
  try {
    const previousCode = editingPrinter.value.code
    const result = await warehouseApiRoutesPrintersUpdatePrinter({
      path: { printer_code: previousCode },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      showEditDialog.value = false
      if (user.value?.default_printer?.code === previousCode) {
        await whoami()
      }
      await fetchPrinters()
    }
  } finally {
    saving.value = false
  }
}

const removePrinter = async () => {
  if (!printerToDelete.value) {
    return
  }

  const deletedCode = printerToDelete.value.code
  const result = await warehouseApiRoutesPrintersDeletePrinter({
    path: { printer_code: deletedCode },
  })
  const response = onResponse(result)
  if (response?.data) {
    printerToDelete.value = null
    if (user.value?.default_printer?.code === deletedCode) {
      await whoami()
    }
    await fetchPrinters()
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
    name: 'description',
    field: 'description',
    label: 'Popis',
    align: 'left',
  },
]
</script>
