<template>
  <div class="relative">
    <DemoGraphWidget
      :title="widgetTitle"
      :subtitle="widgetSubtitle"
      :data="chartData"
      data-key="value"
      data-label="Hodnota skladu"
      x-axis-key="label"
      color="#0f9d58"
      :to="{ name: 'inventorySnapshots' }"
    />

    <q-inner-loading :showing="loading">
      <q-spinner color="primary" size="32px" />
    </q-inner-loading>

    <div
      v-if="errorMessage"
      class="pointer-events-none absolute inset-0 grid content-center rounded bg-white/80 px-6 text-center dark:bg-dark/80"
    >
      <span class="text-sm font-semibold text-negative">Nepodařilo se načíst hodnotu skladu</span>
      <span class="mt-1 text-xs text-gray-6">{{ errorMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  type InventorySnapshotSummarySchema,
  warehouseApiRoutesAnalyticsGetInventorySnapshots,
} from '@/client'
import DemoGraphWidget from './DemoGraphWidget.vue'
import { formatMoney } from '@/views/inventory-snapshot'
import { computed, onMounted, ref } from 'vue'

const loading = ref(true)
const errorMessage = ref<string | null>(null)
const snapshots = ref<InventorySnapshotSummarySchema[]>([])

const chartCurrency = computed(() => snapshots.value[0]?.purchase_totals[0]?.currency ?? null)

const getSnapshotCurrencyValue = (
  snapshot: InventorySnapshotSummarySchema,
  currency: string | null,
) => {
  if (!currency) {
    return null
  }

  const total = snapshot.purchase_totals.find((row) => row.currency === currency)
  return total?.value ?? null
}

const formatSnapshotValueLabel = (snapshot: InventorySnapshotSummarySchema) => {
  if (!snapshot.purchase_totals.length) {
    return '—'
  }

  return snapshot.purchase_totals.map((row) => `${formatMoney(row.value)}`).join(' / ')
}

const latestSnapshot = computed(() => snapshots.value[0] ?? null)

const widgetTitle = computed(() => {
  if (latestSnapshot.value) {
    return formatSnapshotValueLabel(latestSnapshot.value)
  }

  return '—'
})

const widgetSubtitle = computed(() => {
  if (loading.value) {
    return 'Načítám aktuální hodnotu skladu'
  }

  if (errorMessage.value) {
    return 'Hodnotu skladu se nepodařilo načíst'
  }

  if (!latestSnapshot.value) {
    return 'Zatím nejsou k dispozici žádné snapshoty skladu'
  }

  if (latestSnapshot.value.purchase_totals.length > 1 && chartCurrency.value) {
    return `Aktuální hodnota skladu • graf ${chartCurrency.value}`
  }

  return 'Aktuální hodnota skladu'
})

const chartData = computed(() => {
  const currency = chartCurrency.value

  return [...snapshots.value]
    .slice(0, 10)
    .reverse()
    .map((snapshot) => ({
      label: new Date(snapshot.captured_at).toLocaleDateString('cs-CZ', {
        month: 'short',
        day: 'numeric',
      }),
      value: Number.parseFloat(getSnapshotCurrencyValue(snapshot, currency) ?? '0'),
    }))
})

const fetchSnapshots = async () => {
  loading.value = true
  errorMessage.value = null

  try {
    const result = await warehouseApiRoutesAnalyticsGetInventorySnapshots({
      query: {
        page: 1,
        page_size: 10,
      },
    })

    if (!result.response.ok || !result.data) {
      errorMessage.value = result.response.statusText || 'Zkuste obnovit stránku.'
      snapshots.value = []
      return
    }

    snapshots.value = result.data.data
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Zkuste obnovit stránku.'
    snapshots.value = []
  } finally {
    setTimeout(() => {
      loading.value = false
    }, 300)
  }
}

onMounted(fetchSnapshots)
</script>
