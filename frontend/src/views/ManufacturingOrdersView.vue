<template>
  <div class="flex-1">
    <div class="mb-5 flex justify-between items-center">
      <div>
        <h1>Přehled výrobních příkazů</h1>
        <h5 class="text-gray-5 mt-2">Správa výrobních příkazů</h5>
      </div>
      <q-btn
        color="primary"
        unelevated
        label="vytvořit"
        icon="sym_o_add"
        @click="newOrderDialog = true"
        class="mt-5 mx-4 sm:mx-0 sm:mt-0"
      />
    </div>

    <q-input
      v-model="search"
      outlined
      dense
      debounce="300"
      placeholder="Hledat..."
      class="mb-4"
      clearable
    >
      <template #prepend>
        <q-icon name="search" />
      </template>
    </q-input>
    <q-table
      :rows="orders"
      :columns="columns"
      row-key="code"
      :loading="loading"
      flat
      :pagination="{ rowsPerPage: 20 }"
    >
      <template #body-cell-code="slotProps">
        <q-td :props="slotProps">
          <router-link
            :to="{ name: 'manufacturingOrderDetail', params: { code: slotProps.row.code } }"
            class="link"
            >{{ slotProps.row.code }}</router-link
          >
        </q-td>
      </template>
      <template #body-cell-state="slotProps">
        <q-td :props="slotProps">
          <ManufacturingOrderStateBadge :state="slotProps.row.state" />
        </q-td>
      </template>
      <template #body-cell-is_external="slotProps">
        <q-td :props="slotProps">
          <q-badge :color="slotProps.row.is_external ? 'orange-8' : 'teal-7'">
            {{ slotProps.row.is_external ? 'Externí' : 'Interní' }}
          </q-badge>
        </q-td>
      </template>
      <template #no-data>
        <div class="text-center text-gray-5 py-8 w-full">Žádné výrobní příkazy</div>
      </template>
    </q-table>

    <ManufacturingOrderUpdateOrCreateDialog
      v-model:show="newOrderDialog"
      ref="newOrderDialogComponent"
      @create-order="createOrder"
    />
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesManufacturingOrdersCreateManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersGetManufacturingOrders,
  type ManufacturingOrderCreateOrUpdateSchema,
  type ManufacturingOrderSchema,
} from '@/client'
import ManufacturingOrderStateBadge from '@/components/manufacturing/ManufacturingOrderStateBadge.vue'
import ManufacturingOrderUpdateOrCreateDialog from '@/components/manufacturing/ManufacturingOrderUpdateOrCreateDialog.vue'
import { useApi } from '@/composables/use-api'
import router from '@/router'
import type { QTableColumn } from 'quasar'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'

const { onResponse } = useApi()
const $q = useQuasar()

const search = ref('')
const orders = ref<ManufacturingOrderSchema[]>([])
const loading = ref(false)

const fetchOrders = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesManufacturingOrdersGetManufacturingOrders({
      query: { search_term: search.value || undefined },
    })
    const data = onResponse(res)
    if (data) {
      orders.value = data.data
    }
  } finally {
    setTimeout(() => (loading.value = false), 300)
  }
}

await fetchOrders()

watch(search, fetchOrders)

const columns: QTableColumn[] = [
  { name: 'code', field: 'code', label: 'Číslo', align: 'left', sortable: true },
  { name: 'state', field: 'state', label: 'Stav', align: 'left' },
  { name: 'is_external', field: 'is_external', label: 'Typ', align: 'left' },
  {
    name: 'description',
    field: 'description',
    label: 'Popis',
    align: 'left',
    format: (val: string | null) => val ?? '',
  },
  {
    name: 'customer',
    field: (row: ManufacturingOrderSchema) => row.customer?.name ?? '',
    label: 'Pracoviště',
    align: 'left',
  },
  {
    name: 'items',
    field: (row: ManufacturingOrderSchema) => row.items?.length ?? 0,
    label: 'Počet položek',
    align: 'left',
  },
  {
    name: 'created',
    field: 'created',
    label: 'Datum vytvoření',
    align: 'left',
    format: (val: string) => new Date(val).toLocaleDateString('cs-CZ'),
    sortable: true,
  },
]

const goToOrder = (code: string) => {
  router.push({ name: 'manufacturingOrderDetail', params: { code } })
}

const newOrderDialog = ref(false)
const newOrderDialogComponent = ref<InstanceType<typeof ManufacturingOrderUpdateOrCreateDialog>>()

const createOrder = async (params: ManufacturingOrderCreateOrUpdateSchema) => {
  const response = await warehouseApiRoutesManufacturingOrdersCreateManufacturingOrder({
    body: params,
  })
  const data = onResponse(response)
  if (data && newOrderDialogComponent.value) {
    newOrderDialogComponent.value.reset()
    $q.notify({
      type: 'positive',
      message: `Výrobní příkaz úspěšně vytvořen: ${data.data.code}`,
    })
    goToOrder(data.data.code)
  }
}
</script>
