<template>
  <ForegroundPanel no-padding class="relative overflow-hidden">
    <template #header>
      <div class="flex items-center">
        <span class="text-xs font-semibold uppercase tracking-wide text-muted">
          Nedávná aktivita
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
          @click="fetchRecentActivity"
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
      <span class="text-sm font-semibold text-negative"
        >Nepodařilo se načíst poslední aktivitu</span
      >
      <span class="mt-1 text-xs text-gray-6">{{ errorMessage }}</span>
    </div>

    <div
      v-else-if="!loading && !activities.length"
      class="px-5 py-8 text-sm text-gray-5"
      data-testid="empty-state"
    >
      Zatím nejsou k dispozici žádné auditní záznamy.
    </div>

    <q-list v-else separator>
      <q-item
        v-for="activity in activities"
        :key="activity.id"
        class="items-center max-sm:items-start max-sm:flex-col"
      >
        <q-item-section avatar top>
          <div
            class="mt-1 flex h-8 w-8 items-center justify-center rounded-full light:bg-gray-1 dark:bg-dark-2"
            data-testid="activity-icon"
            :data-icon-name="activityIcon(activity.action)"
          >
            <q-icon
              :name="activityIcon(activity.action)"
              :color="activityIconColor(activity.action)"
              size="18px"
            />
          </div>
        </q-item-section>

        <q-item-section>
          <div class="text-sm" data-testid="activity-message">
            {{ activity.message }}
            <br />

            <span
              class="text-xs text-gray-5 flex items-center gap-3"
              data-testid="activity-timestamp"
              >{{ formatActivityTimestamp(activity.happened_at) }}
              <span class="w-1 h-1 bg-gray-5 rounded-full"></span>
              {{ activity.object_repr }}</span
            >
          </div>
        </q-item-section>
      </q-item>
    </q-list>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  type RecentActivityEntrySchema,
  warehouseApiRoutesAnalyticsGetRecentActivity,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import {
  getAuditEntryColor,
  getAuditEntryIcon,
} from '@/components/warehouse/audit-entry-presentation'
import { onMounted, ref } from 'vue'

const loading = ref(true)
const errorMessage = ref<string | null>(null)
const activities = ref<RecentActivityEntrySchema[]>([])

const activityIcon = (action?: string | null) => {
  return getAuditEntryIcon({ source: 'audit', action })
}

const activityIconColor = (action?: string | null) => {
  return getAuditEntryColor({ source: 'audit', action })
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

const formatActivityTimestamp = (value: string) => {
  const activityDate = new Date(value)
  const timestamp = activityDate.getTime()

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

const fetchRecentActivity = async () => {
  loading.value = true
  errorMessage.value = null

  try {
    const result = await warehouseApiRoutesAnalyticsGetRecentActivity()

    if (!result.response.ok || !result.data) {
      errorMessage.value = result.response.statusText || 'Zkuste obnovit stránku.'
      activities.value = []
      return
    }

    activities.value = result.data.data
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Zkuste obnovit stránku.'
    activities.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecentActivity)
</script>
