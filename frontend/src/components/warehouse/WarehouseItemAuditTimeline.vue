<template>
  <q-timeline>
    <q-timeline-entry
      v-for="entry in entries"
      :key="`${entry.source}-${entry.id}-${entry.happened_at}`"
      :title="entryTitle(entry)"
      :subtitle="formatDateTimeLong(entry.happened_at)"
      :color="entryColor(entry)"
      :icon="entryIcon(entry)"
    >
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <q-badge color="grey-6" text-color="white" :label="sourceLabel(entry.source)" />
          <q-badge
            v-if="entry.action"
            :color="entryColor(entry)"
            text-color="white"
            :label="actionLabel(entry.action)"
          />
        </div>

        <div v-if="entry.reason" class="text-body2">{{ entry.reason }}</div>

        <div v-if="entry.object_repr" class="text-caption text-muted">
          Objekt: {{ entry.object_repr }}
        </div>

        <div class="text-caption text-muted flex gap-3 flex-wrap">
          <span
            v-if="entry.actor_user"
            class="flex items-center gap-1 text-sm font-bold text-primary"
            ><q-icon name="sym_o_contacts_product" />{{ entry.actor_user }}</span
          >
        </div>

        <q-list
          v-if="changeRows(entry).length > 0"
          dense
          bordered
          separator
          class="rounded max-w-sm overflow-hidden"
        >
          <q-item v-for="row in changeRows(entry)" :key="row.key">
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ row.key }}</q-item-label>
              <q-item-label caption>{{ row.value }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </q-timeline-entry>

    <q-timeline-entry v-if="entries.length === 0" title="Žádné záznamy" />
  </q-timeline>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDateTimeLong } from '@/utils/date'
import type { AuditTimelineEntrySchema } from '@/client'

const props = defineProps<{
  entries: AuditTimelineEntrySchema[]
}>()

const entries = computed(() => props.entries ?? [])

const ACTION_LABELS: Record<string, string> = {
  create: 'Vytvoření',
  update: 'Úprava',
  delete: 'Smazání',
  transition: 'Změna stavu',
  access: 'Přístup',
  other: 'Ostatní',
}

function normalizeAction(action?: string | null): string {
  return (action ?? '').toString().trim().toLowerCase()
}

function actionLabel(action?: string | null): string {
  const key = normalizeAction(action)
  return ACTION_LABELS[key] ?? action ?? 'Neznámá akce'
}

function sourceLabel(source: string): string {
  return source === 'movement' ? 'Pohyb' : 'Audit'
}

function entryTitle(entry: AuditTimelineEntrySchema): string {
  return entry.object_repr || actionLabel(entry.action)
}

function entryColor(entry: AuditTimelineEntrySchema): string {
  const action = normalizeAction(entry.action)
  if (entry.source === 'movement') {
    return 'primary'
  }
  if (action === 'create') {
    return 'positive'
  }
  if (action === 'delete') {
    return 'negative'
  }
  if (action === 'transition') {
    return 'warning'
  }
  return 'grey-7'
}

function entryIcon(entry: AuditTimelineEntrySchema): string {
  if (entry.source === 'movement') {
    return 'swap_horiz'
  }
  const action = normalizeAction(entry.action)
  if (action === 'create') {
    return 'add'
  }
  if (action === 'delete') {
    return 'delete'
  }
  if (action === 'transition') {
    return 'sym_o_double_arrow'
  }
  if (action === 'update') {
    return 'edit'
  }
  return 'history'
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}

function changeRows(entry: AuditTimelineEntrySchema): Array<{ key: string; value: string }> {
  const changes = entry.changes ?? {}
  return Object.entries(changes).map(([key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const record = value as Record<string, unknown>
      if ('old' in record || 'new' in record) {
        return {
          key,
          value: `${stringifyValue(record.old)} → ${stringifyValue(record.new)}`,
        }
      }
      if ('created' in record) {
        return {
          key,
          value: `vytvořeno: ${stringifyValue(record.created)}`,
        }
      }
    }

    return {
      key,
      value: stringifyValue(value),
    }
  })
}
</script>
