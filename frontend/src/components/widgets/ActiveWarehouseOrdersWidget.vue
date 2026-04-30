<template>
  <div class="relative flex flex-col">
    <SingleValueWidget
      :title="widgetTitle"
      :subtitle="widgetSubtitle"
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
  warehouseApiRoutesWarehouseGetInboundWarehouseOrders,
  warehouseApiRoutesWarehouseGetOutboundWarehouseOrders,
} from '@/client'
import { computed, onMounted, ref } from 'vue'
import SingleValueWidget from './SingleValueWidget.vue'
import {
  isInboundWarehouseOrderActive,
  isOutboundWarehouseOrderActive,
  loadAllPagedItems,
} from './order-widgets'

const loading = ref(true)
const errorMessage = ref<string | null>(null)
const counts = ref({ inbound: 0, outbound: 0 })

const total = computed(() => counts.value.inbound + counts.value.outbound)

const widgetTitle = computed(() => `${total.value}`)

const widgetSubtitle = computed(() => {
  if (loading.value) {
    return 'Načítám aktivní skladové doklady'
  }

  if (errorMessage.value) {
    return 'Aktivní skladové doklady se nepodařilo načíst'
  }

  if (!total.value) {
    return 'Žádné aktivní příjemky ani výdejky'
  }

  return `Aktivní příjemky a výdejky • příjemky ${counts.value.inbound} / výdejky ${counts.value.outbound}`
})

const fetchOrders = async () => {
  loading.value = true
  errorMessage.value = null

  try {
    const [inboundOrders, outboundOrders] = await Promise.all([
      loadAllPagedItems(
        (pageSize) =>
          warehouseApiRoutesWarehouseGetInboundWarehouseOrders({
            query: {
              page: 1,
              page_size: pageSize,
            },
          }),
        'Nepodařilo se načíst příjemky.',
      ),
      loadAllPagedItems(
        (pageSize) =>
          warehouseApiRoutesWarehouseGetOutboundWarehouseOrders({
            query: {
              page: 1,
              page_size: pageSize,
            },
          }),
        'Nepodařilo se načíst výdejky.',
      ),
    ])

    counts.value = {
      inbound: inboundOrders.filter(isInboundWarehouseOrderActive).length,
      outbound: outboundOrders.filter(isOutboundWarehouseOrderActive).length,
    }
  } catch (error) {
    counts.value = { inbound: 0, outbound: 0 }
    errorMessage.value = error instanceof Error ? error.message : 'Zkuste obnovit stránku.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchOrders)
</script>
