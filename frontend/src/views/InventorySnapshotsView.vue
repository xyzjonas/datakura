<template>
  <div class="flex w-full flex-1 flex-col gap-3">
    <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <div class="text-xs uppercase tracking-wide text-muted">Skladové snapshoty</div>
        <h1 class="mt-1">Historie ocenění skladu</h1>
        <div class="mt-2 max-w-3xl text-sm text-gray-6">
          Snapshot ukládá kompletní stav skladu včetně ceny při snapshotu i ceny při příjmu.
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <q-btn
          unelevated
          color="primary"
          icon="sym_o_add"
          label="Vytvořit snapshot"
          :loading="createLoading"
          @click="createSnapshot"
        />
      </div>
    </div>

    <InventorySnapshotValuationToggle v-model:mode="valuationMode" class="max-w-[36rem]" />

    <div v-if="latestSnapshot" class="grid gap-3 xl:grid-cols-[1.2fr_1fr_1fr]">
      <ForegroundPanel class="flex flex-col justify-between gap-3">
        <div>
          <div class="text-xs uppercase tracking-wide text-muted">Poslední snapshot</div>
          <div class="mt-2 text-3xl font-semibold text-primary">#{{ latestSnapshot.id }}</div>
          <div class="mt-2 text-sm text-gray-6">
            {{ formatCapturedAt(latestSnapshot.captured_at) }}
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <q-badge color="primary">{{
            formatInventorySnapshotTriggerSource(latestSnapshot.trigger_source)
          }}</q-badge>
          <q-badge color="secondary">{{
            formatInventorySnapshotCadence(latestSnapshot.cadence)
          }}</q-badge>
          <InventorySnapshotReceiptCoverageBadge :snapshot="latestSnapshot" />
        </div>
      </ForegroundPanel>

      <InventorySnapshotTotalsPanel
        title="Cena při snapshotu"
        :totals="latestSnapshot.purchase_totals"
        caption="Zmražená aktuální nákupní cena produktu"
      />
      <InventorySnapshotTotalsPanel
        title="Cena při příjmu"
        :totals="latestSnapshot.receipt_totals"
        caption="Zmražená cena z příjmové řádky"
        empty-label="Žádné oceněné příjmové řádky"
      />
    </div>

    <ForegroundPanel>
      <q-table
        :rows="snapshots"
        :columns="columns"
        :loading="loading"
        flat
        row-key="id"
        class="bg-transparent"
        v-model:pagination="pagination"
        @request="onPaginationChange"
        :rows-per-page-options="[10, 20, 50]"
      >
        <template #top-left>
          <div>
            <h2>Seznam snapshotů</h2>
            <div class="mt-1 text-sm text-gray-6">
              Tabulka zobrazuje hodnotu podle zvoleného režimu ocenění.
            </div>
          </div>
        </template>

        <template #body-cell-id="props">
          <q-td>
            <a class="link" @click="goToSnapshot(props.row.id)">#{{ props.row.id }}</a>
          </q-td>
        </template>

        <template #body-cell-capturedAt="props">
          <q-td>{{ formatCapturedAt(props.row.captured_at) }}</q-td>
        </template>

        <template #body-cell-trigger="props">
          <q-td>
            <div class="flex flex-wrap gap-2">
              <q-badge color="primary">
                {{ formatInventorySnapshotTriggerSource(props.row.trigger_source) }}
              </q-badge>
              <q-badge color="secondary">{{
                formatInventorySnapshotCadence(props.row.cadence)
              }}</q-badge>
            </div>
          </q-td>
        </template>

        <template #body-cell-valuationTotal="props">
          <q-td class="font-semibold text-primary">
            {{ formatSnapshotTotals(props.row, valuationMode) }}
          </q-td>
        </template>

        <template #body-cell-receiptCoverage="props">
          <q-td>
            <InventorySnapshotReceiptCoverageBadge :snapshot="props.row" />
          </q-td>
        </template>

        <template #no-data>
          <EmptyPanel
            text="Žádné snapshoty nebyly vytvořeny"
            icon="sym_o_inventory_2"
            class="h-lg w-full"
          />
        </template>
      </q-table>
    </ForegroundPanel>
  </div>
