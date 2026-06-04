<template>
  <div class="relative flex flex-col">
    <DemoGraphWidget
      :title="widgetTitle"
      :caption="widgetCaption"
      :subtitle="widgetSubtitle"
      :data="chartData"
      :series="series"
      x-axis-key="label"
      :to="{ name: 'warehouseInboundOrders' }"
      class="flex-1"
    />

    <q-inner-loading :showing="loading">
      <q-spinner color="primary" size="32px" />
    </q-inner-loading>

    <div
      v-if="errorMessage"
      class="pointer-events-none absolute inset-0 grid content-center rounded bg-white/80 px-6 text-center dark:bg-dark/80"
    >
      <span class="text-sm font-semibold text-negative">
        Nepodařilo se načíst aktivní skladové doklady
      </span>
      <span class="mt-1 text-xs text-gray-6">{{ errorMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  type RecentOrdersDailyPointSchema,
  warehouseApiRoutesAnalyticsGetRecentOrders,
} from '@/client'
import { computed, onMounted, ref } from 'vue'
import DemoGraphWidget from './DemoGraphWidget.vue'

const LOOKBACK_DAYS = 14

const series = [
  { key: 'inbound', label: 'Příjemky', color: '#207ed8' },
  { key: 'outbound', label: 'Výdejky', color: '#0f9d58' },
]

const loading = ref(true)
const errorMessage = ref<string | null>(null)
const inbound = ref<RecentOrdersDailyPointSchema[]>([])
const outbound = ref<RecentOrdersDailyPointSchema[]>([])

const formatDayLabel = (value: string) =>
  new Date(value).toLocaleDateString('cs-CZ', {
    month: 'short',
    day: 'numeric',
  })

const chartData = computed(() => {
  const length = Math.max(inbound.value.length, outbound.value.length)
  return Array.from({ length }, (_, i) => ({
    label: formatDayLabel(inbound.value[i]?.date || outbound.value[i]?.date || ''),
    inbound: inbound.value[i]?.value ?? 0,
    outbound: outbound.value[i]?.value ?? 0,
  }))
})

const lastValue = (points: RecentOrdersDailyPointSchema[]) =>
  points.length ? points[points.length - 1]!.value : 0

const widgetTitle = computed(() => {
  const inboundLast = lastValue(inbound.value)
  const outboundLast = lastValue(outbound.value)
  const total = inboundLast + outboundLast
  return `${total}`
})

const widgetCaption = computed(() => {
  if (!inbound.value.length && !outbound.value.length) {
    return undefined
  }
  const lastDate = inbound.value[inbound.value.length - 1]?.date
  return lastDate ? formatDayLabel(lastDate) : undefined
})

const widgetSubtitle = computed(() => {
  if (loading.value) {
    return 'Načítám aktivní skladové doklady'
  }

  if (errorMessage.value) {
    return 'Aktivní skladové doklady se nepodařilo načíst'
  }

  const inboundTotal = inbound.value.reduce((sum, point) => sum + point.value, 0)
  const outboundTotal = outbound.value.reduce((sum, point) => sum + point.value, 0)
  const total = inboundTotal + outboundTotal

  if (!total) {
    return 'Žádné aktivní příjemky ani výdejky'
  }

  return `Aktivní příjemky a výdejky • posledních ${LOOKBACK_DAYS} dní, příjemky ${inboundTotal} / výdejky ${outboundTotal}`
})

const fetchRecentOrders = async () => {
  loading.value = true
  errorMessage.value = null

  try {
    const result = await warehouseApiRoutesAnalyticsGetRecentOrders({
      query: { days: LOOKBACK_DAYS },
    })

    if (!result.response.ok || !result.data) {
      throw new Error(result.response.statusText || 'Zkuste obnovit stránku.')
    }

    inbound.value = result.data.data.inbound
    outbound.value = result.data.data.outbound
  } catch (error) {
    inbound.value = []
    outbound.value = []
    errorMessage.value = error instanceof Error ? error.message : 'Zkuste obnovit stránku.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecentOrders)
</script>
