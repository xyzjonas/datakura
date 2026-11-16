<template>
  <ForegroundPanel :body-class="['flex', 'flex-col']" data-test="customer-codes-card">
    <template #header>
      <span class="text-muted">KÓDY ZÁKAZNÍKŮ</span>
    </template>
    <q-table
      :rows="codes"
      :columns="columns"
      row-key="id"
      flat
      :loading="loading"
      :pagination="{ rowsPerPage: 5 }"
      class="bg-transparent"
      no-data-label="Zákazníci pro tento produkt nemají vlastní kódy."
    >
      <template #body-cell-customer="slotProps">
        <q-td :props="slotProps" auto-width>
          <router-link
            :to="{ name: 'customerDetail', params: { customerCode: slotProps.row.customer.code } }"
            class="link flex"
          >
            <span class="truncate max-w-30">{{ slotProps.row.customer.name }}</span>
            <small class="text-gray-5">{{ slotProps.row.customer.code }}</small>
          </router-link>
        </q-td>
      </template>

      <template #body-cell-actions="slotProps">
        <q-td :props="slotProps" class="text-right">
          <q-btn flat round dense icon="sym_o_edit" color="primary" @click="onEdit(slotProps.row)">
            <q-tooltip>Upravit kód</q-tooltip>
          </q-btn>
          <q-btn
            flat
            round
            dense
            icon="sym_o_close_small"
            color="negative"
            :loading="deletingId === slotProps.row.id"
            @click="onDelete(slotProps.row)"
          >
            <q-tooltip>Odstranit kód</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <q-btn
      outline
      color="primary"
      icon="sym_o_tag"
      label="přidat kód"
      class="mt-auto self-end"
      @click="onAdd"
    />

    <CustomerProductCodeUpsertDialog
      v-model:show="showDialog"
      :editing="editing"
      :saving="saving"
      @submit="onSubmit"
    />

    <ConfirmDialog
      v-model:show="showDeleteDialog"
      title="Opravdu odstranit tento kód?"
      @confirm="onConfirmDelete"
    >
      <span>
        Kód <strong>{{ pendingDelete?.code }}</strong> zákazníka
        <strong>{{ pendingDelete?.customer.name }}</strong> bude smazán.
      </span>
    </ConfirmDialog>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductDeleteProductCustomerCode,
  warehouseApiRoutesProductGetProductCustomerCodes,
  warehouseApiRoutesProductUpdateProductCustomerCode,
  warehouseApiRoutesProductUpsertProductCustomerCode,
  type CustomerProductCodeSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useApi } from '@/composables/use-api'
import { useQuasar, type QTableColumn } from 'quasar'
import { onMounted, ref, watch } from 'vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import CustomerProductCodeUpsertDialog from './CustomerProductCodeUpsertDialog.vue'

const props = defineProps<{ productCode: string }>()

const { onResponse } = useApi()
const $q = useQuasar()

const codes = ref<CustomerProductCodeSchema[]>([])
const loading = ref(false)
const saving = ref(false)
const deletingId = ref<number | null>(null)
const showDialog = ref(false)
const showDeleteDialog = ref(false)
const editing = ref<CustomerProductCodeSchema | null>(null)
const pendingDelete = ref<CustomerProductCodeSchema | null>(null)

const load = async () => {
  loading.value = true
  try {
    const result = await warehouseApiRoutesProductGetProductCustomerCodes({
      path: { product_code: props.productCode },
    })
    codes.value = onResponse(result)?.data ?? []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.productCode, load)

const onAdd = () => {
  editing.value = null
  showDialog.value = true
}

const onEdit = (row: CustomerProductCodeSchema) => {
  editing.value = row
  showDialog.value = true
}

const onSubmit = async ({ customerCode, code }: { customerCode: string; code: string }) => {
  saving.value = true
  try {
    const path = { product_code: props.productCode }
    const result = editing.value
      ? await warehouseApiRoutesProductUpdateProductCustomerCode({
          path: { ...path, entry_id: editing.value.id },
          body: { code },
        })
      : await warehouseApiRoutesProductUpsertProductCustomerCode({
          path,
          body: { customer_code: customerCode, code },
        })
    if (!onResponse(result)?.data) {
      return
    }
    showDialog.value = false
    $q.notify({ type: 'positive', message: 'Kód zákazníka byl uložen.' })
    await load()
  } finally {
    saving.value = false
  }
}

const onDelete = (row: CustomerProductCodeSchema) => {
  pendingDelete.value = row
  showDeleteDialog.value = true
}

const onConfirmDelete = async () => {
  const row = pendingDelete.value
  if (!row) {
    return
  }
  deletingId.value = row.id
  try {
    const result = await warehouseApiRoutesProductDeleteProductCustomerCode({
      path: { product_code: props.productCode, entry_id: row.id },
    })
    const data = onResponse(result)
    if (data?.data) {
      codes.value = data.data
      $q.notify({ type: 'positive', message: 'Kód zákazníka byl odstraněn.' })
    }
  } finally {
    deletingId.value = null
    pendingDelete.value = null
  }
}

const columns: QTableColumn[] = [
  { name: 'actions', label: '', field: 'id', align: 'right' },
  { name: 'customer', label: 'Zákazník', field: 'customer', align: 'left' },
  {
    name: 'code',
    label: 'Kód zákazníka',
    field: 'code',
    align: 'left',
    classes: 'text-primary font-bold',
  },
]
</script>