</template>

<script setup lang="ts">
import {
  type InventorySnapshotSummarySchema,
  warehouseApiRoutesAnalyticsCreateInventorySnapshot,
  warehouseApiRoutesAnalyticsGetInventorySnapshots,
  warehouseApiRoutesAnalyticsGetInventoryValue,
} from '@/client'
import EmptyPanel from '@/components/EmptyPanel.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InventorySnapshotReceiptCoverageBadge from '@/components/warehouse/InventorySnapshotReceiptCoverageBadge.vue'
import InventorySnapshotTotalsPanel from '@/components/warehouse/InventorySnapshotTotalsPanel.vue'
import InventorySnapshotValuationToggle from '@/components/warehouse/InventorySnapshotValuationToggle.vue'
import { useApi } from '@/composables/use-api'
import {
  formatInventorySnapshotCadence,
  formatInventorySnapshotTriggerSource,
  formatSnapshotTotals,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'
import { type QTableColumn, type QTableProps } from 'quasar'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

type Pagination = NonNullable<QTableProps['pagination']>

const { onResponse } = useApi()
const router = useRouter()

const valuationMode = ref<InventorySnapshotValuationMode>('purchase')
const loading = ref(false)
const createLoading = ref(false)
const latestSnapshot = ref<InventorySnapshotSummarySchema | null>(null)
const snapshots = ref<InventorySnapshotSummarySchema[]>([])
const pagination = ref<Pagination>({
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0,
})

const formatCapturedAt = (value: string) => {
  return new Date(value).toLocaleString('cs-CZ')
}

const fetchLatestSnapshot = async () => {
  const response = await warehouseApiRoutesAnalyticsGetInventoryValue()
  const data = onResponse(response)
  latestSnapshot.value = data?.data.snapshot ?? null
}

const fetchSnapshots = async () => {
  loading.value = true
  try {
    const response = await warehouseApiRoutesAnalyticsGetInventorySnapshots({
      query: {
        page: Number(pagination.value.page),
        page_size: Number(pagination.value.rowsPerPage),
      },
    })
    const data = onResponse(response)
    if (!data) {
      return
    }

    snapshots.value = data.data
    pagination.value.rowsNumber = data.count
  } finally {
    loading.value = false
  }
}

const createSnapshot = async () => {
  createLoading.value = true
  try {
    const response = await warehouseApiRoutesAnalyticsCreateInventorySnapshot({
      body: {},
    })
    const data = onResponse(response)
    if (!data) {
      return
    }

    await Promise.all([fetchLatestSnapshot(), fetchSnapshots()])
    router.push({
      name: 'inventorySnapshotDetail',
      params: { snapshotId: data.data.id },
    })
  } finally {
    createLoading.value = false
  }
}

const goToSnapshot = (snapshotId: number) => {
  router.push({ name: 'inventorySnapshotDetail', params: { snapshotId } })
}

const onPaginationChange = async (requestProp: { pagination: QTableProps['pagination'] }) => {
  if (!requestProp.pagination) {
    return
  }

  pagination.value = {
    ...pagination.value,
    ...requestProp.pagination,
  }
  await fetchSnapshots()
}

await Promise.all([fetchLatestSnapshot(), fetchSnapshots()])

const columns = computed<QTableColumn[]>(() => [
  {
    name: 'id',
    label: '#',
    field: 'id',
    align: 'left',
  },
  {
    name: 'capturedAt',
    label: 'Pořízeno',
    field: 'captured_at',
    align: 'left',
  },
  {
    name: 'trigger',
    label: 'Zdroj',
    field: 'trigger_source',
    align: 'left',
  },
  {
    name: 'lineCount',
    label: 'Řádků',
    field: 'line_count',
    align: 'right',
  },
  {
    name: 'valuationTotal',
    label: valuationMode.value === 'purchase' ? 'Cena při snapshotu' : 'Cena při příjmu',
    field: (row: InventorySnapshotSummarySchema) => formatSnapshotTotals(row, valuationMode.value),
    align: 'left',
  },
  {
    name: 'receiptCoverage',
    label: 'Pokrytí příjmu',
    field: 'receipt_complete',
    align: 'left',
  },
])
</script>
