<template>
  <ForegroundPanel no-padding class="relative overflow-hidden">
    <template #header>
      <div class="flex items-center">
        <span class="text-xs font-semibold uppercase tracking-wide text-muted">
          Nedávné pohyby zásob
        </span>
        <q-btn
          v-if="!loading && !errorMessage"
          color="primary"
          flat
          dense
          rounded
          size="sm"
          icon="refresh"
          class="ml-auto"
          @click="fetchRecentMovements"
        >
          <q-tooltip>Obnovit</q-tooltip>
        </q-btn>
      </div>
    </template>

    <q-inner-loading :showing="loading">
      <q-spinner color="primary" size="32px" />
    </q-inner-loading>

    <div
      v-if="errorMessage"
      class="pointer-events-none absolute inset-0 grid content-center rounded bg-white/80 px-6 text-center dark:bg-dark/80"
    >
      <span class="text-sm font-semibold text-negative">Nepodařilo se načíst pohyby zásob</span>
      <span class="mt-1 text-xs text-gray-6">{{ errorMessage }}</span>
    </div>

    <div
      v-else-if="!loading && !movements.length"
      class="px-5 py-8 text-sm text-gray-5"
      data-testid="empty-state"
    >
      Zatím nejsou k dispozici žádné pohyby zásob.
    </div>

    <q-list v-else separator>
      <q-item
        v-for="movement in movements"
        :key="movement.id"
        class="items-center max-sm:items-start max-sm:flex-col"
      >
        <q-item-section avatar top>
          <div
            class="mt-1 flex h-8 w-8 items-center justify-center rounded-full light:bg-gray-1 dark:bg-dark-2"
            data-testid="movement-icon"
          >
            <q-icon name="swap_horizontal" color="primary" size="18px" />
          </div>
        </q-item-section>

        <q-item-section>
          <div class="text-sm" data-testid="movement-details">
            <router-link
              :to="{ name: 'productDetail', params: { productCode: movement.stock_product_code } }"
              class="link"
            >
              {{ movement.stock_product_name }}
            </router-link>
            <span class="mx-2 text-gray-5">•</span>
            <router-link
              :to="{ name: 'warehouseItemDetail', params: { itemId: movement.item_id } }"
              class="link text-muted!"
            >
              <q-icon name="sym_o_open_in_new" />
              <span class="ml-1">detail položky</span>
            </router-link>
            <br />
            <div class="text-xs text-gray-5">
              Množství: {{ formatAmount(movement.amount) }}
              <br />
              {{ movement.location_from_code ?? 'MIMO SKLAD' }}
              <q-icon name="sym_o_arrow_right_alt" class="mx-1" />
              {{ movement.location_to_code ?? 'MIMO SKLAD' }}
            </div>
          </div>
        </q-item-section>

        <q-item-section side>
          <div
            class="text-xs text-gray-5 flex flex-col items-end gap-1"
            data-testid="movement-metadata"
          >
            <span>{{ formatMovementTimestamp(movement.moved_at) }}</span>
            <span v-if="movement.worker_username" class="text-gray-5">
              {{ movement.worker_username }}
            </span>
            <span v-if="movement.batch_barcode" class="font-mono text-gray-5">
              šarže: {{ movement.batch_barcode }}
            </span>
          </div>
        </q-item-section>
      </q-item>
    </q-list>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type WarehouseMovementSchema,
  warehouseApiRoutesAnalyticsGetRecentWarehouseMovements,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { onMounted, ref } from 'vue'

const loading = ref(true)
const errorMessage = ref<string | null>(null)
const movements = ref<WarehouseMovementSchema[]>([])

const formatAmount = (amount: string) => {
  const numAmount = parseFloat(amount)
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  }).format(numAmount)
}

const formatAbsoluteTimestamp = (value: string) => {
  return new Date(value).toLocaleString('cs-CZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatMovementTimestamp = (value: string) => {
  const movementDate = new Date(value)
  const timestamp = movementDate.getTime()

  if (Number.isNaN(timestamp)) {
    return value
  }

  const diffInMilliseconds = Date.now() - timestamp
  if (diffInMilliseconds < 0) {
    return formatAbsoluteTimestamp(value)
  }

  const diffInMinutes = Math.floor(diffInMilliseconds / 60000)
  if (diffInMinutes < 1) {
    return 'právě teď'
  }

  if (diffInMinutes < 60) {
    return `před ${diffInMinutes}min`
  }

  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `před ${diffInHours}h`
  }

  return formatAbsoluteTimestamp(value)
}

const fetchRecentMovements = async () => {
  loading.value = true
  errorMessage.value = null

  try {
    const result = await warehouseApiRoutesAnalyticsGetRecentWarehouseMovements()

    if (!result.response.ok || !result.data) {
      errorMessage.value = result.response.statusText || 'Zkuste obnovit stránku.'
      movements.value = []
      return
    }

    movements.value = result.data.data
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Zkuste obnovit stránku.'
    movements.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecentMovements)
</script>
